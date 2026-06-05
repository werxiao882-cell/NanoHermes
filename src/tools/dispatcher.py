"""工具分发器。

按工具名查找并执行 handler，统一处理：
1. 工具查找
2. 可用性检查
3. 参数解析（JSON 字符串 → dict）
4. task_id 传播
5. 错误包装（所有异常转为 JSON 错误字符串）
6. 异步桥接（在同步上下文中执行异步 handler）
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
_persistent_loop: asyncio.AbstractEventLoop | None = None
_persistent_loop_thread: threading.Thread | None = None
_persistent_loop_lock = threading.Lock()


def dispatch(
    name: str,
    args: dict[str, Any] | str | None = None,
    task_id: str | None = None,
) -> str:
    """分发工具调用。

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
        task_id: 任务 ID，用于日志和会话关联。

    Returns:
        工具执行结果（JSON 字符串）。
    """
    # 步骤 1: 查找工具
    entry = ToolRegistry.get_tool(name)
    if entry is None:
        tool_names = [t.name for t in ToolRegistry.get_all_tools()]
        return json.dumps({
            "error": f"工具未找到: '{name}'。已注册的工具: "
                     f"{', '.join(tool_names)}"
        })

    # 步骤 2: 检查可用性
    if entry.check_fn and not check_tool_availability(entry.check_fn):
        return json.dumps({
            "error": f"工具不可用: '{name}'。检查函数返回 False。"
        })

    # 步骤 3: 解析参数（LLM 返回的 arguments 是 JSON 字符串）
    call_args = _parse_args(args)

    # 步骤 4: 执行 handler
    try:
        if entry.is_async:
            # 异步工具通过桥接执行
            result = _async_bridge(entry.handler, call_args, task_id)
        else:
            # 同步工具直接调用
            result = entry.handler(**call_args, task_id=task_id)

        return result

    except Exception as e:
        # 步骤 5: 错误包装
        logger.error(f"工具执行失败 '{name}': {e}", exc_info=True)
        return json.dumps({
            "error": f"工具执行失败: {type(e).__name__}: {e}"
        })


def _async_bridge(
    async_fn,
    args: dict[str, Any],
    task_id: str | None = None,
) -> str:
    """在同步上下文中执行异步函数。"""
    if task_id is not None:
        args = {**args, "task_id": task_id}

    try:
        loop = asyncio.get_running_loop()
        return _run_in_new_thread(async_fn, args)
    except RuntimeError:
        return _run_in_persistent_loop(async_fn, args)


def _run_in_persistent_loop(
    async_fn,
    args: dict[str, Any],
) -> str:
    """在持久事件循环中执行异步函数。"""
    global _persistent_loop

    with _persistent_loop_lock:
        if _persistent_loop is None:
            _persistent_loop = asyncio.new_event_loop()

            def _run_loop():
                asyncio.set_event_loop(_persistent_loop)
                _persistent_loop.run_forever()

            _persistent_loop_thread = threading.Thread(
                target=_run_loop,
                daemon=True,
            )
            _persistent_loop_thread.start()

    future = asyncio.run_coroutine_threadsafe(async_fn(**args), _persistent_loop)
    try:
        result = future.result(timeout=300)
        return str(result)
    except Exception as e:
        return json.dumps({
            "error": f"异步执行失败: {type(e).__name__}: {e}"
        })


def _run_in_new_thread(
    async_fn,
    args: dict[str, Any],
) -> str:
    """在新线程中创建事件循环执行异步函数。"""
    result: list[str | Exception] = []

    def _target():
        try:
            coro = async_fn(**args)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            outcome = loop.run_until_complete(coro)
            result.append(str(outcome))
        except Exception as e:
            result.append(e)
        finally:
            loop.close()

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=300)

    if not result:
        return json.dumps({"error": "异步执行超时"})

    outcome = result[0]
    if isinstance(outcome, Exception):
        return json.dumps({
            "error": f"异步执行失败: {type(outcome).__name__}: {outcome}"
        })
    return outcome


def _parse_args(args: dict[str, Any] | str | None) -> dict[str, Any]:
    """解析工具参数。"""
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
        except json.JSONDecodeError:
            return {"raw": args}
    return {}
