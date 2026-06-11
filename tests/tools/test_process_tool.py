"""Tests for process tools module."""

import pytest
import json

from src.tools.impls.process_tool import process


class TestProcessTool:
    """Tests for process tool function."""

    def test_process_list(self):
        """Test listing processes."""
        result = json.loads(process(action="list"))
        assert result["status"] in ("process_requested", "success")
        assert result["action"] == "list"

    def test_process_stop(self):
        """Test stopping a process."""
        result = json.loads(process(action="stop", process_id="proc123"))
        # 进程不存在时返回 error
        assert result["status"] in ("process_requested", "error")

    def test_process_via_dispatcher(self):
        """Test process tool via dispatcher."""
        from src.tools.core.registry import ToolRegistry
        from src.tools.impls import process_tool
        import importlib
        from src.tools.core.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(process_tool)

        result = dispatch("process", {"action": "list"})
        data = json.loads(result)
        assert data["status"] in ("process_requested", "success", "error")

