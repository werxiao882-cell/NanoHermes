"""Tests for memory tools module."""

import pytest
import json

from src.tools.memory_tools import memory


class TestMemoryTool:
    """Tests for memory tool function."""

    def test_memory_add(self):
        """Test adding memory."""
        result = json.loads(memory(action="add", content="User likes Python"))
        assert result["status"] == "memory_requested"
        assert result["action"] == "add"

    def test_memory_view(self):
        """Test viewing memory."""
        result = json.loads(memory(action="view"))
        assert result["status"] == "memory_requested"
        assert result["action"] == "view"

    def test_memory_via_dispatcher(self):
        """Test memory tool via dispatcher."""
        from src.tools.registry import ToolRegistry
        from src.tools import memory_tools
        import importlib
        from src.tools.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(memory_tools)

        result = dispatch("memory", {"action": "view"})
        data = json.loads(result)
        assert data["status"] == "memory_requested"
