"""Tests for prompt assembler module."""

import pytest

from src.prompt.assembler import PromptAssembler


class TestPromptAssembler:
    """Tests for PromptAssembler class."""

    def test_init_empty(self):
        """Test initialization with empty parts."""
        assembler = PromptAssembler()
        assert assembler._stable_parts == []
        assert assembler._context_parts == []
        assert assembler._volatile_parts == []

    def test_set_stable(self):
        """Test setting stable parts."""
        assembler = PromptAssembler()
        assembler.set_stable(["Identity", "Tools"])
        assert assembler._stable_parts == ["Identity", "Tools"]

    def test_set_context(self):
        """Test setting context parts."""
        assembler = PromptAssembler()
        assembler.set_context(["Context file", "System message"])
        assert assembler._context_parts == ["Context file", "System message"]

    def test_set_volatile(self):
        """Test setting volatile parts."""
        assembler = PromptAssembler()
        assembler.set_volatile(["Memory", "User profile"])
        assert assembler._volatile_parts == ["Memory", "User profile"]

    def test_assemble_empty(self):
        """Test assemble returns empty string when no parts."""
        assembler = PromptAssembler()
        result = assembler.assemble()
        assert result == ""

    def test_assemble_stable_only(self):
        """Test assemble with only stable parts."""
        assembler = PromptAssembler()
        assembler.set_stable(["Identity", "Tools"])
        result = assembler.assemble()
        assert "Identity" in result
        assert "Tools" in result

    def test_assemble_all_parts(self):
        """Test assemble with all parts."""
        assembler = PromptAssembler()
        assembler.set_stable(["Identity"])
        assembler.set_context(["Context"])
        assembler.set_volatile(["Memory"])

        result = assembler.assemble()

        assert "Identity" in result
        assert "Context" in result
        assert "Memory" in result
        # Parts should be separated by double newlines
        assert "\n\n" in result

    def test_assemble_joins_parts_with_newlines(self):
        """Test assemble joins parts within each layer with newlines."""
        assembler = PromptAssembler()
        assembler.set_stable(["Part1", "Part2"])
        result = assembler.assemble()
        assert "Part1\nPart2" in result

    def test_get_stable_hash_empty(self):
        """Test get_stable_hash with empty parts."""
        assembler = PromptAssembler()
        hash1 = assembler.get_stable_hash()
        assert isinstance(hash1, int)

    def test_get_stable_hash_changes(self):
        """Test get_stable_hash changes when parts change."""
        assembler = PromptAssembler()
        assembler.set_stable(["Part1"])
        hash1 = assembler.get_stable_hash()

        assembler.set_stable(["Part2"])
        hash2 = assembler.get_stable_hash()

        assert hash1 != hash2

    def test_get_stable_hash_same(self):
        """Test get_stable_hash is same for same parts."""
        assembler = PromptAssembler()
        assembler.set_stable(["Part1", "Part2"])
        hash1 = assembler.get_stable_hash()

        assembler.set_stable(["Part1", "Part2"])
        hash2 = assembler.get_stable_hash()

        assert hash1 == hash2

    def test_set_stable_replaces(self):
        """Test set_stable replaces previous parts."""
        assembler = PromptAssembler()
        assembler.set_stable(["Old1", "Old2"])
        assembler.set_stable(["New1"])
        assert assembler._stable_parts == ["New1"]

    def test_set_context_replaces(self):
        """Test set_context replaces previous parts."""
        assembler = PromptAssembler()
        assembler.set_context(["Old"])
        assembler.set_context(["New1", "New2"])
        assert assembler._context_parts == ["New1", "New2"]

    def test_set_volatile_replaces(self):
        """Test set_volatile replaces previous parts."""
        assembler = PromptAssembler()
        assembler.set_volatile(["Old"])
        assembler.set_volatile(["New"])
        assert assembler._volatile_parts == ["New"]

    def test_assemble_order(self):
        """Test assemble maintains stable → context → volatile order."""
        assembler = PromptAssembler()
        assembler.set_stable(["Stable"])
        assembler.set_context(["Context"])
        assembler.set_volatile(["Volatile"])

        result = assembler.assemble()

        stable_pos = result.index("Stable")
        context_pos = result.index("Context")
        volatile_pos = result.index("Volatile")

        assert stable_pos < context_pos < volatile_pos
