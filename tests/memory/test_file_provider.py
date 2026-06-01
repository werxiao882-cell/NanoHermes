"""FileMemoryProvider 单元测试。"""

import json
import tempfile
from pathlib import Path

import pytest

from src.memory.file_provider import FileMemoryProvider


@pytest.fixture
def hermes_home():
    """创建临时 hermes_home 目录。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def provider(hermes_home):
    """创建 FileMemoryProvider 实例。"""
    return FileMemoryProvider(str(hermes_home))


class TestFileMemoryProviderInit:
    """测试 FileMemoryProvider 初始化。"""

    def test_create_memory_and_user_files(self, provider, hermes_home):
        """测试创建 MEMORY.md 和 USER.md。"""
        provider.initialize("session-1")

        assert (hermes_home / "MEMORY.md").exists()
        assert (hermes_home / "USER.md").exists()

    def test_not_overwrite_existing_files(self, provider, hermes_home):
        """测试不覆盖已存在的文件。"""
        memory_path = hermes_home / "MEMORY.md"
        memory_path.write_text("# Existing Memory\n\n- Existing fact\n", encoding="utf-8")

        provider.initialize("session-1")

        content = memory_path.read_text(encoding="utf-8")
        assert "Existing fact" in content


class TestFileMemoryProviderPrefetch:
    """测试 prefetch 方法。"""

    def test_return_full_memory_content(self, provider, hermes_home):
        """测试返回完整记忆内容。"""
        memory_path = hermes_home / "MEMORY.md"
        memory_path.write_text("- User prefers Python\n", encoding="utf-8")

        provider.initialize("session-1")
        result = provider.prefetch("")

        assert "## Memory" in result
        assert "User prefers Python" in result

    def test_empty_files_return_empty(self, provider, hermes_home):
        """测试空文件返回空字符串。"""
        memory_path = hermes_home / "MEMORY.md"
        user_path = hermes_home / "USER.md"
        memory_path.write_text("", encoding="utf-8")
        user_path.write_text("", encoding="utf-8")

        provider.initialize("session-1")
        result = provider.prefetch("")

        assert result == ""

    def test_system_prompt_block_returns_prefetch(self, provider, hermes_home):
        """测试 system_prompt_block 返回 prefetch 内容。"""
        memory_path = hermes_home / "MEMORY.md"
        memory_path.write_text("- Test memory\n", encoding="utf-8")

        provider.initialize("session-1")
        result = provider.system_prompt_block()

        assert "Test memory" in result


class TestFileMemoryProviderActions:
    """测试 add/replace/remove 操作。"""

    def test_add_memory_entry(self, provider, hermes_home):
        """测试添加记忆条目。"""
        provider.initialize("session-1")
        result = provider._handle_memory_action({
            "action": "add",
            "target": "memory",
            "content": "New fact"
        })

        assert json.loads(result)["success"] is True

        memory_path = hermes_home / "MEMORY.md"
        content = memory_path.read_text(encoding="utf-8")
        assert "- New fact" in content

    def test_replace_memory_entry(self, provider, hermes_home):
        """测试替换记忆条目。"""
        memory_path = hermes_home / "MEMORY.md"
        memory_path.write_text("- Old fact\n", encoding="utf-8")

        provider.initialize("session-1")
        result = provider._handle_memory_action({
            "action": "replace",
            "target": "memory",
            "content": "New fact",
            "search": "Old fact"
        })

        assert json.loads(result)["success"] is True

        content = memory_path.read_text(encoding="utf-8")
        assert "- New fact" in content
        assert "Old fact" not in content

    def test_remove_memory_entry(self, provider, hermes_home):
        """测试删除记忆条目。"""
        memory_path = hermes_home / "MEMORY.md"
        memory_path.write_text("- Fact to remove\n- Keep this\n", encoding="utf-8")

        provider.initialize("session-1")
        result = provider._handle_memory_action({
            "action": "remove",
            "target": "memory",
            "content": "Fact to remove",
            "search": "Fact to remove"
        })

        assert json.loads(result)["success"] is True

        content = memory_path.read_text(encoding="utf-8")
        assert "Fact to remove" not in content
        assert "Keep this" in content

    def test_add_user_entry(self, provider, hermes_home):
        """测试添加用户条目。"""
        provider.initialize("session-1")
        result = provider._handle_memory_action({
            "action": "add",
            "target": "user",
            "content": "User is a developer"
        })

        assert json.loads(result)["success"] is True

        user_path = hermes_home / "USER.md"
        content = user_path.read_text(encoding="utf-8")
        assert "- User is a developer" in content


class TestFileMemoryProviderAtomicWrite:
    """测试原子写入。"""

    def test_atomic_write_creates_temp_file(self, provider, hermes_home):
        """测试原子写入创建临时文件。"""
        memory_path = hermes_home / "MEMORY.md"
        memory_path.write_text("# Memory\n\n", encoding="utf-8")

        provider._atomic_write(memory_path, "- New content\n")

        # 临时文件不应存在
        assert not (hermes_home / "MEMORY.tmp").exists()
        # 目标文件应包含新内容
        content = memory_path.read_text(encoding="utf-8")
        assert "- New content" in content


class TestFileMemoryProviderToolSchema:
    """测试工具 schema。"""

    def test_get_tool_schemas(self, provider):
        """测试返回工具 schema。"""
        schemas = provider.get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "memory"
        assert "action" in schemas[0]["parameters"]["properties"]
        assert "target" in schemas[0]["parameters"]["properties"]
        assert "content" in schemas[0]["parameters"]["properties"]

    def test_handle_tool_call_memory(self, provider, hermes_home):
        """测试处理 memory 工具调用。"""
        provider.initialize("session-1")
        result = provider.handle_tool_call("memory", {
            "action": "add",
            "target": "memory",
            "content": "Test via tool"
        })

        assert json.loads(result)["success"] is True

    def test_handle_tool_call_unknown_raises(self, provider):
        """测试未知工具抛出异常。"""
        with pytest.raises(NotImplementedError):
            provider.handle_tool_call("unknown", {})


class TestFileMemoryProviderCharLimits:
    """测试字符数限制。"""

    def test_truncate_long_memory_content(self, provider, hermes_home):
        """测试截断过长的记忆内容。"""
        memory_path = hermes_home / "MEMORY.md"
        long_content = "A" * 3000
        memory_path.write_text(long_content, encoding="utf-8")

        provider.initialize("session-1")
        result = provider.prefetch("")

        # 内容应被截断到 2200 字符
        assert len(result) < 3000

    def test_truncate_long_user_content(self, provider, hermes_home):
        """测试截断过长的用户内容。"""
        user_path = hermes_home / "USER.md"
        long_content = "B" * 2000
        user_path.write_text(long_content, encoding="utf-8")

        provider.initialize("session-1")
        result = provider.prefetch("")

        # 内容应被截断到 1375 字符
        assert len(result) < 2000
