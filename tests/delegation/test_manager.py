"""Tests for delegation manager module."""

import pytest

from src.delegation.manager import DelegationManager, AgentRole, DelegationResult


class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_leaf_role(self):
        """Test leaf role value."""
        assert AgentRole.LEAF.value == "leaf"

    def test_orchestrator_role(self):
        """Test orchestrator role value."""
        assert AgentRole.ORCHESTRATOR.value == "orchestrator"


class TestDelegationResult:
    """Tests for DelegationResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = DelegationResult(task_id="test", success=False)
        assert result.task_id == "test"
        assert result.success is False
        assert result.summary == ""
        assert result.error == ""

    def test_success_result(self):
        """Test success result."""
        result = DelegationResult(
            task_id="test",
            success=True,
            summary="Task completed",
        )
        assert result.success is True
        assert result.summary == "Task completed"

    def test_error_result(self):
        """Test error result."""
        result = DelegationResult(
            task_id="test",
            success=False,
            error="Task failed",
        )
        assert result.success is False
        assert result.error == "Task failed"


class TestDelegationManager:
    """Tests for DelegationManager class."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        manager = DelegationManager()
        assert manager.max_concurrent == 3
        assert manager.max_depth == 2
        assert manager.timeout_seconds == 300.0
        assert manager.auto_approve is False
        assert manager._current_depth == 0

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        manager = DelegationManager(
            max_concurrent=5,
            max_depth=3,
            timeout_seconds=600.0,
            auto_approve=True,
        )
        assert manager.max_concurrent == 5
        assert manager.max_depth == 3
        assert manager.timeout_seconds == 600.0
        assert manager.auto_approve is True

    def test_delegate_task_single_goal(self):
        """Test delegating a single task with goal."""
        manager = DelegationManager()
        results = manager.delegate_task(goal="Fix the bug")
        assert len(results) == 1
        assert results[0].task_id == "single"
        assert results[0].success is True

    def test_delegate_task_batch(self):
        """Test delegating batch tasks."""
        manager = DelegationManager()
        tasks = [
            {"goal": "Task 1"},
            {"goal": "Task 2"},
            {"goal": "Task 3"},
        ]
        results = manager.delegate_task(tasks=tasks)
        assert len(results) == 3
        assert results[0].task_id == "batch_0"
        assert results[1].task_id == "batch_1"
        assert results[2].task_id == "batch_2"

    def test_delegate_task_respects_max_concurrent(self):
        """Test delegation respects max_concurrent limit."""
        manager = DelegationManager(max_concurrent=2)
        tasks = [
            {"goal": "Task 1"},
            {"goal": "Task 2"},
            {"goal": "Task 3"},
            {"goal": "Task 4"},
        ]
        results = manager.delegate_task(tasks=tasks)
        assert len(results) == 2  # Limited to max_concurrent

    def test_delegate_task_no_goal_or_tasks(self):
        """Test delegation with no goal or tasks returns empty."""
        manager = DelegationManager()
        results = manager.delegate_task()
        assert results == []

    def test_delegate_task_with_role(self):
        """Test delegation with specific role."""
        manager = DelegationManager()
        results = manager.delegate_task(
            goal="Test task",
            role=AgentRole.ORCHESTRATOR,
        )
        assert len(results) == 1
        assert results[0].success is True

    def test_delegate_task_with_toolsets(self):
        """Test delegation with toolsets."""
        manager = DelegationManager()
        results = manager.delegate_task(
            goal="Test task",
            toolsets=["terminal", "file"],
        )
        assert len(results) == 1
        assert results[0].success is True

    def test_delegate_task_with_context(self):
        """Test delegation with context."""
        manager = DelegationManager()
        results = manager.delegate_task(
            goal="Test task",
            context="Additional context",
        )
        assert len(results) == 1
        assert results[0].success is True

    def test_delegate_task_depth_limit(self):
        """Test delegation respects depth limit."""
        manager = DelegationManager(max_depth=1)
        manager._current_depth = 1  # Simulate being at max depth

        results = manager.delegate_task(goal="Test task")
        assert len(results) == 1
        assert results[0].success is False
        assert "深度" in results[0].error or "depth" in results[0].error.lower()

    def test_spawn_single_returns_result(self):
        """Test _spawn_single returns DelegationResult."""
        manager = DelegationManager()
        result = manager._spawn_single(
            goal="Test goal",
            role=AgentRole.LEAF,
            toolsets=None,
            context=None,
        )
        assert isinstance(result, DelegationResult)
        assert result.success is True

    def test_spawn_batch_returns_results(self):
        """Test _spawn_batch returns list of DelegationResult."""
        manager = DelegationManager()
        tasks = [
            {"goal": "Task 1"},
            {"goal": "Task 2"},
        ]
        results = manager._spawn_batch(
            tasks=tasks,
            role=AgentRole.LEAF,
            toolsets=None,
        )
        assert len(results) == 2
        assert all(isinstance(r, DelegationResult) for r in results)
