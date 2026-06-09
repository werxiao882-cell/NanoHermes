"""测试: 工具分发器。"""

import json
import pytest

from src.tools.registry import register_tool, ToolRegistry, ToolEntry
from src.tools.dispatcher import dispatch, dispatch_batch


@pytest.fixture(autouse=True)
def _clear_registry():
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()


class TestDispatch:
    """测试 dispatch 函数。"""

    def test_dispatch_existing_tool(self):
        """测试分发已存在的工具。"""
        register_tool(
            name="echo",
            toolset="test",
            schema={"name": "echo"},
            handler=lambda **kwargs: json.dumps({"echo": kwargs.get("msg", "")}),
        )

        result = dispatch("echo", {"msg": "hello"})
        data = json.loads(result)
        assert data["echo"] == "hello"

    def test_dispatch_nonexistent_tool(self):
        """测试分发不存在的工具返回 InputValidationError + select: 提示。"""
        register_tool(
            name="existing_tool",
            toolset="test",
            schema={"name": "existing_tool"},
            handler=lambda **kwargs: "ok",
        )
        register_tool(
            name="deferred_tool",
            toolset="test",
            schema={"name": "deferred_tool"},
            handler=lambda **kwargs: "ok",
            defer_loading=True,
        )

        result = dispatch("nonexistent_tool")
        data = json.loads(result)
        assert data["error"] == "InputValidationError"
        assert "nonexistent_tool" in data["message"]
        assert "select:nonexistent_tool" in data["hint"]
        assert "existing_tool" in data["available_tools"]
        assert "deferred_tool" in data["deferred_tools"]

    def test_dispatch_handler_exception(self):
        """测试 handler 抛出异常时返回错误。"""
        register_tool(
            name="failing",
            toolset="test",
            schema={"name": "failing"},
            handler=lambda **kwargs: 1 / 0,  # 抛出 ZeroDivisionError
        )

        result = dispatch("failing")
        data = json.loads(result)
        assert "error" in data
        assert "ZeroDivisionError" in data["error"]

    def test_dispatch_task_id_propagation(self):
        """测试 task_id 传播到 handler。"""
        received_task_id = None

        def handler(task_id=None, **kwargs):
            nonlocal received_task_id
            received_task_id = task_id
            return "ok"

        register_tool(name="with_id", toolset="test", schema={}, handler=handler)
        dispatch("with_id", task_id="task_123")

        assert received_task_id == "task_123"

    def test_dispatch_unavailable_tool(self):
        """测试不可用工具返回错误。"""
        register_tool(
            name="unavailable",
            toolset="test",
            schema={"name": "unavailable"},
            handler=lambda **kwargs: "ok",
            check_fn=lambda: False,
        )

        result = dispatch("unavailable")
        data = json.loads(result)
        assert "error" in data
        assert "不可用" in data["error"]


class TestDispatchBatch:
    """测试 dispatch_batch 函数。"""

    def _register_tool(self, name, is_concurrency_safe=False, max_concurrent=1):
        """Helper: register a test tool with concurrency flags."""
        register_tool(
            name=name,
            toolset="test",
            schema={"name": name},
            handler=lambda **kwargs: json.dumps({"tool": name, "args": kwargs}),
        )
        # Set concurrency flags via direct ToolEntry update
        entry = ToolRegistry.get_tool(name)
        if entry:
            entry.is_concurrency_safe = is_concurrency_safe
            entry.max_concurrent_instances = max_concurrent

    def test_dispatch_batch_empty(self):
        """空列表返回空结果。"""
        assert dispatch_batch([]) == []

    def test_dispatch_batch_single(self):
        """单个工具调用正常工作。"""
        self._register_tool("echo")
        results = dispatch_batch([("echo", {"msg": "hello"})])
        assert len(results) == 1
        data = json.loads(results[0])
        assert data["tool"] == "echo"

    def test_dispatch_batch_multiple(self):
        """多个工具调用按顺序返回结果。"""
        self._register_tool("add")
        self._register_tool("mul")

        results = dispatch_batch([
            ("add", {"a": 1, "b": 2}),
            ("mul", {"a": 3, "b": 4}),
        ])
        assert len(results) == 2

        data1 = json.loads(results[0])
        assert data1["tool"] == "add"

        data2 = json.loads(results[1])
        assert data2["tool"] == "mul"

    def test_dispatch_batch_order_preserved(self):
        """结果顺序与输入顺序一致。"""
        self._register_tool("first")
        self._register_tool("second")
        self._register_tool("third")

        results = dispatch_batch([
            ("third", {}),
            ("first", {}),
            ("second", {}),
        ])

        assert json.loads(results[0])["tool"] == "third"
        assert json.loads(results[1])["tool"] == "first"
        assert json.loads(results[2])["tool"] == "second"

    def test_dispatch_batch_mixed_existence(self):
        """混合存在和不存在的工具。"""
        self._register_tool("exists")

        results = dispatch_batch([
            ("exists", {}),
            ("ghost_tool", {}),
        ])
        assert len(results) == 2

        data1 = json.loads(results[0])
        assert "tool" in data1

        data2 = json.loads(results[1])
        assert "error" in data2
        assert data2["error"] == "InputValidationError"

    def test_dispatch_batch_with_none_args(self):
        """参数为 None 时正常工作。"""
        self._register_tool("no_args")
        results = dispatch_batch([("no_args", None)])
        assert len(results) == 1

    def test_dispatch_batch_with_string_args(self):
        """JSON 字符串参数正常工作。"""
        self._register_tool("json_args")
        results = dispatch_batch([
            ("json_args", '{"key": "value"}'),
        ])
        assert len(results) == 1
        data = json.loads(results[0])
        assert data["tool"] == "json_args"


