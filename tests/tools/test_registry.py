"""测试: 工具注册表。"""

import pytest

from src.tools.registry import (
    ToolEntry,
    ToolRegistry,
    register_tool,
    get_tool,
    get_all_tools,
    get_tool_schemas,
    discover_tools,
)


@pytest.fixture(autouse=True)
def _clear_registry():
    """每个测试前后清空注册表。"""
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()


def _make_handler(result="ok"):
    """创建测试用 handler。"""
    def handler(**kwargs):
        return result
    return handler


class TestToolRegistry:
    """测试 ToolRegistry 类。"""

    def test_register_and_get_tool(self):
        """测试注册和获取工具。"""
        entry = ToolEntry(
            name="test_tool",
            toolset="test",
            schema={"name": "test_tool", "description": "Test", "parameters": {}},
            handler=_make_handler(),
        )
        register_tool(
            name="test_tool",
            toolset="test",
            schema=entry.schema,
            handler=_make_handler(),
        )

        result = get_tool("test_tool")
        assert result is not None
        assert result.name == "test_tool"
        assert result.toolset == "test"

    def test_get_nonexistent_tool(self):
        """测试获取不存在的工具返回 None。"""
        assert get_tool("nonexistent") is None

    def test_get_all_tools(self):
        """测试获取所有工具。"""
        register_tool(name="a", toolset="t", schema={}, handler=_make_handler())
        register_tool(name="b", toolset="t", schema={}, handler=_make_handler())

        tools = get_all_tools()
        assert len(tools) == 2
        assert {t.name for t in tools} == {"a", "b"}

    def test_get_tool_schemas_with_filter(self):
        """测试按 toolset 过滤获取 schema。"""
        register_tool(name="term", toolset="terminal", schema={"name": "term"}, handler=_make_handler())
        register_tool(name="file", toolset="file", schema={"name": "file"}, handler=_make_handler())

        schemas = get_tool_schemas(toolset_filter={"terminal"})
        assert len(schemas) == 1
        assert schemas[0]["name"] == "term"

    def test_get_tool_schemas_no_filter(self):
        """测试无过滤时获取所有 schema。"""
        register_tool(name="a", toolset="t", schema={"name": "a"}, handler=_make_handler())
        register_tool(name="b", toolset="t", schema={"name": "b"}, handler=_make_handler())

        schemas = get_tool_schemas()
        assert len(schemas) == 2

    def test_duplicate_name_logs_warning(self, caplog):
        """测试重复工具名记录警告。"""
        register_tool(name="dup", toolset="t", schema={}, handler=_make_handler())
        register_tool(name="dup", toolset="t", schema={}, handler=_make_handler("new"))

        assert "工具名冲突" in caplog.text

    def test_clear_registry(self):
        """测试清空注册表。"""
        register_tool(name="x", toolset="t", schema={}, handler=_make_handler())
        ToolRegistry.clear()
        assert get_all_tools() == []
