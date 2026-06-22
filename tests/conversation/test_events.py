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
        assert len(EventType) == 18


class TestChainInterceptors:
    """测试责任链拦截器机制。"""

    def test_intercept_and_emit_returns_chain_result(self):
        """测试 intercept 注册后 emit 返回 ChainResult。"""
        from src.conversation.events import ChainResult

        bus = EventBus()
        bus.intercept(EventType.TOOL_START, lambda data, next_fn: next_fn())
        result = bus.emit(EventType.TOOL_START, {})

        assert isinstance(result, ChainResult)
        assert result.blocked is False

    def test_interceptor_can_modify_data(self):
        """测试拦截器可以修改 data dict。"""
        bus = EventBus()

        def modifier(data, next_fn):
            data["modified"] = True
            next_fn()

        bus.intercept(EventType.TOOL_START, modifier)
        data = {"original": True}
        bus.emit(EventType.TOOL_START, data)

        assert data["modified"] is True

    def test_interceptor_block_by_not_calling_next(self):
        """测试拦截器不调用 next_fn 表示阻断。"""
        bus = EventBus()

        def blocker(data, next_fn):
            pass  # 不调用 next_fn = 阻断

        bus.intercept(EventType.TOOL_START, blocker)
        result = bus.emit(EventType.TOOL_START, {})

        assert result.blocked is True

    def test_interceptor_block_stops_subsequent_interceptors(self):
        """测试阻断后后续拦截器不执行。"""
        bus = EventBus()
        execution_order = []

        def blocker(data, next_fn):
            execution_order.append("blocker")
            # 不调用 next_fn

        def should_not_run(data, next_fn):
            execution_order.append("should_not_run")
            next_fn()

        bus.intercept(EventType.TOOL_START, blocker, priority=1)
        bus.intercept(EventType.TOOL_START, should_not_run, priority=2)
        bus.emit(EventType.TOOL_START, {})

        assert execution_order == ["blocker"]

    def test_interceptor_priority_order(self):
        """测试拦截器按 priority 升序执行。"""
        bus = EventBus()
        execution_order = []

        def make_handler(name):
            def handler(data, next_fn):
                execution_order.append(name)
                next_fn()
            return handler

        bus.intercept(EventType.TOOL_START, make_handler("high"), priority=10)
        bus.intercept(EventType.TOOL_START, make_handler("low"), priority=1)
        bus.intercept(EventType.TOOL_START, make_handler("medium"), priority=5)
        bus.emit(EventType.TOOL_START, {})

        assert execution_order == ["low", "medium", "high"]

    def test_observers_still_fire_when_blocked(self):
        """测试拦截器阻断后观察者仍然触发。"""
        bus = EventBus()
        observer_called = False

        def blocker(data, next_fn):
            pass  # 阻断

        def observer(data):
            nonlocal observer_called
            observer_called = True

        bus.intercept(EventType.TOOL_START, blocker)
        bus.on(EventType.TOOL_START, observer)
        bus.emit(EventType.TOOL_START, {})

        assert observer_called is True

    def test_interceptor_exception_does_not_block_others(self):
        """测试拦截器异常不影响其他拦截器。"""
        bus = EventBus()
        execution_order = []

        def bad_interceptor(data, next_fn):
            execution_order.append("bad")
            raise ValueError("Interceptor error")

        def good_interceptor(data, next_fn):
            execution_order.append("good")
            next_fn()

        bus.intercept(EventType.TOOL_START, bad_interceptor, priority=1)
        bus.intercept(EventType.TOOL_START, good_interceptor, priority=2)
        result = bus.emit(EventType.TOOL_START, {})

        assert "bad" in execution_order
        assert "good" in execution_order
        assert result.blocked is False  # 异常不视为阻断

    def test_interceptor_onion_model(self):
        """测试拦截器洋葱模型（next 前后执行逻辑）。"""
        bus = EventBus()
        execution_order = []

        def make_onion(name):
            def handler(data, next_fn):
                execution_order.append(f"{name}_before")
                next_fn()
                execution_order.append(f"{name}_after")
            return handler

        bus.intercept(EventType.TOOL_START, make_onion("outer"), priority=1)
        bus.intercept(EventType.TOOL_START, make_onion("inner"), priority=2)
        bus.emit(EventType.TOOL_START, {})

        assert execution_order == [
            "outer_before",
            "inner_before",
            "inner_after",
            "outer_after",
        ]

    def test_no_interceptors_backward_compatible(self):
        """测试无拦截器时行为与现有逻辑一致。"""
        bus = EventBus()
        received = []

        def observer(data):
            received.append(data)

        bus.on(EventType.TOOL_START, observer)
        result = bus.emit(EventType.TOOL_START, {"test": "data"})

        assert len(received) == 1
        assert received[0]["test"] == "data"
        assert result.blocked is False

    def test_emit_returns_chain_result_not_none(self):
        """测试 emit 返回 ChainResult 而非 None（向后兼容：调用方可忽略返回值）。"""
        bus = EventBus()
        result = bus.emit(EventType.TOOL_START, {})

        # 调用方忽略返回值不应报错
        bus.emit(EventType.TOOL_START, {})

        # 返回值是 ChainResult
        from src.conversation.events import ChainResult
        assert isinstance(result, ChainResult)

    def test_clear_also_clears_interceptors(self):
        """测试 clear 同时清除拦截器和观察者。"""
        bus = EventBus()
        bus.intercept(EventType.TOOL_START, lambda data, next_fn: next_fn())
        bus.on(EventType.TOOL_START, lambda data: None)
        bus.clear(EventType.TOOL_START)

        result = bus.emit(EventType.TOOL_START, {})
        assert result.blocked is False

    def test_unintercept_removes_interceptor(self):
        """测试 unintercept 移除拦截器。"""
        bus = EventBus()

        def blocker(data, next_fn):
            pass  # 阻断

        bus.intercept(EventType.TOOL_START, blocker)
        bus.unintercept(EventType.TOOL_START, blocker)
        result = bus.emit(EventType.TOOL_START, {})

        assert result.blocked is False

    def test_interceptor_exception_after_next_does_not_block(self):
        """测试拦截器调用 next 后抛出异常不阻断。"""
        bus = EventBus()

        def bad_after_next(data, next_fn):
            next_fn()
            raise ValueError("Error after next")

        def good_interceptor(data, next_fn):
            next_fn()

        bus.intercept(EventType.TOOL_START, bad_after_next, priority=1)
        bus.intercept(EventType.TOOL_START, good_interceptor, priority=2)
        result = bus.emit(EventType.TOOL_START, {})

        assert result.blocked is False
