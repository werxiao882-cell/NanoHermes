"""工具分发器。

核心职责：在同步上下文中统一调度同步/异步工具执行。

设计决策说明：
1. 为什么需要异步桥接？
   - LLM 主循环是同步的（避免阻塞 UI 和简化错误处理）
   - 但许多工具（如网络请求、文件 I/O）天然适合异步实现
   - 桥接层让同步代码能安全调用异步 handler，无需重构主循环

2. 三种异步桥接策略的选择依据：
   * 策略 A（已有事件循环 -> 新线程执行）：
     - 当检测到 asyncio.get_running_loop() 时，说明当前线程已有事件循环在运行
     - 不能在同一线程嵌套调用 run_until_complete()（会触发 "This event loop is already running" 错误）
     - 也不能直接 await（因为 dispatch() 是同步函数）
     - 解决方案：创建新线程 + 新事件循环，隔离执行环境
   
   * 策略 B（无事件循环 -> 持久事件循环）：
     - 当没有运行中的事件循环时，复用全局持久循环
     - 避免每次调用都创建/销毁线程和事件循环的开销
     - 适用于 CLI 路径（主线程无事件循环，但可能频繁调用工具）
   
   * 策略 C（超时保护 300 秒）：
     - 防止工具无限阻塞（如网络超时、死锁）
     - 300 秒是经验值：足够完成大多数工具调用，又不会永久阻塞主线程
     - 两种策略都使用相同超时阈值，保持一致性

3. 持久事件循环的生命周期管理：
   - 懒加载：首次调用时创建，避免启动时不必要的资源占用
   - 线程安全：使用 _persistent_loop_lock 防止并发创建多个循环
   - 守护线程：daemon=True 确保主程序退出时自动清理
   - 永久运行：run_forever() 保持循环存活，通过 run_coroutine_threadsafe() 提交任务

4. 工具分发的策略模式：
   - 通过 ToolRegistry 统一查找工具（解耦注册与执行）
   - 通过 entry.is_async 分支选择执行策略（同步直接调用 vs 异步桥接）
   - 通过 check_fn 实现可用性检查（如 API Key 是否配置）
   - 统一错误包装：所有异常转为 JSON 错误字符串，保证返回值格式一致
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

from src.tools.registry import ToolRegistry
from src.tools.availability import check_tool_availability

logger = logging.getLogger(__name__)

# 持久事件循环（CLI 路径复用）
# 为什么需要全局持久循环？
# - CLI 场景下，主线程没有事件循环，但工具调用频繁
# - 每次创建新线程+新循环的开销较大（约 10-50ms）
# - 持久循环只需创建一次，后续调用通过 run_coroutine_threadsafe() 提交任务
# - 使用守护线程确保程序退出时自动清理，无需显式关闭
_persistent_loop: asyncio.AbstractEventLoop | None = None
_persistent_loop_thread: threading.Thread | None = None
_persistent_loop_lock = threading.Lock()  # 保护 _persistent_loop 的懒加载（防止并发创建多个循环）


def dispatch(
    name: str,
    args: dict[str, Any] | str | None = None,
    task_id: str | None = None,
) -> str:
    """分发工具调用。

    策略模式实现：
    - 根据工具名称查找对应的 ToolEntry（注册表模式）
    - 根据 entry.is_async 选择执行策略（同步直接调用 vs 异步桥接）
    - 根据 entry.check_fn 实现可用性检查（可选的守卫条件）
    - 统一错误包装：所有异常转为 JSON 错误字符串，保证返回值格式一致

    执行流程：
    1. 按名称查找 ToolEntry
    2. 检查工具可用性（check_fn）
    3. 解析参数（如果是 JSON 字符串则解析为 dict）
    4. 执行 handler（同步直接调用，异步通过内部桥接）
    5. 返回结果字符串
    6. 任何异常包装为 JSON 错误字符串

    Args:
        name: 工具名称。
        args: 工具参数字典或 JSON 字符串。
              为什么支持字符串？因为 LLM 返回的 function_call.arguments 是 JSON 字符串。
        task_id: 任务 ID，用于日志和会话关联。

    Returns:
        工具执行结果（JSON 字符串）。
    """
    # 步骤 1: 查找工具
    # 为什么返回 JSON 错误而不是抛异常？
    # - dispatch() 是同步函数，被主循环直接调用
    # - 抛异常会导致主循环中断，影响用户体验
    # - 返回错误字符串让主循环能继续处理（如展示错误给用户）
    entry = ToolRegistry.get_tool(name)
    if entry is None:
        tool_names = [t.name for t in ToolRegistry.get_all_tools()]
        return json.dumps({
            "error": f"工具未找到: '{name}'。已注册的工具: "
                     f"{', '.join(tool_names)}"
        })

    # 步骤 2: 检查可用性
    # 为什么需要可用性检查？
    # - 某些工具依赖外部服务（如 API Key、网络连接、特定软件）
    # - 在执行前快速失败，避免无效调用和超时等待
    # - check_fn 是可选的（None 表示无需检查）
    if entry.check_fn and not check_tool_availability(entry.check_fn):
        return json.dumps({
            "error": f"工具不可用: '{name}'。检查函数返回 False。"
        })

    # 步骤 3: 解析参数（LLM 返回的 arguments 是 JSON 字符串）
    # 为什么需要解析？
    # - LLM 的 function_call.arguments 字段是 JSON 格式的字符串
    # - handler 期望接收 dict 参数
    # - _parse_args() 处理多种输入格式（None/dict/str），保证兼容性
    call_args = _parse_args(args)

    # 步骤 4: 执行 handler
    try:
        if entry.is_async:
            # 异步工具通过桥接执行
            # 为什么不能直接 await？
            # - dispatch() 是同步函数，不能使用 await 语法
            # - 需要通过桥接层在同步上下文中安全执行异步代码
            result = _async_bridge(entry.handler, call_args, task_id)
        else:
            # 同步工具直接调用
            # 为什么注入 task_id？
            # - 工具可能需要记录日志或关联会话
            # - 统一注入避免每个工具手动处理
            result = entry.handler(**call_args, task_id=task_id)

        return result

    except Exception as e:
        # 步骤 5: 错误包装
        # 为什么捕获所有异常？
        # - 工具实现可能有各种 bug（网络错误、解析错误、权限问题等）
        # - 主循环需要稳定的返回值格式（JSON 字符串）
        # - exc_info=True 记录完整堆栈，便于调试
        logger.error(f"工具执行失败 '{name}': {e}", exc_info=True)
        return json.dumps({
            "error": f"工具执行失败: {type(e).__name__}: {e}"
        })


def _async_bridge(
    async_fn,
    args: dict[str, Any],
    task_id: str | None = None,
) -> str:
    """在同步上下文中执行异步函数。

    为什么需要这个函数？
    - dispatch() 是同步函数，但工具 handler 可能是 async def 定义的
    - Python 不允许在同步函数中直接使用 await
    - 也不能简单调用 asyncio.run()，因为可能与现有事件循环冲突

    桥接策略选择逻辑：
    1. 尝试获取当前运行中的事件循环（asyncio.get_running_loop()）
       - 如果成功：说明当前线程已有事件循环在运行
         -> 使用策略 A：创建新线程 + 新事件循环执行（_run_in_new_thread）
         -> 原因：不能在同一线程嵌套调用 run_until_complete()
       
       - 如果失败（RuntimeError）：说明当前线程没有运行中的事件循环
         -> 使用策略 B：复用持久事件循环执行（_run_in_persistent_loop）
         -> 原因：避免每次调用都创建/销毁线程的开销

    Args:
        async_fn: 异步函数（async def 定义的 handler）
        args: 参数字典
        task_id: 任务 ID（注入到参数中）

    Returns:
        执行结果（字符串）
    """
    # 注入 task_id 到参数中（工具 handler 可能需要用于日志或会话关联）
    if task_id is not None:
        args = {**args, "task_id": task_id}

    try:
        # 尝试获取当前运行中的事件循环
        # 如果成功，说明当前线程已有事件循环（如 TUI 或其他异步框架）
        loop = asyncio.get_running_loop()
        # 策略 A：在新线程中创建独立事件循环执行
        # 为什么不能直接用 loop.run_until_complete()？
        # - 会触发 "This event loop is already running" 错误
        # - 也不能用 asyncio.ensure_future()，因为 dispatch() 是同步的，无法 await
        return _run_in_new_thread(async_fn, args)
    except RuntimeError:
        # 策略 B：当前线程没有运行中的事件循环
        # 复用持久事件循环（懒加载，首次调用时创建）
        return _run_in_persistent_loop(async_fn, args)


def _run_in_persistent_loop(
    async_fn,
    args: dict[str, Any],
) -> str:
    """在持久事件循环中执行异步函数。

    持久事件循环的生命周期管理：
    1. 懒加载：首次调用时创建，避免启动时不必要的资源占用
    2. 线程安全：使用 _persistent_loop_lock 防止并发创建多个循环
       - 为什么需要锁？多个工具调用可能并发进入此函数
       - 没有锁会导致创建多个事件循环，造成资源浪费和不可预测的行为
    3. 守护线程：daemon=True 确保主程序退出时自动清理
       - 为什么是守护线程？非守护线程会阻止程序退出
       - 程序退出时，守护线程会被强制终止，无需显式关闭
    4. 永久运行：run_forever() 保持循环存活
       - 为什么不 run_until_complete()？因为循环需要持续服务多次调用
       - 通过 run_coroutine_threadsafe() 提交任务到循环

    超时保护机制：
    - future.result(timeout=300) 等待最多 300 秒
    - 为什么是 300 秒？经验值：足够完成大多数工具调用，又不会永久阻塞
    - 超时抛出 TimeoutError，被 except 捕获并返回错误字符串

    Args:
        async_fn: 异步函数
        args: 参数字典

    Returns:
        执行结果（字符串）或错误 JSON
    """
    global _persistent_loop

    # 线程安全地初始化持久事件循环（懒加载 + 单例模式）
    with _persistent_loop_lock:
        if _persistent_loop is None:
            # 创建新的事件循环
            _persistent_loop = asyncio.new_event_loop()

            # 定义循环运行函数（在独立线程中执行）
            def _run_loop():
                # 将循环绑定到当前线程（asyncio 要求每个线程有自己的事件循环）
                asyncio.set_event_loop(_persistent_loop)
                # 永久运行，等待任务提交（通过 run_coroutine_threadsafe）
                _persistent_loop.run_forever()

            # 创建守护线程运行事件循环
            _persistent_loop_thread = threading.Thread(
                target=_run_loop,
                daemon=True,  # 守护线程：主程序退出时自动终止
            )
            _persistent_loop_thread.start()
            # 注意：这里没有等待循环启动，因为 run_forever() 是阻塞的
            # 但 run_coroutine_threadsafe() 是线程安全的，可以在循环运行后提交任务

    # 将协程提交到持久事件循环（线程安全）
    # run_coroutine_threadsafe() 返回 Future，可以在其他线程中等待结果
    future = asyncio.run_coroutine_threadsafe(async_fn(**args), _persistent_loop)
    try:
        # 等待结果，最多 300 秒
        # 超时抛出 TimeoutError，被 except 捕获
        result = future.result(timeout=300)
        return str(result)
    except Exception as e:
        # 捕获所有异常（包括 TimeoutError、CancelledError、工具内部异常等）
        # 统一包装为 JSON 错误字符串，保证返回值格式一致
        return json.dumps({
            "error": f"异步执行失败: {type(e).__name__}: {e}"
        })


def _run_in_new_thread(
    async_fn,
    args: dict[str, Any],
) -> str:
    """在新线程中创建事件循环执行异步函数。

    适用场景：
    - 当前线程已有运行中的事件循环（如 TUI、其他异步框架）
    - 不能在当前线程嵌套调用 run_until_complete()
    - 也不能直接 await（因为 dispatch() 是同步函数）

    执行流程：
    1. 创建新线程
    2. 在新线程中创建独立的事件循环
    3. 运行协程直到完成
    4. 通过 result 列表传递结果/异常（线程安全的简单方式）
    5. 主线程等待最多 300 秒（thread.join(timeout=300)）

    为什么用 result 列表而不是 Queue？
    - 只需要传递单个结果，列表足够简单
    - 通过检查列表是否为空判断超时
    - 避免引入额外的同步原语（Queue 内部也是基于锁和条件变量）

    超时处理：
    - thread.join(timeout=300) 等待线程结束
    - 如果超时，result 为空，返回超时错误
    - 注意：线程不会立即终止，但主线程不再等待
    - 守护线程会在主程序退出时自动清理

    Args:
        async_fn: 异步函数
        args: 参数字典

    Returns:
        执行结果（字符串）或错误 JSON
    """
    # 使用列表传递结果（线程安全的简单方式）
    # 为什么不用 Queue？因为只需要传递单个结果，列表更简单
    result: list[str | Exception] = []

    def _target():
        """在新线程中执行的函数。"""
        try:
            # 创建协程对象
            coro = async_fn(**args)
            # 创建新的事件循环（每个线程需要自己的事件循环）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # 运行协程直到完成
            outcome = loop.run_until_complete(coro)
            # 将结果存入列表（字符串化，保证可序列化）
            result.append(str(outcome))
        except Exception as e:
            # 捕获所有异常，存入列表
            result.append(e)
        finally:
            # 关闭事件循环（释放资源）
            loop.close()

    # 创建并启动守护线程
    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    # 等待线程结束，最多 300 秒
    thread.join(timeout=300)

    # 检查结果列表
    if not result:
        # 超时：线程还在运行，但主线程不再等待
        return json.dumps({"error": "异步执行超时"})

    outcome = result[0]
    if isinstance(outcome, Exception):
        # 工具执行异常
        return json.dumps({
            "error": f"异步执行失败: {type(outcome).__name__}: {outcome}"
        })
    # 成功返回结果
    return outcome


def _parse_args(args: dict[str, Any] | str | None) -> dict[str, Any]:
    """解析工具参数。

    为什么需要这个函数？
    - LLM 返回的 function_call.arguments 是 JSON 格式的字符串
    - 但工具 handler 期望接收 dict 参数
    - 需要处理多种输入格式，保证兼容性

    支持的输入格式：
    1. None -> 返回空字典 {}
    2. dict -> 直接返回（已经是正确格式）
    3. str -> 尝试解析为 JSON：
       - 成功且是 dict -> 返回解析后的字典
       - 成功但不是 dict（如列表、字符串）-> 包装为 {"value": parsed}
       - 解析失败 -> 包装为 {"raw": args}（保留原始字符串）

    边界情况处理：
    - 为什么非 dict JSON 值包装为 {"value": parsed}？
      因为某些工具可能只接收单个参数，这样 handler 可以通过 args["value"] 获取
    - 为什么解析失败返回 {"raw": args}？
      因为可能是非 JSON 格式的字符串（如纯文本），保留原始值让工具自行处理

    Args:
        args: 工具参数（None/dict/str）

    Returns:
        解析后的参数字典
    """
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            if isinstance(parsed, dict):
                return parsed
            # JSON 成功但不是 dict（如列表、字符串、数字）
            # 包装为 {"value": parsed} 让工具可以通过固定键获取
            return {"value": parsed}
        except json.JSONDecodeError:
            # 不是有效的 JSON，保留原始字符串
            # 某些工具可能接收纯文本参数（如搜索关键词）
            return {"raw": args}
    # 其他类型（理论上不应该出现），返回空字典
    return {}
