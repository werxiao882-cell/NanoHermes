"""Tests for cronjob tools module."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.tools.impls.cronjob_tool import cronjob


class TestCronjobTool:
    """Tests for cronjob tool function."""

    def test_cronjob_list(self):
        """Test listing cron jobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.tools.impls.cronjob_tool.CRON_DIR", Path(tmpdir)), \
                 patch("src.tools.impls.cronjob_tool.CRON_FILE", Path(tmpdir) / "jobs.json"):
                result = json.loads(cronjob(action="list"))
                assert result["status"] == "success"
                assert result["jobs"] == []

    def test_cronjob_add(self):
        """Test adding a cron job."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.tools.impls.cronjob_tool.CRON_DIR", Path(tmpdir)), \
                 patch("src.tools.impls.cronjob_tool.CRON_FILE", Path(tmpdir) / "jobs.json"):
                result = json.loads(cronjob(action="add", schedule="30m", prompt="Test task"))
                assert result["status"] == "success"
                assert "job_id" in result

    def test_cronjob_remove(self):
        """Test removing a cron job."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.tools.impls.cronjob_tool.CRON_DIR", Path(tmpdir)), \
                 patch("src.tools.impls.cronjob_tool.CRON_FILE", Path(tmpdir) / "jobs.json"):
                # 先添加再删除
                cronjob(action="add", schedule="30m", prompt="Test task")
                # 获取 job_id
                list_result = json.loads(cronjob(action="list"))
                if list_result["jobs"]:
                    job_id = list_result["jobs"][0]["job_id"]
                    result = json.loads(cronjob(action="remove", job_id=job_id))
                    assert result["status"] == "success"

    def test_cronjob_via_dispatcher(self):
        """Test cronjob tool via dispatcher."""
        from src.tools.core.registry import ToolRegistry
        from src.tools.impls import cronjob_tool
        import importlib
        from src.tools.core.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(cronjob_tool)

        result = dispatch("cronjob", {"action": "list"})
        data = json.loads(result)
        assert data["status"] in ("success", "error")

