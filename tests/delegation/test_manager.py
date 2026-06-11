"""Tests for delegation manager module."""

import pytest

from src.delegation.manager import (
    DelegationManager,
    AgentRole,
    DelegationResult,
    Semaphore,
)


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
            max_concurrent_children=5,
            max_spawn_depth=3,
            child_timeout_seconds=600.0,
            subagent_auto_approve=True,
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
        assert results[0].task_id.startswith("batch_0_")
        assert results[1].task_id.startswith("batch_1_")
        assert results[2].task_id.startswith("batch_2_")

    def test_delegate_task_respects_max_concurrent(self):
        """Test delegation respects max_concurrent limit."""
        manager = DelegationManager(max_concurrent_children=2)
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
        manager = DelegationManager(max_spawn_depth=1)
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


class TestConcurrencyControl:
    """Tests for concurrency control (4.6)."""

    def test_4_6_4_child_agent_timeout_config(self):
        """4.6.4 测试子 Agent 超时配置传播。

        注意：当前 _execute_single_agent 是模拟执行，不实际超时。
        这里测试超时配置的传播和设置。
        """
        manager = DelegationManager(child_timeout_seconds=10.0)
        config = manager.build_child_agent_config(
            goal="Test timeout",
            role=AgentRole.LEAF,
        )
        # 验证超时配置传播到子 Agent 配置
        assert config.timeout == 10.0

        # 执行任务（模拟执行，不会真正超时）
        result = manager.delegate_single(goal="Test timeout")
        assert result.success is True

        # 验证活跃子 Agent 被正确记录
        active = manager.get_active_children()
        assert len(active) == 0  # 执行完成后应清空

    def test_4_6_5_auto_deny_callback_default(self):
        """4.6.5 测试自动拒绝回调默认行为。

        默认拒绝危险操作：terminal, execute_code, write_file, delete_file。
        """
        manager = DelegationManager()

        # 默认行为：拒绝危险操作
        dangerous_call = {"name": "terminal", "args": {"command": "rm -rf"}}
        assert manager._subagent_auto_deny(dangerous_call) is True

        dangerous_call2 = {"name": "execute_code", "args": {"code": "test"}}
        assert manager._subagent_auto_deny(dangerous_call2) is True

        dangerous_call3 = {"name": "write_file", "args": {"path": "/tmp"}}
        assert manager._subagent_auto_deny(dangerous_call3) is True

        # 安全操作不被拒绝
        safe_call = {"name": "read_file", "args": {"path": "/tmp"}}
        assert manager._subagent_auto_deny(safe_call) is False

    def test_4_6_5_auto_deny_custom_callback(self):
        """4.6.5 测试自定义拒绝回调覆盖默认行为。"""
        manager = DelegationManager()

        # 设置自定义拒绝回调
        def custom_deny(tool_call: dict) -> bool:
            return tool_call.get("name") == "custom_dangerous_tool"

        manager.set_auto_deny_callback(custom_deny)

        custom_dangerous = {"name": "custom_dangerous_tool", "args": {}}
        assert manager._subagent_auto_deny(custom_dangerous) is True

        # 默认危险工具现在不被拒绝（自定义回调覆盖默认行为）
        dangerous_call = {"name": "terminal", "args": {"command": "rm -rf"}}
        assert manager._subagent_auto_deny(dangerous_call) is False

    def test_4_6_6_auto_approve_callback_default(self):
        """4.6.6 测试自动批准回调默认行为。"""
        manager = DelegationManager(subagent_auto_approve=False)

        # 默认行为：不批准（subagent_auto_approve=False）
        tool_call = {"name": "terminal", "args": {"command": "ls"}}
        assert manager._subagent_auto_approve(tool_call) is False

        # 设置 auto_approve=True
        manager_auto = DelegationManager(subagent_auto_approve=True)
        assert manager_auto._subagent_auto_approve(tool_call) is True

    def test_4_6_6_auto_approve_custom_callback(self):
        """4.6.6 测试自定义批准回调。"""
        manager = DelegationManager(subagent_auto_approve=False)

        # 设置自定义批准回调
        def custom_approve(tool_call: dict) -> bool:
            return tool_call.get("name") == "safe_tool"

        manager.set_auto_approve_callback(custom_approve)

        safe_tool_call = {"name": "safe_tool", "args": {}}
        assert manager._subagent_auto_approve(safe_tool_call) is True

        # 其他工具不被批准（即使 auto_approve=False）
        other_call = {"name": "other_tool", "args": {}}
        assert manager._subagent_auto_approve(other_call) is False


