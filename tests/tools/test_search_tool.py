"""Tool Search 测试。

覆盖：
- ToolEntry defer_loading 字段
- ToolRegistry 过滤方法
- ToolSearch BM25 + Regex 搜索
- ConversationLoop 动态工具发现
"""

import json
import sys
import pytest

from src.tools.registry import ToolEntry, ToolRegistry, register_tool, get_deferred_tools, get_tool_schemas
from src.tools.search_tool import ToolSearch


@pytest.fixture(autouse=True)
def clean_registry():
    """每个测试前后清理注册表，并重新导入工具模块。"""
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()


def _reinit_all_tools():
    """重新导入所有工具模块（清除 sys.modules 缓存后）。"""
    tool_modules = [
        "src.tools.terminal",
        "src.tools.file_tool",
        "src.tools.clarify_tool",
        "src.tools.code_execution_tool",
        "src.tools.cronjob_tool",
        "src.tools.delegation_tool",
        "src.tools.memory_tool",
        "src.tools.session_search_tool",
        "src.tools.skills_tool",
        "src.tools.process_tool",
        "src.tools.todo_tool",
    ]
    for mod in tool_modules:
        sys.modules.pop(mod, None)

    import importlib
    for mod in tool_modules:
        try:
            importlib.import_module(mod)
        except Exception:
            pass


# ============================================================================
# 7.1-7.4: defer_loading 字段和注册表过滤
# ============================================================================

class TestDeferLoadingField:
    """测试 ToolEntry defer_loading 字段。"""

    def test_default_value_is_false(self):
        """默认 defer_loading 为 False。"""
        entry = ToolEntry(
            name="test_tool",
            toolset="test",
            schema={"name": "test_tool"},
            handler=lambda: "ok",
        )
        assert entry.defer_loading is False

    def test_explicit_true(self):
        """显式设置 defer_loading=True。"""
        entry = ToolEntry(
            name="deferred_tool",
            toolset="test",
            schema={"name": "deferred_tool"},
            handler=lambda: "ok",
            defer_loading=True,
        )
        assert entry.defer_loading is True


class TestRegistryFiltering:
    """测试 ToolRegistry 过滤方法。"""

    def _register_tools(self):
        """注册 3 个核心工具 + 2 个延迟工具。"""
        register_tool(name="core_a", toolset="core", schema={"name": "core_a"}, handler=lambda: "a")
        register_tool(name="core_b", toolset="core", schema={"name": "core_b"}, handler=lambda: "b")
        register_tool(name="core_c", toolset="core", schema={"name": "core_c"}, handler=lambda: "c")
        register_tool(name="defer_a", toolset="extra", schema={"name": "defer_a"}, handler=lambda: "d", defer_loading=True)
        register_tool(name="defer_b", toolset="extra", schema={"name": "defer_b"}, handler=lambda: "e", defer_loading=True)

    def test_get_tool_schemas_exclude_deferred(self):
        """exclude_deferred=True 只返回非延迟工具。"""
        self._register_tools()
        schemas = get_tool_schemas(exclude_deferred=True)
        names = {s["name"] for s in schemas}
        assert names == {"core_a", "core_b", "core_c"}

    def test_get_tool_schemas_include_all(self):
        """exclude_deferred=False（默认）返回所有工具。"""
        self._register_tools()
        schemas = get_tool_schemas(exclude_deferred=False)
        names = {s["name"] for s in schemas}
        assert names == {"core_a", "core_b", "core_c", "defer_a", "defer_b"}

    def test_get_deferred_tools(self):
        """get_deferred_tools() 返回所有 defer_loading=True 的条目。"""
        self._register_tools()
        deferred = get_deferred_tools()
        names = {e.name for e in deferred}
        assert names == {"defer_a", "defer_b"}

    def test_five_core_eleven_deferred(self):
        """验证 5 个核心工具 + 11 个延迟工具 + 1 个 search_tools。"""
        # 清理并重新导入所有工具模块
        ToolRegistry.clear()
        tool_modules = [
            "src.tools.terminal",
            "src.tools.file_tool",
            "src.tools.clarify_tool",
            "src.tools.code_execution_tool",
            "src.tools.cronjob_tool",
            "src.tools.delegation_tool",
            "src.tools.memory_tool",
            "src.tools.session_search_tool",
            "src.tools.skills_tool",
            "src.tools.process_tool",
            "src.tools.todo_tool",
            "src.tools.search_tool",
        ]
        for mod in tool_modules:
            sys.modules.pop(mod, None)

        import importlib
        for mod in tool_modules:
            try:
                importlib.import_module(mod)
            except Exception:
                pass

        all_tools = ToolRegistry.get_all_tools()
        core = get_tool_schemas(exclude_deferred=True)
        deferred = get_deferred_tools()

        core_names = {s["name"] for s in core}
        deferred_names = {e.name for e in deferred}

        # 6 个核心（5 个核心 + search_tools）
        assert len(core) == 6
        # 11 个延迟
        assert len(deferred) == 11
        # 总共 17
        assert len(all_tools) == 17

        # 验证核心工具
        assert "read_file" in core_names
        assert "write_file" in core_names
        assert "search_files" in core_names
        assert "patch" in core_names
        assert "terminal" in core_names
        assert "search_tools" in core_names

        # 验证延迟工具
        assert "execute_code" in deferred_names
        assert "process" in deferred_names
        assert "todo" in deferred_names
        assert "memory" in deferred_names
        assert "session_search" in deferred_names
        assert "clarify" in deferred_names
        assert "skill_view" in deferred_names
        assert "skills_list" in deferred_names
        assert "skill_manage" in deferred_names
        assert "delegate_task" in deferred_names
        assert "cronjob" in deferred_names


