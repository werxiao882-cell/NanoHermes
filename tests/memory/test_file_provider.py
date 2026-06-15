"""FileMemoryProvider 单元测试。

重构后：FileMemoryProvider 委托 MemoryStore，测试验证委托行为。
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.memory.memory_store import MemoryStore, ENTRY_DELIMITER
from src.memory.file_provider import FileMemoryProvider


@pytest.fixture
def hermes_home():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def store(hermes_home):
    memory_dir = hermes_home / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    s = MemoryStore(memory_dir)
    s.load_from_disk()
    return s


@pytest.fixture
def provider(hermes_home, store):
    return FileMemoryProvider(str(hermes_home), store=store)


class TestFileMemoryProviderInit:
    """测试 FileMemoryProvider 初始化。"""

    def test_initialize_loads_from_disk(self, provider, hermes_home):
        memory_path = hermes_home / "memory" / "MEMORY.md"
        memory_path.write_text("Existing fact", encoding="utf-8")
        provider.initialize("session-1")
        assert "Existing fact" in provider._store.memory_entries

    def test_not_overwrite_existing_files(self, provider, hermes_home):
        memory_path = hermes_home / "memory" / "MEMORY.md"
        memory_path.write_text("Existing fact", encoding="utf-8")
        provider.initialize("session-1")
        content = memory_path.read_text(encoding="utf-8")
        assert "Existing fact" in content


class TestFileMemoryProviderPrefetch:
    """测试 prefetch 方法。"""

    def test_return_memory_content(self, provider, hermes_home):
        memory_path = hermes_home / "memory" / "MEMORY.md"
        memory_path.write_text("User prefers Python", encoding="utf-8")
        provider.initialize("session-1")
        result = provider.prefetch("")
        assert "User prefers Python" in result

    def test_empty_files_return_empty(self, provider, hermes_home):
        provider.initialize("session-1")
        result = provider.prefetch("")
        assert result == ""

    def test_system_prompt_block_returns_prefetch(self, provider, hermes_home):
        memory_path = hermes_home / "memory" / "MEMORY.md"
        memory_path.write_text("Test memory", encoding="utf-8")
        provider.initialize("session-1")
        result = provider.system_prompt_block()
        assert "Test memory" in result


class TestFileMemoryProviderActions:
    """测试 add/replace/remove 操作。"""

    def test_add_memory_entry(self, provider, hermes_home):
        provider.initialize("session-1")
        result = provider._handle_memory_action({
            "action": "add",
            "target": "memory",
            "content": "New fact"
        })
        data = json.loads(result)
        assert data["success"] is True
        assert "New fact" in provider._store.memory_entries

    def test_replace_memory_entry(self, provider, hermes_home):
        provider.initialize("session-1")
        provider._handle_memory_action({
            "action": "add",
            "target": "memory",
            "content": "Old fact"
        })
        result = provider._handle_memory_action({
            "action": "replace",
            "target": "memory",
            "content": "New fact",
            "search": "Old fact"
        })
        data = json.loads(result)
        assert data["success"] is True
        assert any("New fact" in e for e in provider._store.memory_entries)

    def test_remove_memory_entry(self, provider, hermes_home):
        provider.initialize("session-1")
        provider._handle_memory_action({
            "action": "add",
            "target": "memory",
            "content": "Fact to remove"
        })
        provider._handle_memory_action({
            "action": "add",
            "target": "memory",
            "content": "Keep this"
        })
        result = provider._handle_memory_action({
            "action": "remove",
            "target": "memory",
            "content": "Fact to remove",
            "search": "Fact to remove"
        })
        data = json.loads(result)
        assert data["success"] is True
        assert not any("Fact to remove" in e for e in provider._store.memory_entries)
        assert any("Keep this" in e for e in provider._store.memory_entries)

    def test_add_user_entry(self, provider, hermes_home):
        provider.initialize("session-1")
        result = provider._handle_memory_action({
            "action": "add",
            "target": "user",
            "content": "User is a developer"
        })
        data = json.loads(result)
        assert data["success"] is True
        assert "User is a developer" in provider._store.user_entries


class TestFileMemoryProviderToolSchema:
    """测试工具 schema。"""

    def test_get_tool_schemas(self, provider):
        schemas = provider.get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "memory"
        assert "action" in schemas[0]["parameters"]["properties"]
        assert "target" in schemas[0]["parameters"]["properties"]
        assert "content" in schemas[0]["parameters"]["properties"]

    def test_handle_tool_call_memory(self, provider, hermes_home):
        provider.initialize("session-1")
        result = provider.handle_tool_call("memory", {
            "action": "add",
            "target": "memory",
            "content": "Test via tool"
        })
        assert json.loads(result)["success"] is True

    def test_handle_tool_call_unknown_raises(self, provider):
        with pytest.raises(NotImplementedError):
            provider.handle_tool_call("unknown", {})


class TestFileMemoryProviderCharLimits:
    """测试字符数限制。"""

    def test_add_respects_memory_limit(self, provider, hermes_home):
        provider.initialize("session-1")
        long_content = "A" * 2190
        result = provider._handle_memory_action({
            "action": "add",
            "target": "memory",
            "content": long_content
        })
        assert json.loads(result)["success"] is True

        result2 = provider._handle_memory_action({
            "action": "add",
            "target": "memory",
            "content": "This would exceed limit"
        })
        assert json.loads(result2)["success"] is False

    def test_add_respects_user_limit(self, provider, hermes_home):
        provider.initialize("session-1")
        long_content = "B" * 1370
        result = provider._handle_memory_action({
            "action": "add",
            "target": "user",
            "content": long_content
        })
        assert json.loads(result)["success"] is True

        result2 = provider._handle_memory_action({
            "action": "add",
            "target": "user",
            "content": "This would exceed limit"
        })
        assert json.loads(result2)["success"] is False