class TestSubAgentIsolation:
    """Tests for sub-agent context isolation (5.1)."""

    def test_5_1_1_subagent_no_parent_history(self):
        """5.1.1 测试子 Agent 无父历史。

        子 Agent 的上下文应该只包含传入的 goal 和 context，
        不包含父 Agent 的完整对话历史。
        """
        manager = DelegationManager()

        # 构建子 Agent 配置
        config = manager.build_child_agent_config(
            goal="独立任务",
            role=AgentRole.LEAF,
            context="这是子 Agent 的上下文",
        )

        # 验证配置中没有父对话历史
        # system_prompt 应只包含 goal 和 context
        assert "独立任务" in config.system_prompt
        assert "这是子 Agent 的上下文" in config.system_prompt
        # 不应包含父 Agent 的对话内容
        assert "parent message" not in config.system_prompt.lower()
        assert "父消息" not in config.system_prompt

        # 执行子 Agent
        result = manager.delegate_single(
            goal="独立任务",
            context="这是子 Agent 的上下文",
        )

        # 验证结果是独立的摘要，不是父对话的副本
        assert result.success is True
        assert "已完成任务" in result.summary

    def test_5_1_2_parent_context_only_sees_summary(self):
        """5.1.2 测试父上下文只看到摘要。

        父 Agent 只能看到子 Agent 返回的摘要，
        不应看到子 Agent 的完整执行过程。
        """
        manager = DelegationManager()

        # 委托任务
        result = manager.delegate_single(
            goal="复杂任务",
            context="需要处理的上下文",
        )

        # 父 Agent 只看到摘要
        summary = result.summary
        assert summary is not None
        assert len(summary) < 500  # 摘要应简洁

        # 验证摘要不包含子 Agent 的详细日志
        assert "tool_calls:" not in summary.lower()
        assert "intermediate steps" not in summary.lower()

        # 验证 tool_calls 计数存在（但不暴露详细内容）
        assert result.tool_calls >= 0

        # 获取已完成的结果列表
        completed = manager.get_completed_results()
        assert len(completed) == 1
        assert completed[0].summary == result.summary

    def test_subagent_context_isolation_complete(self):
        """完整上下文隔离测试。

        验证父 Agent 和子 Agent 之间完全隔离。
        """
        manager = DelegationManager()

        # 模拟父 Agent 有一些状态
        manager._completed_results.append(DelegationResult(
            task_id="previous_task",
            success=True,
            summary="父 Agent 之前的任务",
        ))

        # 委托新任务给子 Agent
        new_result = manager.delegate_single(
            goal="新任务",
            context="新任务的上下文",
        )

        # 验证新任务的系统提示不包含之前的任务记录
        config = manager.build_child_agent_config(
            goal="新任务",
            role=AgentRole.LEAF,
            context="新任务的上下文",
        )
        assert "previous_task" not in config.system_prompt
        assert "父 Agent 之前的任务" not in config.system_prompt

        # 验证子 Agent 结果独立
        assert new_result.task_id != "previous_task"
        assert "新任务" in new_result.summary

        # 验证父 Agent 可以区分不同子 Agent 的结果
        all_results = manager.get_completed_results()
        assert len(all_results) == 2
        task_ids = [r.task_id for r in all_results]
        assert "previous_task" in task_ids
        assert new_result.task_id in task_ids


class TestOrchestratorRole:
    """Tests for orchestrator role behavior."""

    def test_orchestrator_can_delegate(self):
        """测试 Orchestrator 可以进一步委托。"""
        manager = DelegationManager(max_spawn_depth=2)

        # Orchestrator 角色
        config = manager.build_child_agent_config(
            goal="编排任务",
            role=AgentRole.ORCHESTRATOR,
        )

        # 验证 Orchestrator 可以使用 delegate_task
        blocked = config.blocked_tools
        assert "delegate_task" not in blocked
        assert "clarify" in blocked  # clarify 仍被阻止
        assert "memory" in blocked   # memory 仍被阻止

    def test_orchestrator_depth_limit(self):
        """测试 Orchestrator 深度限制。"""
        manager = DelegationManager(max_spawn_depth=2)

        # 第一层委托（depth=0 → depth=1）
        result1 = manager.delegate_single(
            goal="Level 1 task",
            role=AgentRole.ORCHESTRATOR,
        )
        assert result1.success is True

        # 模拟进入第二层
        manager._current_depth = 1
        result2 = manager.delegate_single(
            goal="Level 2 task",
            role=AgentRole.ORCHESTRATOR,
        )
        assert result2.success is True

        # 第三层应被阻止
        manager._current_depth = 2
        result3 = manager.delegate_single(
            goal="Level 3 task",
            role=AgentRole.ORCHESTRATOR,
        )
        assert result3.success is False
        assert "深度" in result3.error or "depth" in result3.error.lower()


class TestSemaphore:
    """Tests for Semaphore concurrency control."""

    def test_semaphore_acquire_release(self):
        """测试信号量获取和释放。"""
        sem = Semaphore(max_concurrent=2)

        # 获取第一个槽位
        assert sem.acquire_sync() is True
        assert sem.active_count == 1

        # 获取第二个槽位
        assert sem.acquire_sync() is True
        assert sem.active_count == 2

        # 第三个应失败
        assert sem.acquire_sync() is False
        assert sem.active_count == 2

        # 释放一个
        sem.release_sync()
        assert sem.active_count == 1

        # 现在可以再次获取
        assert sem.acquire_sync() is True
        assert sem.active_count == 2

    def test_semaphore_context_manager(self):
        """测试信号量上下文管理器。"""
        sem = Semaphore(max_concurrent=1)

        with sem:
            assert sem.active_count == 1

        # 退出后自动释放
        assert sem.active_count == 0

    def test_semaphore_available_slots(self):
        """测试可用槽位计算。"""
        sem = Semaphore(max_concurrent=3)

        assert sem.available_slots == 3

        sem.acquire_sync()
        assert sem.available_slots == 2

        sem.acquire_sync()
        assert sem.available_slots == 1

        sem.acquire_sync()
        assert sem.available_slots == 0