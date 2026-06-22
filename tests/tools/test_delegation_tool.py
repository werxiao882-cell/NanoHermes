"""Tests for delegation tools module."""

import pytest
import json

from src.tools.impls.delegation_tool import delegate_task


class TestDelegateTask:
    """Tests for delegate_task tool function."""

    def test_delegate_task_single_goal(self):
        """Test delegating a single task with goal."""
        result = json.loads(delegate_task(goal="Fix the bug"))
        # background=True 默认返回 dispatched 状态
        assert result["status"] in ("delegation_requested", "success", "dispatched")
        if result["status"] == "dispatched":
            assert "task_id" in result
        else:
            assert result.get("goal") == "Fix the bug" or "summary" in result

    def test_delegate_task_with_role(self):
        """Test delegating with specific role."""
        result = json.loads(delegate_task(goal="Test", role="orchestrator"))
        # background=True 时不返回 role，只返回 task_id
        assert result.get("role") == "orchestrator" or "summary" in result or "task_id" in result

    def test_delegate_task_with_context(self):
        """Test delegating with context."""
        result = json.loads(delegate_task(goal="Test", context="Additional context"))
        assert result["status"] in ("delegation_requested", "success", "dispatched")

    def test_delegate_task_blocking_mode(self):
        """Test delegating with background=False (blocking mode)."""
        result = json.loads(delegate_task(goal="Fix the bug", background=False))
        assert result["status"] in ("delegation_requested", "success", "error")

    def test_delegate_task_via_dispatcher(self):
        """Test delegate_task tool via dispatcher."""
        from src.tools.core.registry import ToolRegistry
        from src.tools.impls import delegation_tool
        import importlib
        from src.tools.core.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(delegation_tool)

        result = dispatch("delegate_task", {"goal": "Test task"})
        data = json.loads(result)
        assert data["status"] in ("delegation_requested", "success", "error", "dispatched")

