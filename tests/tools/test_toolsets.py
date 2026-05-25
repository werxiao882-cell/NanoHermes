"""测试: 工具集解析。"""

from src.tools.toolsets import TOOLSETS, resolve_toolset, resolve_enabled_toolsets


class TestResolveToolset:
    """测试 resolve_toolset 函数。"""

    def test_resolve_single_toolset(self):
        """测试解析单个工具集。"""
        result = resolve_toolset("terminal")
        assert "terminal" in result

    def test_resolve_multiple_toolsets(self):
        """测试解析多个工具集（逗号分隔）。"""
        result = resolve_toolset("terminal,file")
        assert "terminal" in result

    def test_resolve_nonexistent_toolset(self):
        """测试解析不存在的工具集返回空集合。"""
        result = resolve_toolset("nonexistent")
        assert result == set()


class TestResolveEnabledToolsets:
    """测试 resolve_enabled_toolsets 函数。"""

    def test_enabled_whitelist(self):
        """测试白名单模式：只包含启用的。"""
        result = resolve_enabled_toolsets(enabled_toolsets=["terminal"])
        assert "terminal" in result
        assert "read_file" not in result

    def test_disabled_blacklist(self):
        """测试黑名单模式：排除禁用的。"""
        result = resolve_enabled_toolsets(disabled_toolsets=["terminal"])
        assert "terminal" not in result

    def test_no_filter_returns_all(self):
        """测试无过滤返回所有工具。"""
        result = resolve_enabled_toolsets()
        assert len(result) > 0
