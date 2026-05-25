"""异步桥接。

在同步调用链中执行异步工具 handler。

策略：
1. 检测是否有运行中的事件循环
2. 如果没有：使用持久事件循环（复用，保持异步客户端存活）
3. 如果有：在新线程中创建独立事件循环执行

这解决了以下场景：
- CLI 路径（无运行中的事件循环）：需要持久 loop 复用
- Gateway 路径（有运行中的事件循环）：不能阻塞主 loop，需要新线程
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

# 持久事件循环（CLI 路径复用）
_persistent_loop: asyncio.AbstractEventLoop | None = None
_persistent_loop_thread: threading.Thread | None = None
_persistent_loop_lock = threading.Lock()


def async_bridge(
    async_fn,
    args: dict[str, Any],
    task_id: str | None = None,
) -> str:
    """在同步上下文中执行异步函数。

    执行策略：
    1. 检测是否有运行中的事件循环
    2. 无 loop → 使用持久事件循环
    3. 有 loop → 在新线程中执行

    Args:
        async_fn: 异步函数。
        args: 传递给异步函数的参数字典。
        task_id: 任务 ID（可选）。

    Returns:
        异步函数的返回值（字符串）。
    """
    # 添加 task_id 到参数中
    if task_id is not None:
        args = {**args, "task_id": task_id}

    try:
        # 检测是否有运行中的事件循环
        loop = asyncio.get_running_loop()
        # 有运行中的 loop，在新线程中执行
        return _run_in_new_thread(async_fn, args)
    except RuntimeError:
        # 没有运行中的 loop，使用持久事件循环
        return _run_in_persistent_loop(async_fn, args)


def _run_in_persistent_loop(
    async_fn,
    args: dict[str, Any],
) -> str:
    """在持久事件循环中执行异步函数。

    Args:
        async_fn: 异步函数。
        args: 参数字典。

    Returns:
        异步函数的返回值。
    """
    global _persistent_loop

    with _persistent_loop_lock:
        if _persistent_loop is None:
            # 创建新的持久事件循环
            _persistent_loop = asyncio.new_event_loop()

            def _run_loop():
                asyncio.set_event_loop(_persistent_loop)
                _persistent_loop.run_forever()

            _persistent_loop_thread = threading.Thread(
                target=_run_loop,
                daemon=True,
            )
            _persistent_loop_thread.start()

    # 在持久 loop 中执行协程
    future = asyncio.run_coroutine_threadsafe(async_fn(**args), _persistent_loop)
    try:
        result = future.result(timeout=300)  # 5 分钟超时
        return str(result)
    except Exception as e:
        import json
        return json.dumps({
            "error": f"异步执行失败: {type(e).__name__}: {e}"
        })


def _run_in_new_thread(
    async_fn,
    args: dict[str, Any],
) -> str:
    """在新线程中创建事件循环执行异步函数。

    用于已有运行中事件循环的场景（如 Gateway 路径）。

    Args:
        async_fn: 异步函数。
        args: 参数字典。

    Returns:
        异步函数的返回值。
    """
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
        import json
        return json.dumps({"error": "异步执行超时"})

    outcome = result[0]
    if isinstance(outcome, Exception):
        import json
        return json.dumps({
            "error": f"异步执行失败: {type(outcome).__name__}: {outcome}"
        })
    return outcome