class TestConcurrencyIntegration:
    """测试 dispatch_batch 与并发限流器的集成。"""

    def _register_tool(self, name, is_concurrency_safe=False, max_concurrent=1):
        register_tool(
            name=name,
            toolset="test",
            schema={"name": name},
            handler=lambda **kwargs: json.dumps({"tool": name}),
        )
        entry = ToolRegistry.get_tool(name)
        if entry:
            entry.is_concurrency_safe = is_concurrency_safe
            entry.max_concurrent_instances = max_concurrent

    def test_partition_respects_concurrency_flags(self):
        """并发安全工具被分组到一起。"""
        from src.tools.concurrency_limiter import ToolConcurrencyLimiter

        self._register_tool("safe_read", is_concurrency_safe=True)
        self._register_tool("safe_search", is_concurrency_safe=True)
        self._register_tool("unsafe_write", is_concurrency_safe=False)

        limiter = ToolConcurrencyLimiter()
        limiter.register_tool("safe_read", is_concurrency_safe=True)
        limiter.register_tool("safe_search", is_concurrency_safe=True)
        limiter.register_tool("unsafe_write", is_concurrency_safe=False)

        call_dicts = [
            {"name": "safe_read", "args": {}},
            {"name": "safe_search", "args": {}},
            {"name": "unsafe_write", "args": {}},
        ]

        batches = limiter.partition_tool_calls(call_dicts)

        # 连续的安全工具应该被合并到一个组
        assert len(batches) == 2
        assert batches[0]["is_concurrency_safe"] is True
        assert len(batches[0]["calls"]) == 2  # safe_read + safe_search
        assert batches[1]["is_concurrency_safe"] is False
        assert len(batches[1]["calls"]) == 1  # unsafe_write

    def test_non_consecutive_safe_tools_separate(self):
        """不连续的安全工具不合并。"""
        from src.tools.concurrency_limiter import ToolConcurrencyLimiter

        self._register_tool("safe1", is_concurrency_safe=True)
        self._register_tool("unsafe", is_concurrency_safe=False)
        self._register_tool("safe2", is_concurrency_safe=True)

        limiter = ToolConcurrencyLimiter()
        limiter.register_tool("safe1", is_concurrency_safe=True)
        limiter.register_tool("unsafe", is_concurrency_safe=False)
        limiter.register_tool("safe2", is_concurrency_safe=True)

        call_dicts = [
            {"name": "safe1"},
            {"name": "unsafe"},
            {"name": "safe2"},
        ]

        batches = limiter.partition_tool_calls(call_dicts)

        # safe1 | unsafe | safe2 -> 3 groups
        assert len(batches) == 3
        assert batches[0]["is_concurrency_safe"] is True
        assert batches[1]["is_concurrency_safe"] is False
        assert batches[2]["is_concurrency_safe"] is True

    def test_execute_batch_sync_preserves_order(self):
        """execute_batch_sync 保持结果顺序。"""
        from src.tools.concurrency_limiter import ToolConcurrencyLimiter

        self._register_tool("a")
        self._register_tool("b")
        self._register_tool("c")

        limiter = ToolConcurrencyLimiter()

        call_dicts = [
            {"name": "a", "args": {}},
            {"name": "b", "args": {}},
            {"name": "c", "args": {}},
        ]

        results = limiter.execute_batch_sync(call_dicts, dispatch)

        assert len(results) == 3
        assert json.loads(results[0])["tool"] == "a"
        assert json.loads(results[1])["tool"] == "b"
        assert json.loads(results[2])["tool"] == "c"
