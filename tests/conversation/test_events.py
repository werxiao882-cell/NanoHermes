"""EventBus 事件系统测试。"""

import pytest
from src.conversation.events import EventBus, EventType


class TestEventBus:
    """测试 EventBus 基本功能。"""

    def test_subscribe_and_emit(self):
        """测试订阅和触发事件。"""
        bus = EventBus()
        received_data = []

        def handler(data):
            received_data.append(data)

        bus.on(EventType.TOOL_START, handler)
        bus.emit(EventType.TOOL_START, {"tool_name": "test", "tool_args": "{}"})

        assert len(received_data) == 1
        assert received_data[0]["tool_name"] == "test"

    def test_multiple_handlers(self):
        """测试多个处理器订阅同一事件。"""
        bus = EventBus()
        results = []

        def handler1(data):
            results.append("handler1")

        def handler2(data):
            results.append("handler2")

        bus.on(EventType.TOOL_START, handler1)
        bus.on(EventType.TOOL_START, handler2)
        bus.emit(EventType.TOOL_START, {})

        assert len(results) == 2
        assert "handler1" in results
        assert "handler2" in results

    def test_unsubscribe(self):
        """测试取消订阅。"""
        bus = EventBus()
        results = []

        def handler(data):
            results.append("called")

        bus.on(EventType.TOOL_START, handler)
        bus.off(EventType.TOOL_START, handler)
        bus.emit(EventType.TOOL_START, {})

        assert len(results) == 0

    def test_handler_exception_isolation(self):
        """测试处理器异常不影响其他处理器。"""
        bus = EventBus()
        results = []

        def bad_handler(data):
            raise ValueError("Handler error")

        def good_handler(data):
            results.append("success")

        bus.on(EventType.TOOL_START, bad_handler)
        bus.on(EventType.TOOL_START, good_handler)
        bus.emit(EventType.TOOL_START, {})

        assert len(results) == 1
        assert results[0] == "success"

    def test_clear_specific_event(self):
        """测试清除特定事件的订阅。"""
        bus = EventBus()
        results = []

        def handler(data):
            results.append("called")

        bus.on(EventType.TOOL_START, handler)
        bus.on(EventType.TOOL_END, handler)
        bus.clear(EventType.TOOL_START)

        bus.emit(EventType.TOOL_START, {})
        bus.emit(EventType.TOOL_END, {})

        assert len(results) == 1

    def test_clear_all_events(self):
        """测试清除所有事件的订阅。"""
        bus = EventBus()
        results = []

        def handler(data):
            results.append("called")

        bus.on(EventType.TOOL_START, handler)
        bus.on(EventType.TOOL_END, handler)
        bus.clear()

        bus.emit(EventType.TOOL_START, {})
        bus.emit(EventType.TOOL_END, {})

        assert len(results) == 0

    def test_emit_with_none_data(self):
        """测试触发事件时 data 为 None。"""
        bus = EventBus()
        received_data = []

        def handler(data):
            received_data.append(data)

        bus.on(EventType.TOOL_START, handler)
        bus.emit(EventType.TOOL_START, None)

        assert len(received_data) == 1
        assert received_data[0] == {}

    def test_emit_nonexistent_event(self):
        """测试触发未订阅的事件。"""
        bus = EventBus()
        bus.emit(EventType.TOOL_START, {"test": "data"})


class TestEventType:
    """测试 EventType 枚举。"""

    def test_lifecycle_events(self):
        """测试生命周期事件类型。"""
        assert EventType.LOOP_START.value == "loop_start"
        assert EventType.LOOP_END.value == "loop_end"
        assert EventType.ITERATION_START.value == "iteration_start"
        assert EventType.ITERATION_END.value == "iteration_end"

    def test_model_events(self):
        """测试模型调用事件类型。"""
        assert EventType.MODEL_REQUEST.value == "model_request"
        assert EventType.MODEL_RESPONSE.value == "model_response"
        assert EventType.MODEL_ERROR.value == "model_error"
        assert EventType.MODEL_RETRY.value == "model_retry"

    def test_tool_events(self):
        """测试工具事件类型。"""
        assert EventType.TOOL_START.value == "tool_start"
        assert EventType.TOOL_END.value == "tool_end"
        assert EventType.TOOL_ERROR.value == "tool_error"

    def test_message_events(self):
        """测试消息事件类型。"""
        assert EventType.MESSAGE_APPEND.value == "message_append"

    def test_context_events(self):
        """测试上下文事件类型。"""
        assert EventType.PRE_COMPRESS.value == "pre_compress"

    def test_control_events(self):
        """测试控制事件类型。"""
        assert EventType.INTERRUPT.value == "interrupt"
        assert EventType.MAX_ITERATIONS.value == "max_iterations"

    def test_total_event_count(self):
        """测试事件类型总数。"""
        assert len(EventType) == 15