# ============================================================================
# 7.5-7.7: ToolSearch BM25 + Regex + Auto
# ============================================================================

class TestBM25Search:
    """测试 BM25 索引构建和评分。"""

    def _sample_tools(self):
        return [
            {"name": "read_file", "description": "Read a text file with line numbers", "parameters": {"properties": {"path": {"description": "File path to read"}}}},
            {"name": "write_file", "description": "Write content to a file", "parameters": {"properties": {"path": {"description": "File path to write"}, "content": {"description": "Content to write"}}}},
            {"name": "send_email", "description": "Send an email to a user", "parameters": {"properties": {"to": {"description": "Recipient email"}, "subject": {"description": "Email subject"}}}},
            {"name": "get_weather", "description": "Get weather data for a location", "parameters": {"properties": {"city": {"description": "City name"}}}},
        ]

    def test_index_builds(self):
        """索引从工具列表构建。"""
        searcher = ToolSearch(self._sample_tools())
        assert searcher.tool_count == 4

    def test_bm25_finds_relevant_tools(self):
        """BM25 搜索返回相关工具。"""
        searcher = ToolSearch(self._sample_tools())
        results = searcher.search("read a file", mode="bm25")
        assert len(results) > 0
        assert results[0]["name"] == "read_file"

    def test_bm25_respects_top_k(self):
        """BM25 搜索尊重 top_k 限制。"""
        searcher = ToolSearch(self._sample_tools())
        results = searcher.search("file", mode="bm25", top_k=1)
        assert len(results) == 1

    def test_empty_query(self):
        """空索引返回空结果。"""
        searcher = ToolSearch([])
        assert searcher.search("anything") == []


class TestRegexSearch:
    """测试 Regex 搜索匹配和无效正则处理。"""

    def _sample_tools(self):
        return [
            {"name": "read_file", "description": "Read a text file", "parameters": {"properties": {}}},
            {"name": "write_file", "description": "Write to a file", "parameters": {"properties": {}}},
            {"name": "get_weather_data", "description": "Get weather", "parameters": {"properties": {}}},
        ]

    def test_regex_matches_tool_names(self):
        """Regex 匹配工具名。"""
        searcher = ToolSearch(self._sample_tools())
        results = searcher.search("get_.*_data", mode="regex")
        assert len(results) == 1
        assert results[0]["name"] == "get_weather_data"

    def test_invalid_regex_returns_empty(self):
        """无效正则返回空列表。"""
        searcher = ToolSearch(self._sample_tools())
        results = searcher.search("[invalid", mode="regex")
        assert results == []

    def test_regex_case_insensitive(self):
        """Regex 不区分大小写。"""
        searcher = ToolSearch(self._sample_tools())
        results = searcher.search("READ", mode="regex")
        assert len(results) == 1
        assert results[0]["name"] == "read_file"


