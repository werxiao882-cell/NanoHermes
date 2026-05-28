"""Tests for memory manager module."""

import pytest
from unittest.mock import MagicMock

from src.memory.provider import MemoryProvider
from src.memory.managers import MemoryManager, MEMORY_CONTEXT_OPEN, MEMORY_CONTEXT_CLOSE


class MockMemoryProvider(MemoryProvider):
    """Mock provider for testing."""

    def __init__(self, name: str, is_external: bool = False, prefetch_content: str = ""):
        self._name = name
        self._is_external = is_external
        self._prefetch_content = prefetch_content
        self.initialize_called = False
        self.sync_turn_called = False
        self.shutdown_called = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_external(self) -> bool:
        return self._is_external

    def initialize(self, options: dict) -> None:
        self.initialize_called = True

    def prefetch(self, query: str) -> str:
        return self._prefetch_content

    def sync_turn(self, messages: list) -> None:
        self.sync_turn_called = True

    def shutdown(self) -> None:
        self.shutdown_called = True


class TestMemoryManager:
    """Tests for MemoryManager class."""

    def test_init_empty(self):
        """Test initialization with no providers."""
        manager = MemoryManager()
        assert manager._providers == []
        assert manager._external_count == 0

    def test_add_builtin_provider(self):
        """Test adding a builtin provider."""
        manager = MemoryManager()
        provider = MockMemoryProvider("builtin", is_external=False)
        manager.add_provider(provider)
        assert len(manager._providers) == 1
        assert manager._external_count == 0

    def test_add_external_provider(self):
        """Test adding an external provider."""
        manager = MemoryManager()
        provider = MockMemoryProvider("external", is_external=True)
        manager.add_provider(provider)
        assert len(manager._providers) == 1
        assert manager._external_count == 1

    def test_add_second_external_provider_raises(self):
        """Test adding second external provider raises ValueError."""
        manager = MemoryManager()
        manager.add_provider(MockMemoryProvider("ext1", is_external=True))

        with pytest.raises(ValueError, match="只允许注册一个外部记忆提供者"):
            manager.add_provider(MockMemoryProvider("ext2", is_external=True))

    def test_add_multiple_builtin_providers(self):
        """Test adding multiple builtin providers."""
        manager = MemoryManager()
        manager.add_provider(MockMemoryProvider("builtin1"))
        manager.add_provider(MockMemoryProvider("builtin2"))
        assert len(manager._providers) == 2

    def test_initialize_all(self):
        """Test initialize_all calls initialize on all providers."""
        manager = MemoryManager()
        p1 = MockMemoryProvider("p1")
        p2 = MockMemoryProvider("p2")
        manager.add_provider(p1)
        manager.add_provider(p2)

        manager.initialize_all({"key": "value"})

        assert p1.initialize_called is True
        assert p2.initialize_called is True

    def test_prefetch_all_empty(self):
        """Test prefetch_all returns empty when no providers."""
        manager = MemoryManager()
        result = manager.prefetch_all("query")
        assert result == ""

    def test_prefetch_all_with_content(self):
        """Test prefetch_all returns wrapped content."""
        manager = MemoryManager()
        provider = MockMemoryProvider("test", prefetch_content="Memory content")
        manager.add_provider(provider)

        result = manager.prefetch_all("query")

        assert MEMORY_CONTEXT_OPEN in result
        assert "Memory content" in result
        assert MEMORY_CONTEXT_CLOSE in result

    def test_prefetch_all_skips_empty(self):
        """Test prefetch_all skips providers with empty content."""
        manager = MemoryManager()
        p1 = MockMemoryProvider("p1", prefetch_content="")
        p2 = MockMemoryProvider("p2", prefetch_content="Content")
        manager.add_provider(p1)
        manager.add_provider(p2)

        result = manager.prefetch_all("query")

        assert "p1" not in result
        assert "Content" in result

    def test_prefetch_all_multiple_providers(self):
        """Test prefetch_all combines content from multiple providers."""
        manager = MemoryManager()
        p1 = MockMemoryProvider("p1", prefetch_content="Content 1")
        p2 = MockMemoryProvider("p2", prefetch_content="Content 2")
        manager.add_provider(p1)
        manager.add_provider(p2)

        result = manager.prefetch_all("query")

        assert "Content 1" in result
        assert "Content 2" in result
        assert "p1" in result
        assert "p2" in result

    def test_sync_all(self):
        """Test sync_all calls sync_turn on all providers."""
        manager = MemoryManager()
        p1 = MockMemoryProvider("p1")
        p2 = MockMemoryProvider("p2")
        manager.add_provider(p1)
        manager.add_provider(p2)

        messages = [{"role": "user", "content": "test"}]
        manager.sync_all(messages)

        assert p1.sync_turn_called is True
        assert p2.sync_turn_called is True

    def test_shutdown_all(self):
        """Test shutdown_all calls shutdown on all providers."""
        manager = MemoryManager()
        p1 = MockMemoryProvider("p1")
        p2 = MockMemoryProvider("p2")
        manager.add_provider(p1)
        manager.add_provider(p2)

        manager.shutdown_all()

        assert p1.shutdown_called is True
        assert p2.shutdown_called is True

    def test_build_system_prompt_section(self):
        """Test build_system_prompt_section delegates to prefetch_all."""
        manager = MemoryManager()
        provider = MockMemoryProvider("test", prefetch_content="Memory")
        manager.add_provider(provider)

        result = manager.build_system_prompt_section("query")

        assert MEMORY_CONTEXT_OPEN in result
        assert "Memory" in result

    def test_build_system_prompt_section_empty(self):
        """Test build_system_prompt_section returns empty when no content."""
        manager = MemoryManager()
        provider = MockMemoryProvider("test", prefetch_content="")
        manager.add_provider(provider)

        result = manager.build_system_prompt_section("query")

        assert result == ""


class TestMemoryContextConstants:
    """Tests for memory context constants."""

    def test_context_open_tag(self):
        """Test context open tag format."""
        assert MEMORY_CONTEXT_OPEN == "<memory-context>"

    def test_context_close_tag(self):
        """Test context close tag format."""
        assert MEMORY_CONTEXT_CLOSE == "</memory-context>"
