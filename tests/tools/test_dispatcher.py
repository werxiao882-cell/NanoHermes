"""测试: 工具分发器。"""

import json
import pytest

from src.tools.registry import register_tool, ToolRegistry
from src.tools.dispatcher import dispatch


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
        """测试分发不存在的工具返回错误。"""
        result = dispatch("nonexistent_tool")
        data = json.loads(result)
        assert "error" in data
        assert "未找到" in data["error"]

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