class TestAutoMode:
    """测试 Auto 模式策略选择。"""

    def _sample_tools(self):
        return [
            {"name": "send_message", "description": "Send a message to a user", "parameters": {"properties": {}}},
            {"name": "get_user_data", "description": "Get user data from API", "parameters": {"properties": {}}},
        ]

    def test_auto_detects_regex(self):
        """Auto 模式检测正则。"""
        searcher = ToolSearch(self._sample_tools())
        results = searcher.search("get_.*_data")
        assert len(results) == 1
        assert results[0]["name"] == "get_user_data"

    def test_auto_defaults_to_bm25(self):
        """Auto 模式默认使用 BM25。"""
        searcher = ToolSearch(self._sample_tools())
        results = searcher.search("send a message")
        assert len(results) > 0
        assert results[0]["name"] == "send_message"


# ============================================================================
# 7.8: search_tools 工具调用
# ============================================================================

class TestSearchToolsTool:
    """测试 search_tools 工具调用返回正确 JSON。"""

    def test_returns_json_array(self, clean_registry):
        """search_tools 返回 JSON 数组。"""
        from src.tools.search_tool import search_tools

        # 注册一个延迟工具
        register_tool(
            name="send_email",
            toolset="email",
            schema={"name": "send_email", "description": "Send an email", "parameters": {"properties": {}}},
            handler=lambda: "sent",
            defer_loading=True,
        )

        result = search_tools(query="send email")
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "send_email"

    def test_empty_query_returns_empty_array(self):
        """空查询返回空数组。"""
        from src.tools.search_tool import search_tools
        result = search_tools(query="")
        assert json.loads(result) == []

    def test_no_deferred_tools_returns_empty(self, clean_registry):
        """没有延迟工具时返回空数组。"""
        from src.tools.search_tool import search_tools
        result = search_tools(query="anything")
        assert json.loads(result) == []


# ============================================================================
# 7.9: ConversationLoop 动态工具发现
# ============================================================================

class TestConversationLoopDynamicTools:
    """测试 ConversationLoop 动态工具发现和合并。"""

    def test_discovers_tools_from_search_result(self):
        """ConversationLoop 从 search_tools 结果中发现工具。"""
        from src.conversation.loop import ConversationLoop

        loop = ConversationLoop()
        loop._always_loaded_schemas = [{"name": "core_tool"}]

        # 模拟 search_tools 返回结果
        search_result = json.dumps([
            {"name": "discovered_a", "description": "Tool A"},
            {"name": "discovered_b", "description": "Tool B"},
        ])
        loop._process_search_result(search_result)

        assert "discovered_a" in loop._discovered_tools
        assert "discovered_b" in loop._discovered_tools

    def test_merges_always_loaded_and_discovered(self):
        """合并 always_loaded + discovered tools。"""
        from src.conversation.loop import ConversationLoop

        loop = ConversationLoop()
        loop._always_loaded_schemas = [{"name": "core"}]
        loop._discovered_tools = {
            "extra": {"name": "extra"},
        }

        current = loop._get_current_tools()
        names = {t["name"] for t in current}
        assert names == {"core", "extra"}

    def test_discovered_overrides_always_loaded(self):
        """Discovered tools 覆盖 always_loaded 中的同名工具。"""
        from src.conversation.loop import ConversationLoop

        loop = ConversationLoop()
        loop._always_loaded_schemas = [{"name": "shared", "version": 1}]
        loop._discovered_tools = {
            "shared": {"name": "shared", "version": 2},
        }

        current = loop._get_current_tools()
        shared = [t for t in current if t["name"] == "shared"][0]
        assert shared["version"] == 2

    def test_empty_tools_returns_none(self):
        """空工具集返回 None。"""
        from src.conversation.loop import ConversationLoop

        loop = ConversationLoop()
        assert loop._get_current_tools() is None
