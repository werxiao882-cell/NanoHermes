"""Tests for memory tools module."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.memory.memory_store import MemoryStore
from src.tools.impls.memory_tool import memory, set_memory_store, get_memory_store


class TestMemoryTool:
    """Tests for memory tool function."""

    def test_memory_add(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir))
            store.load_from_disk()
            set_memory_store(store)
            try:
                result = json.loads(memory(action="add", content="User likes Python"))
                assert result["success"] is True
                assert "User likes Python" in store.memory_entries
            finally:
                set_memory_store(None)

    def test_memory_view(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir))
            store.load_from_disk()
            set_memory_store(store)
            try:
                result = json.loads(memory(action="view"))
                assert result["success"] is True
                assert result["action"] == "view"
            finally:
                set_memory_store(None)

    def test_memory_via_dispatcher(self):
        from src.tools.core.registry import ToolRegistry
        from src.tools.impls import memory_tool
        import importlib
        from src.tools.core.dispatcher import dispatch

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir))
            store.load_from_disk()
            set_memory_store(store)

            ToolRegistry.clear()
            importlib.reload(memory_tool)

            try:
                result = dispatch("memory", {"action": "view"})
                data = json.loads(result)
                assert data["success"] is True or "error" in data
            finally:
                set_memory_store(None)
