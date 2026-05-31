"""注册表单元测试"""

import pytest
from src.mcp.registry import McpToolRegistry, to_kebab_case, apply_registry_to_server


class TestToKebabCase:
    def test_simple(self):
        assert to_kebab_case("read_file") == "read-file"

    def test_camel_case(self):
        assert to_kebab_case("readFile") == "read-file"

    def test_mixed(self):
        assert to_kebab_case("ExecuteCommand") == "execute-command"


class TestMcpToolRegistry:
    def test_register_single(self):
        registry = McpToolRegistry()
        registry.register_tool("test_tool", lambda: None)
        assert "test-tool" in registry.get_tools()

    def test_register_batch(self):
        registry = McpToolRegistry()
        tools = {
            "tool_a": (lambda: None, {}),
            "tool_b": (lambda: None, {}),
        }
        registry.register_tools(tools)
        assert len(registry.get_tools()) == 2

    def test_include_filter(self):
        registry = McpToolRegistry(include={"tool-a"})
        registry.register_tool("tool_a", lambda: None)
        registry.register_tool("tool_b", lambda: None)
        assert "tool-a" in registry.get_tools()
        assert "tool-b" not in registry.get_tools()

    def test_exclude_filter(self):
        registry = McpToolRegistry(exclude={"tool-b"})
        registry.register_tool("tool_a", lambda: None)
        registry.register_tool("tool_b", lambda: None)
        assert "tool-a" in registry.get_tools()
        assert "tool-b" not in registry.get_tools()

    def test_get_tool_names(self):
        registry = McpToolRegistry()
        registry.register_tool("tool_a", lambda: None)
        registry.register_tool("tool_b", lambda: None)
        names = registry.get_tool_names()
        assert len(names) == 2
