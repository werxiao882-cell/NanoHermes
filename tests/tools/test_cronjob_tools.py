"""Tests for cronjob tools module."""

import pytest
import json

from src.tools.cronjob_tools import cronjob


class TestCronjobTool:
    """Tests for cronjob tool function."""

    def test_cronjob_list(self):
        """Test listing cron jobs."""
        result = json.loads(cronjob(action="list"))
        assert result["status"] == "success"
        assert result["jobs"] == []

    def test_cronjob_add(self):
        """Test adding a cron job."""
        result = json.loads(cronjob(action="add", schedule="30m", prompt="Test task"))
        assert result["status"] == "cronjob_requested"
        assert result["action"] == "add"

    def test_cronjob_remove(self):
        """Test removing a cron job."""
        result = json.loads(cronjob(action="remove", job_id="job123"))
        assert result["status"] == "cronjob_requested"
        assert result["action"] == "remove"

    def test_cronjob_via_dispatcher(self):
        """Test cronjob tool via dispatcher."""
        from src.tools.registry import ToolRegistry
        from src.tools import cronjob_tools
        import importlib
        from src.tools.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(cronjob_tools)

        result = dispatch("cronjob", {"action": "list"})
        data = json.loads(result)
        assert data["status"] == "success"
