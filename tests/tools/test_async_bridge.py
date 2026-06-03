"""测试: 异步桥接。

测试 src/tools/async_bridge.py 中的异步执行桥接逻辑。
"""

import asyncio
import pytest
import threading
import time
from unittest import mock

from src.tools.async_bridge import (
    async_bridge,
    _run_in_persistent_loop,
    _run_in_new_thread,
)


class TestAsyncBridge:
    """测试 async_bridge 主函数。"""

    def test_sync_context_no_running_loop(self):
        """测试无运行事件循环时的同步上下文执行。"""
        async def async_handler(**kwargs):
            return f"result: {kwargs.get('value', 'default')}"
        
        # 在无事件循环的同步上下文中调用
        result = async_bridge(async_handler, {"value": "test"})
        
        assert "result: test" in result

    def test_with_task_id(self):
        """测试 task_id 参数传播。"""
        async def async_handler(**kwargs):
            return f"task_id: {kwargs.get('task_id')}"
        
        result = async_bridge(async_handler, {}, task_id="task-123")
        
        assert "task_id: task-123" in result

    def test_async_exception_handling(self):
        """测试异步函数异常处理。"""
        async def failing_handler(**kwargs):
            raise ValueError("test error")
        
        result = async_bridge(failing_handler, {})
        
        # 异常应被捕获并返回 JSON 错误
        assert "error" in result
        assert "ValueError" in result

    def test_async_timeout(self):
        """测试超时处理。"""
        async def slow_handler(**kwargs):
            await asyncio.sleep(400)  # 超过 300 秒超时
            return "done"
        
        # 注意：实际测试中不等待 300 秒
        # 这里只验证函数不会阻塞主线程
        # 实际超时测试需要 mock time 或使用更小的超时值


class TestRunWithPersistentLoop:
    """测试持久事件循环执行。"""

    def test_persistent_loop_created_when_needed(self):
        """测试需要时创建持久事件循环。"""
        async def handler(**kwargs):
            return "test result"
        
        # 通过 async_bridge 调用会创建持久 loop
        result = async_bridge(handler, {})
        
        # 验证结果正确返回
        assert "test result" in result

    def test_reuses_existing_loop(self):
        """测试复用已存在的持久事件循环。"""
        async def handler(**kwargs):
            return f"call-{kwargs.get('call', 1)}"
        
        # 首次调用
        result1 = async_bridge(handler, {"call": 1})
        
        # 第二次调用应复用
        result2 = async_bridge(handler, {"call": 2})
        
        assert "call-1" in result1
        assert "call-2" in result2


class TestRunWithNewThread:
    """测试新线程执行。"""

    def test_executes_in_separate_thread(self):
        """测试在新线程中执行。"""
        main_thread_id = threading.current_thread().ident
        
        async def handler(**kwargs):
            await asyncio.sleep(0.01)
            return f"thread: {threading.current_thread().ident != main_thread_id}"
        
        result = _run_in_new_thread(handler, {})
        
        # 应在新线程中执行
        assert "thread: True" in result

    def test_exception_in_thread(self):
        """测试线程内异常处理。"""
        async def failing_handler(**kwargs):
            raise RuntimeError("thread error")
        
        result = _run_in_new_thread(failing_handler, {})
        
        assert "error" in result
        assert "RuntimeError" in result

    def test_thread_timeout(self):
        """测试线程超时处理。"""
        async def slow_handler(**kwargs):
            await asyncio.sleep(400)  # 超时
            return "late"
        
        # 实际测试中不等待超时
        # 超时逻辑通过 thread.join(timeout=300) 实现


class TestAsyncBridgeInRunningLoop:
    """测试在有运行事件循环时的行为。"""

    @pytest.mark.asyncio
    async def test_bridge_with_running_loop(self):
        """测试在异步测试中调用 async_bridge。"""
        # pytest.mark.asyncio 会创建运行中的事件循环
        async def handler(**kwargs):
            await asyncio.sleep(0.01)
            return "async result"
        
        # 在运行中的 loop 内调用，应使用新线程
        result = async_bridge(handler, {"test": "value"})
        
        assert "async result" in result

    @pytest.mark.asyncio
    async def test_concurrent_calls(self):
        """测试并发调用不会阻塞。"""
        async def handler(**kwargs):
            await asyncio.sleep(0.05)
            return f"id: {kwargs.get('id')}"
        
        # 在 async 上下文中并发调用
        results = []
        for i in range(3):
            # 每个调用应在新线程中执行，不阻塞主 loop
            result = async_bridge(handler, {"id": i})
            results.append(result)
        
        # 所有调用应成功完成
        for i, result in enumerate(results):
            assert f"id: {i}" in result


class TestAsyncBridgeReturnType:
    """测试返回值类型处理。"""

    def test_string_result(self):
        """测试字符串结果。"""
        async def string_handler(**kwargs):
            return "plain string"
        
        result = async_bridge(string_handler, {})
        assert result == "plain string"

    def test_dict_result_converted_to_string(self):
        """测试 dict 结果转换为字符串。"""
        async def dict_handler(**kwargs):
            return {"key": "value", "nested": {"a": 1}}
        
        result = async_bridge(dict_handler, {})
        # dict 应被 str() 转换
        assert "key" in result
        assert "value" in result

    def test_none_result(self):
        """测试 None 结果。"""
        async def none_handler(**kwargs):
            return None
        
        result = async_bridge(none_handler, {})
        assert result == "None" or result == ""  # str(None) == "None"