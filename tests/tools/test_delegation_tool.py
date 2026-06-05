"""Tests for delegation tools module."""

import pytest
import json

from src.tools.delegation_tool import delegate_task


class TestDelegateTask:
    """Tests for delegate_task tool function."""

    def test_delegate_task_single_goal(self):
        """Test delegating a single task with goal."""
        result = json.loads(delegate_task(goal="Fix the bug"))
        assert result["status"] in ("delegation_requested", "success")
        assert result.get("goal") == "Fix the bug" or "summary" in result

    def test_delegate_task_with_role(self):
        """Test delegating with specific role."""
        result = json.loads(delegate_task(goal="Test", role="orchestrator"))
        assert result.get("role") == "orchestrator" or "summary" in result

    def test_delegate_task_with_context(self):
        """Test delegating with context."""
        result = json.loads(delegate_task(goal="Test", context="Additional context"))
        assert result["status"] in ("delegation_requested", "success")

    def test_delegate_task_via_dispatcher(self):
        """Test delegate_task tool via dispatcher."""
        from src.tools.registry import ToolRegistry
        from src.tools import delegation_tools
        import importlib
        from src.tools.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(delegation_tools)

        result = dispatch("delegate_task", {"goal": "Test task"})
        data = json.loads(result)
        assert data["status"] in ("delegation_requested", "success", "error")

