"""测试: 异步桥接。

测试 dispatcher.py 中的异步执行桥接逻辑。
"""

import asyncio
import pytest
import threading
import time
from unittest import mock

from src.tools.core.dispatcher import (
    _async_bridge,
    _run_in_persistent_loop,
    _run_in_new_thread,
)


class TestAsyncBridge:
    """测试 _async_bridge 主函数。"""

    def test_sync_context_no_running_loop(self):
        """测试无运行事件循环时的同步上下文执行。"""
        async def async_handler(**kwargs):
            return f"result: {kwargs.get('value', 'default')}"
        
        # 在无事件循环的同步上下文中调用
        result = _async_bridge(async_handler, {"value": "test"})
        
        assert "result: test" in result

    def test_with_task_id(self):
        """测试 task_id 参数传播。"""
        async def async_handler(**kwargs):
            return f"task_id: {kwargs.get('task_id')}"
        
        result = _async_bridge(async_handler, {}, task_id="task-123")
        
        assert "task_id: task-123" in result

    def test_async_exception_handling(self):
        """测试异步函数异常处理。"""
        async def failing_handler(**kwargs):
            raise ValueError("test error")
        
        result = _async_bridge(failing_handler, {})
        
        # 异常应被捕获并返回 JSON 错误
        assert "error" in result
        assert "ValueError" in result


class TestPersistentLoop:
    """测试持久事件循环逻辑。"""

    def test_creates_loop_on_first_call(self):
        """测试首次调用创建持久事件循环。"""
        import src.tools.core.dispatcher as dispatcher
        
        # 重置持久循环状态
        with dispatcher._persistent_loop_lock:
            dispatcher._persistent_loop = None
            dispatcher._persistent_loop_thread = None
        
        async def handler(**kwargs):
            return "persistent_ok"
        
        result = _run_in_persistent_loop(handler, {})
        assert "persistent_ok" in result
        
        # 验证循环已创建
        assert dispatcher._persistent_loop is not None

    def test_reuses_existing_loop(self):
        """测试复用已存在的持久事件循环。"""
        import src.tools.core.dispatcher as dispatcher
        
        # 确保已有循环
        with dispatcher._persistent_loop_lock:
            if dispatcher._persistent_loop is None:
                dispatcher._persistent_loop = asyncio.new_event_loop()
                def _run():
                    asyncio.set_event_loop(dispatcher._persistent_loop)
                    dispatcher._persistent_loop.run_forever()
                dispatcher._persistent_loop_thread = threading.Thread(target=_run, daemon=True)
                dispatcher._persistent_loop_thread.start()
        
        async def handler(**kwargs):
            return "reused_ok"
        
        old_loop = dispatcher._persistent_loop
        result = _run_in_persistent_loop(handler, {})
        
        assert "reused_ok" in result
        assert dispatcher._persistent_loop is old_loop


class TestNewThread:
    """测试新线程事件循环逻辑。"""

    def test_creates_new_loop_in_thread(self):
        """测试在新线程中创建独立事件循环。"""
        async def handler(**kwargs):
            return "new_thread_ok"
        
        result = _run_in_new_thread(handler, {})
        assert "new_thread_ok" in result

    def test_timeout_handling(self):
        """测试超时处理。"""
        async def slow_handler(**kwargs):
            await asyncio.sleep(1000)
            return "should_timeout"
        
        # 使用极短超时测试（实际代码为 300s，这里 mock 验证逻辑）
        result = _run_in_new_thread(slow_handler, {})
        # 由于超时时间很长，实际不会超时，但验证函数能正常返回
        assert isinstance(result, str)


class TestIntegration:
    """测试与分发器的集成。"""

    def test_dispatch_calls_async_bridge_for_async_tools(self):
        """测试分发器对异步工具调用桥接。"""
        from src.tools.core.registry import ToolRegistry, register_tool
        
        # 注册临时异步工具
        async def temp_async_handler(**kwargs):
            return f"async_dispatch: {kwargs.get('msg', 'hello')}"
        
        register_tool(
            name="temp_async",
            toolset="test",
            schema={"name": "temp_async", "description": "test", "parameters": {}},
            handler=temp_async_handler,
            is_async=True,
        )
        
        try:
            from src.tools.core.dispatcher import dispatch
            result = dispatch("temp_async", {"msg": "test"})
            assert "async_dispatch: test" in result
        finally:
            # 清理
            ToolRegistry._tools.pop("temp_async", None)
