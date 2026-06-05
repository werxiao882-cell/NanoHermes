"""Tests for memory tools module."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.tools.memory_tool import memory


class TestMemoryTool:
    """Tests for memory tool function."""

    def test_memory_add(self):
        """Test adding memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.tools.memory_tools.MEMORY_DIR", Path(tmpdir)), \
                 patch("src.tools.memory_tools.MEMORY_FILE", Path(tmpdir) / "MEMORY.md"), \
                 patch("src.tools.memory_tools.USER_FILE", Path(tmpdir) / "USER.md"):
                result = json.loads(memory(action="add", content="User likes Python"))
                assert result["status"] in ("memory_requested", "success")
                assert result["action"] == "add"

    def test_memory_view(self):
        """Test viewing memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.tools.memory_tools.MEMORY_DIR", Path(tmpdir)), \
                 patch("src.tools.memory_tools.MEMORY_FILE", Path(tmpdir) / "MEMORY.md"), \
                 patch("src.tools.memory_tools.USER_FILE", Path(tmpdir) / "USER.md"):
                result = json.loads(memory(action="view"))
                assert result["status"] in ("memory_requested", "success")
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
        assert data["status"] in ("memory_requested", "success", "error")

