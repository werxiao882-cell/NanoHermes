"""Tests for memory provider module."""

import pytest
from unittest.mock import MagicMock

from src.memory.provider import MemoryProvider


class ConcreteMemoryProvider(MemoryProvider):
    """Concrete implementation for testing."""

    @property
    def name(self) -> str:
        return "test_provider"

    @property
    def is_external(self) -> bool:
        return False


class TestMemoryProvider:
    """Tests for MemoryProvider abstract base class."""

    def test_name_property(self):
        """Test name property returns provider name."""
        provider = ConcreteMemoryProvider()
        assert provider.name == "test_provider"

    def test_is_external_default(self):
        """Test is_external returns False by default."""
        provider = ConcreteMemoryProvider()
        assert provider.is_external is False

    def test_initialize_does_nothing(self):
        """Test initialize does nothing by default."""
        provider = ConcreteMemoryProvider()
        # Should not raise
        provider.initialize({})

    def test_prefetch_returns_empty(self):
        """Test prefetch returns empty string by default."""
        provider = ConcreteMemoryProvider()
        result = provider.prefetch("test query")
        assert result == ""

    def test_sync_turn_does_nothing(self):
        """Test sync_turn does nothing by default."""
        provider = ConcreteMemoryProvider()
        # Should not raise
        provider.sync_turn([{"role": "user", "content": "test"}])

    def test_shutdown_does_nothing(self):
        """Test shutdown does nothing by default."""
        provider = ConcreteMemoryProvider()
        # Should not raise
        provider.shutdown()

    def test_on_turn_start_does_nothing(self):
        """Test on_turn_start does nothing by default."""
        provider = ConcreteMemoryProvider()
        # Should not raise
        provider.on_turn_start([{"role": "user", "content": "test"}])

    def test_on_session_end_does_nothing(self):
        """Test on_session_end does nothing by default."""
        provider = ConcreteMemoryProvider()
        # Should not raise
        provider.on_session_end("session_123")

    def test_on_session_switch_does_nothing(self):
        """Test on_session_switch does nothing by default."""
        provider = ConcreteMemoryProvider()
        # Should not raise
        provider.on_session_switch("session_456")

    def test_on_pre_compress_does_nothing(self):
        """Test on_pre_compress does nothing by default."""
        provider = ConcreteMemoryProvider()
        # Should not raise
        provider.on_pre_compress("session_123")

    def test_on_delegation_returns_empty(self):
        """Test on_delegation returns empty string by default."""
        provider = ConcreteMemoryProvider()
        result = provider.on_delegation("test task")
        assert result == ""

    def test_on_memory_write_does_nothing(self):
        """Test on_memory_write does nothing by default."""
        provider = ConcreteMemoryProvider()
        # Should not raise
        provider.on_memory_write("add", "test content")


class TestMemoryProviderSubclass:
    """Tests for custom MemoryProvider subclass."""

    def test_custom_provider_can_override_methods(self):
        """Test that custom provider can override methods."""

        class CustomProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "custom"

            @property
            def is_external(self) -> bool:
                return True

            def prefetch(self, query: str) -> str:
                return f"Prefetched: {query}"

        provider = CustomProvider()
        assert provider.name == "custom"
        assert provider.is_external is True
        assert provider.prefetch("test") == "Prefetched: test"

    def test_custom_provider_inherits_optional_hooks(self):
        """Test that custom provider inherits optional hooks."""

        class MinimalProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "minimal"

        provider = MinimalProvider()
        # All optional hooks should work without error
        provider.on_turn_start([])
        provider.on_session_end("test")
        provider.on_session_switch("test")
        provider.on_pre_compress("test")
        result = provider.on_delegation("test")
        assert result == ""
        provider.on_memory_write("add", "test")
