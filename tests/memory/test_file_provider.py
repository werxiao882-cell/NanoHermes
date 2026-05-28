"""Tests for file memory provider module."""

import pytest
import tempfile
from pathlib import Path

from src.memory.file_provider import FileMemoryProvider


class TestFileMemoryProvider:
    """Tests for FileMemoryProvider class."""

    def test_init_default_dir(self):
        """Test initialization with default directory."""
        provider = FileMemoryProvider()
        assert provider._base_dir == Path.cwd()

    def test_init_custom_dir(self):
        """Test initialization with custom directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = FileMemoryProvider(tmpdir)
            assert provider._base_dir == Path(tmpdir)

    def test_name_property(self):
        """Test name property returns 'file'."""
        provider = FileMemoryProvider()
        assert provider.name == "file"

    def test_is_external_property(self):
        """Test is_external returns False."""
        provider = FileMemoryProvider()
        assert provider.is_external is False

    def test_initialize_creates_files(self):
        """Test initialize creates MEMORY.md and USER.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = FileMemoryProvider(tmpdir)
            provider.initialize({})

            memory_file = Path(tmpdir) / "MEMORY.md"
            user_file = Path(tmpdir) / "USER.md"

            assert memory_file.exists()
            assert user_file.exists()

    def test_initialize_does_not_overwrite(self):
        """Test initialize doesn't overwrite existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            memory_file.write_text("# Existing Memory", encoding="utf-8")

            provider = FileMemoryProvider(tmpdir)
            provider.initialize({})

            content = memory_file.read_text(encoding="utf-8")
            assert content == "# Existing Memory"

    def test_prefetch_returns_content(self):
        """Test prefetch returns file contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            memory_file.write_text("# Memory\n\nTest memory content", encoding="utf-8")

            user_file = Path(tmpdir) / "USER.md"
            user_file.write_text("# User\n\nTest user content", encoding="utf-8")

            provider = FileMemoryProvider(tmpdir)
            result = provider.prefetch()

            assert "Test memory content" in result
            assert "Test user content" in result

    def test_prefetch_empty_files(self):
        """Test prefetch handles empty files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            memory_file.write_text("", encoding="utf-8")

            user_file = Path(tmpdir) / "USER.md"
            user_file.write_text("", encoding="utf-8")

            provider = FileMemoryProvider(tmpdir)
            result = provider.prefetch()

            assert result == ""

    def test_prefetch_missing_files(self):
        """Test prefetch handles missing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = FileMemoryProvider(tmpdir)
            # Don't initialize, files don't exist
            result = provider.prefetch()
            assert result == ""

    def test_add_entry(self):
        """Test add_entry appends to MEMORY.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = FileMemoryProvider(tmpdir)
            provider.initialize({})

            provider.add_entry("Test Section", "Test content")

            memory_file = Path(tmpdir) / "MEMORY.md"
            content = memory_file.read_text(encoding="utf-8")

            assert "## Test Section" in content
            assert "Test content" in content

    def test_replace_entry(self):
        """Test replace_entry updates content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = FileMemoryProvider(tmpdir)
            provider.initialize({})

            provider.replace_entry("Test Section", "New content")

            memory_file = Path(tmpdir) / "MEMORY.md"
            content = memory_file.read_text(encoding="utf-8")

            assert "## Test Section" in content
            assert "New content" in content

    def test_remove_entry(self):
        """Test remove_entry is implemented (no-op for now)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = FileMemoryProvider(tmpdir)
            provider.initialize({})

            # Should not raise
            provider.remove_entry("Test Section")

    def test_sync_turn(self):
        """Test sync_turn is implemented (no-op for now)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = FileMemoryProvider(tmpdir)
            # Should not raise
            provider.sync_turn([{"role": "user", "content": "test"}])
