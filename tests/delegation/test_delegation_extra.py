"""委托系统补充测试。

覆盖现有测试未涉及的边界场景、内部方法和数据类。
"""

import asyncio
import threading

import pytest

from src.delegation import (
    AgentRole,
    ChildAgentConfig,
    DelegationManager,
    DelegationResult,
    Semaphore,
)
from src.delegation.types import DELEGATE_BLOCKED_TOOLS, ORCHESTRATOR_ALLOWED_TOOLS


# ── ChildAgentConfig ──


class TestChildAgentConfig:

    def test_defaults(self):
        cfg = ChildAgentConfig(task_id="t1", role="leaf", goal="do stuff")
        assert cfg.context == ""
        assert cfg.allowed_toolsets == []
        assert cfg.blocked_tools == []
        assert cfg.system_prompt == ""
        assert cfg.max_depth == 2
        assert cfg.timeout == 300.0
        assert cfg.auto_approve is False

    def test_custom_values(self):
        cfg = ChildAgentConfig(
            task_id="t2",
            role="orchestrator",
            goal="orchestrate",
            context="ctx",
            allowed_toolsets=["terminal"],
            blocked_tools=["memory"],
            system_prompt="prompt",
            max_depth=5,
            timeout=60.0,
            auto_approve=True,
        )
        assert cfg.task_id == "t2"
        assert cfg.role == "orchestrator"
        assert cfg.goal == "orchestrate"
        assert cfg.context == "ctx"
        assert cfg.allowed_toolsets == ["terminal"]
        assert cfg.blocked_tools == ["memory"]
        assert cfg.system_prompt == "prompt"
        assert cfg.max_depth == 5
        assert cfg.timeout == 60.0
        assert cfg.auto_approve is True

    def test_mutable_defaults_independent(self):
        cfg1 = ChildAgentConfig(task_id="a", role="leaf", goal="g1")
        cfg2 = ChildAgentConfig(task_id="b", role="leaf", goal="g2")
        cfg1.allowed_toolsets.append("terminal")
        assert "terminal" not in cfg2.allowed_toolsets


# ── DelegationResult 补充 ──


class TestDelegationResultExtra:

    def test_all_fields(self):
        r = DelegationResult(
            task_id="x",
            success=True,
            summary="done",
            error="",
            role="orchestrator",
            duration=1.5,
            tool_calls=3,
        )
        assert r.role == "orchestrator"
        assert r.duration == 1.5
        assert r.tool_calls == 3

    def test_default_role_is_leaf(self):
        r = DelegationResult(task_id="x", success=True)
        assert r.role == "leaf"


# ── 常量 ──


class TestConstants:

    def test_blocked_tools_contents(self):
        assert "delegate_task" in DELEGATE_BLOCKED_TOOLS
        assert "clarify" in DELEGATE_BLOCKED_TOOLS
        assert "memory" in DELEGATE_BLOCKED_TOOLS
        assert "execute_code" in DELEGATE_BLOCKED_TOOLS

    def test_blocked_tools_is_frozenset(self):
        assert isinstance(DELEGATE_BLOCKED_TOOLS, frozenset)

    def test_orchestrator_allowed_tools(self):
        assert "delegate_task" in ORCHESTRATOR_ALLOWED_TOOLS
        assert isinstance(ORCHESTRATOR_ALLOWED_TOOLS, frozenset)


# ── filter_blocked_tools ──


class TestFilterBlockedTools:

    def test_leaf_blocks_all_default_tools(self):
        mgr = DelegationManager()
        blocked = mgr.filter_blocked_tools(AgentRole.LEAF)
        for tool in DELEGATE_BLOCKED_TOOLS:
            assert tool in blocked

    def test_orchestrator_unblocks_delegate_task(self):
        mgr = DelegationManager()
        blocked = mgr.filter_blocked_tools(AgentRole.ORCHESTRATOR)
        assert "delegate_task" not in blocked
        assert "clarify" in blocked
        assert "memory" in blocked
        assert "execute_code" in blocked

    def test_with_toolsets_whitelist_leaf(self):
        mgr = DelegationManager()
        result = mgr.filter_blocked_tools(
            AgentRole.LEAF,
            toolsets=["terminal", "read_file", "delegate_task", "memory"],
        )
        assert "terminal" in result
        assert "read_file" in result
        assert "delegate_task" not in result
        assert "memory" not in result

    def test_with_toolsets_whitelist_orchestrator(self):
        mgr = DelegationManager()
        result = mgr.filter_blocked_tools(
            AgentRole.ORCHESTRATOR,
            toolsets=["terminal", "delegate_task", "clarify"],
        )
        assert "terminal" in result
        assert "delegate_task" in result
        assert "clarify" not in result

    def test_string_role_normalization(self):
        mgr = DelegationManager()
        blocked_leaf = mgr.filter_blocked_tools("leaf")
        blocked_orch = mgr.filter_blocked_tools("orchestrator")
        assert "delegate_task" in blocked_leaf
        assert "delegate_task" not in blocked_orch

    def test_empty_toolsets_returns_blocked_list(self):
        mgr = DelegationManager()
        result = mgr.filter_blocked_tools(AgentRole.LEAF, toolsets=[])
        assert isinstance(result, list)
        assert len(result) > 0


# ── build_child_agent_config ──


class TestBuildChildAgentConfig:

    def test_auto_generated_task_id(self):
        mgr = DelegationManager()
        cfg = mgr.build_child_agent_config(goal="test", role=AgentRole.LEAF)
        assert len(cfg.task_id) == 8

    def test_custom_task_id(self):
        mgr = DelegationManager()
        cfg = mgr.build_child_agent_config(
            goal="test", role=AgentRole.LEAF, task_id="custom-id"
        )
        assert cfg.task_id == "custom-id"

    def test_unique_task_ids(self):
        mgr = DelegationManager()
        ids = set()
        for _ in range(50):
            cfg = mgr.build_child_agent_config(goal="test", role=AgentRole.LEAF)
            ids.add(cfg.task_id)
        assert len(ids) == 50

    def test_context_defaults_to_empty(self):
        mgr = DelegationManager()
        cfg = mgr.build_child_agent_config(goal="test", role=AgentRole.LEAF)
        assert cfg.context == ""

    def test_context_propagated(self):
        mgr = DelegationManager()
        cfg = mgr.build_child_agent_config(
            goal="test", role=AgentRole.LEAF, context="important context"
        )
        assert cfg.context == "important context"

    def test_max_depth_from_manager(self):
        mgr = DelegationManager(max_spawn_depth=5)
        cfg = mgr.build_child_agent_config(goal="test", role=AgentRole.LEAF)
        assert cfg.max_depth == 5

    def test_auto_approve_from_manager(self):
        mgr = DelegationManager(subagent_auto_approve=True)
        cfg = mgr.build_child_agent_config(goal="test", role=AgentRole.LEAF)
        assert cfg.auto_approve is True

    def test_string_role(self):
        mgr = DelegationManager()
        cfg = mgr.build_child_agent_config(goal="test", role="orchestrator")
        assert cfg.role == "orchestrator"


# ── 系统提示构建 ──


class TestSystemPromptBuilding:

    def test_leaf_prompt_contains_restrictions(self):
        mgr = DelegationManager()
        prompt = mgr._build_leaf_system_prompt("do task", None)
        assert "# Leaf Agent" in prompt
        assert "delegate_task 不可用" in prompt
        assert "clarify 不可用" in prompt
        assert "memory 不可用" in prompt
        assert "execute_code 不可用" in prompt
        assert "do task" in prompt

    def test_leaf_prompt_without_context(self):
        mgr = DelegationManager()
        prompt = mgr._build_leaf_system_prompt("do task", None)
        assert "## 上下文" not in prompt

    def test_leaf_prompt_with_context(self):
        mgr = DelegationManager()
        prompt = mgr._build_leaf_system_prompt("do task", "extra info")
        assert "## 上下文" in prompt
        assert "extra info" in prompt

    def test_orchestrator_prompt_contains_capabilities(self):
        mgr = DelegationManager()
        prompt = mgr._build_orchestrator_system_prompt("orchestrate", None)
        assert "# Orchestrator Agent" in prompt
        assert "delegate_task 可用" in prompt
        assert "分解任务" in prompt
        assert "合并" in prompt
        assert "orchestrate" in prompt

    def test_orchestrator_prompt_without_context(self):
        mgr = DelegationManager()
        prompt = mgr._build_orchestrator_system_prompt("orchestrate", None)
        assert "## 上下文" not in prompt

    def test_orchestrator_prompt_with_context(self):
        mgr = DelegationManager()
        prompt = mgr._build_orchestrator_system_prompt("orchestrate", "bg info")
        assert "## 上下文" in prompt
        assert "bg info" in prompt

    def test_build_system_prompt_dispatches_leaf(self):
        mgr = DelegationManager()
        prompt = mgr._build_system_prompt(AgentRole.LEAF, "task")
        assert "# Leaf Agent" in prompt

    def test_build_system_prompt_dispatches_orchestrator(self):
        mgr = DelegationManager()
        prompt = mgr._build_system_prompt(AgentRole.ORCHESTRATOR, "task")
        assert "# Orchestrator Agent" in prompt


# ── _get_filtered_tool_schemas ──


class TestGetFilteredToolSchemas:

    def test_empty_schemas(self):
        mgr = DelegationManager(tool_schemas=[])
        result = mgr._get_filtered_tool_schemas(["terminal"])
        assert result == []

    def test_no_schemas_default(self):
        mgr = DelegationManager()
        result = mgr._get_filtered_tool_schemas(["terminal"])
        assert result == []

    def test_filters_blocked_tools(self):
        schemas = [
            {"name": "read_file", "description": "read"},
            {"name": "terminal", "description": "run commands"},
            {"name": "memory", "description": "persist"},
        ]
        mgr = DelegationManager(tool_schemas=schemas)
        result = mgr._get_filtered_tool_schemas(["terminal", "memory"])
        names = [s["name"] for s in result]
        assert "read_file" in names
        assert "terminal" not in names
        assert "memory" not in names

    def test_no_blocked_returns_all(self):
        schemas = [
            {"name": "read_file", "description": "read"},
            {"name": "terminal", "description": "run"},
        ]
        mgr = DelegationManager(tool_schemas=schemas)
        result = mgr._get_filtered_tool_schemas([])
        assert len(result) == 2

    def test_schema_without_name_filtered_out(self):
        """没有 name 字段的 schema 应被过滤掉，防止 API 报错。"""
        schemas = [{"description": "no name field"}]
        mgr = DelegationManager(tool_schemas=schemas)
        result = mgr._get_filtered_tool_schemas(["terminal"])
        assert len(result) == 0


# ── _simulate_execution ──


class TestSimulateExecution:

    def test_short_goal(self):
        mgr = DelegationManager()
        cfg = ChildAgentConfig(task_id="t", role="leaf", goal="short")
        result = mgr._simulate_execution(cfg)
        assert result == "已完成任务: short"

    def test_long_goal_truncated(self):
        mgr = DelegationManager()
        long_goal = "A" * 200
        cfg = ChildAgentConfig(task_id="t", role="leaf", goal=long_goal)
        result = mgr._simulate_execution(cfg)
        assert len(result) < len(long_goal)
        assert "A" * 80 in result

    def test_exactly_80_chars(self):
        mgr = DelegationManager()
        goal = "B" * 80
        cfg = ChildAgentConfig(task_id="t", role="leaf", goal=goal)
        result = mgr._simulate_execution(cfg)
        assert "B" * 80 in result


# ── reset ──


class TestReset:

    def test_reset_clears_all_state(self):
        mgr = DelegationManager()
        mgr.delegate_single(goal="task1")
        mgr.delegate_single(goal="task2")
        assert len(mgr.get_completed_results()) == 2

        mgr.reset()
        assert mgr._current_depth == 0
        assert len(mgr.get_active_children()) == 0
        assert len(mgr.get_completed_results()) == 0

    def test_reset_preserves_config(self):
        mgr = DelegationManager(
            max_concurrent_children=5,
            max_spawn_depth=3,
            child_timeout_seconds=42.0,
            subagent_auto_approve=True,
        )
        mgr.reset()
        assert mgr.max_concurrent_children == 5
        assert mgr.max_spawn_depth == 3
        assert mgr.child_timeout_seconds == 42.0
        assert mgr.subagent_auto_approve is True

    def test_reset_allows_new_delegations(self):
        mgr = DelegationManager()
        mgr.delegate_single(goal="before")
        mgr.reset()
        result = mgr.delegate_single(goal="after")
        assert result.success is True
        assert len(mgr.get_completed_results()) == 1


# ── 状态查询 ──


class TestStateQueries:

    def test_get_active_children_returns_copy(self):
        mgr = DelegationManager()
        active = mgr.get_active_children()
        active["fake"] = {"status": "running"}
        assert "fake" not in mgr.get_active_children()

    def test_get_completed_results_returns_copy(self):
        mgr = DelegationManager()
        mgr.delegate_single(goal="task")
        results = mgr.get_completed_results()
        results.clear()
        assert len(mgr.get_completed_results()) == 1

    def test_completed_results_accumulate(self):
        mgr = DelegationManager()
        mgr.delegate_single(goal="a")
        mgr.delegate_single(goal="b")
        mgr.delegate_single(goal="c")
        results = mgr.get_completed_results()
        assert len(results) == 3
        summaries = [r.summary for r in results]
        assert any("a" in s for s in summaries)
        assert any("b" in s for s in summaries)
        assert any("c" in s for s in summaries)


# ── Semaphore 边界 ──


class TestSemaphoreEdgeCases:

    def test_zero_max_clamped_to_one(self):
        sem = Semaphore(max_concurrent=0)
        assert sem.max_concurrent == 1
        assert sem.acquire_sync() is True

    def test_negative_max_clamped_to_one(self):
        sem = Semaphore(max_concurrent=-5)
        assert sem.max_concurrent == 1

    def test_release_when_zero_no_negative(self):
        sem = Semaphore(max_concurrent=1)
        sem.release_sync()
        sem.release_sync()
        assert sem.active_count == 0

    def test_repr(self):
        sem = Semaphore(max_concurrent=3)
        assert repr(sem) == "Semaphore(0/3)"
        sem.acquire_sync()
        assert repr(sem) == "Semaphore(1/3)"

    def test_context_manager_releases_on_exception(self):
        sem = Semaphore(max_concurrent=1)
        with pytest.raises(ValueError):
            with sem:
                assert sem.active_count == 1
                raise ValueError("boom")
        assert sem.active_count == 0

    def test_available_slots_never_negative(self):
        sem = Semaphore(max_concurrent=1)
        sem.acquire_sync()
        assert sem.available_slots == 0
        sem._active = 999
        assert sem.available_slots == 0

    async def test_async_acquire_release(self):
        sem = Semaphore(max_concurrent=2)
        await sem.acquire()
        assert sem.active_count == 1
        await sem.acquire()
        assert sem.active_count == 2
        await sem.release()
        assert sem.active_count == 1
        await sem.release()
        assert sem.active_count == 0

    async def test_async_release_when_zero(self):
        sem = Semaphore(max_concurrent=1)
        await sem.release()
        assert sem.active_count == 0


# ── 初始化参数边界 ──


class TestInitClamping:

    def test_zero_concurrent_children(self):
        mgr = DelegationManager(max_concurrent_children=0)
        assert mgr.max_concurrent_children == 1

    def test_negative_concurrent_children(self):
        mgr = DelegationManager(max_concurrent_children=-10)
        assert mgr.max_concurrent_children == 1

    def test_negative_spawn_depth(self):
        mgr = DelegationManager(max_spawn_depth=-1)
        assert mgr.max_spawn_depth == 0

    def test_zero_timeout(self):
        mgr = DelegationManager(child_timeout_seconds=0)
        assert mgr.child_timeout_seconds == 1.0

    def test_negative_timeout(self):
        mgr = DelegationManager(child_timeout_seconds=-100)
        assert mgr.child_timeout_seconds == 1.0


# ── 角色字符串标准化 ──


class TestRoleStringNormalization:

    def test_delegate_task_string_role(self):
        mgr = DelegationManager()
        results = mgr.delegate_task(goal="test", role="leaf")
        assert len(results) == 1
        assert results[0].success is True

    def test_delegate_single_string_role(self):
        mgr = DelegationManager()
        result = mgr.delegate_single(goal="test", role="orchestrator")
        assert result.success is True
        assert result.role == "orchestrator"

    def test_delegate_batch_string_role(self):
        mgr = DelegationManager()
        results = mgr.delegate_batch(
            tasks=[{"goal": "a"}], role="leaf"
        )
        assert len(results) == 1


# ── 批量任务格式 ──


class TestBatchTaskFormats:

    def test_batch_with_description_field(self):
        mgr = DelegationManager()
        tasks = [{"description": "desc task"}]
        results = mgr.delegate_batch(tasks=tasks)
        assert len(results) == 1
        assert results[0].success is True

    def test_batch_with_per_task_context(self):
        mgr = DelegationManager()
        tasks = [
            {"goal": "task1", "context": "ctx1"},
            {"goal": "task2", "context": "ctx2"},
        ]
        results = mgr.delegate_batch(tasks=tasks)
        assert len(results) == 2

    def test_batch_with_per_task_toolsets(self):
        mgr = DelegationManager()
        tasks = [
            {"goal": "task1", "toolsets": ["terminal"]},
            {"goal": "task2", "toolsets": ["read_file"]},
        ]
        results = mgr.delegate_batch(tasks=tasks)
        assert len(results) == 2

    def test_batch_empty_list(self):
        mgr = DelegationManager()
        results = mgr.delegate_batch(tasks=[])
        assert results == []


# ── auto_deny 补充 ──


class TestAutoDenyExtra:

    def test_delete_file_is_dangerous(self):
        mgr = DelegationManager()
        assert mgr._subagent_auto_deny({"name": "delete_file"}) is True

    def test_tool_key_fallback(self):
        mgr = DelegationManager()
        assert mgr._subagent_auto_deny({"tool": "terminal"}) is True

    def test_empty_tool_call_not_dangerous(self):
        mgr = DelegationManager()
        assert mgr._subagent_auto_deny({}) is False

    def test_read_file_safe(self):
        mgr = DelegationManager()
        assert mgr._subagent_auto_deny({"name": "read_file"}) is False

    def test_search_files_safe(self):
        mgr = DelegationManager()
        assert mgr._subagent_auto_deny({"name": "search_files"}) is False


# ── 深度管理 ──


class TestDepthManagement:

    def test_depth_returns_to_zero_after_single(self):
        mgr = DelegationManager()
        mgr.delegate_single(goal="task")
        assert mgr._current_depth == 0

    def test_depth_returns_to_zero_after_batch(self):
        mgr = DelegationManager()
        mgr.delegate_batch(tasks=[{"goal": "a"}, {"goal": "b"}])
        assert mgr._current_depth == 0

    def test_depth_zero_blocks_when_max_depth_zero(self):
        mgr = DelegationManager(max_spawn_depth=0)
        result = mgr.delegate_single(goal="blocked")
        assert result.success is False

    def test_depth_limit_via_delegate_task(self):
        mgr = DelegationManager(max_spawn_depth=1)
        mgr._current_depth = 1
        results = mgr.delegate_task(goal="blocked")
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].task_id == "depth_limit"


# ── 事件总线补充 ──


class TestEventBusExtra:

    def test_batch_events(self):
        from src.conversation.events import EventType

        events = []

        mgr = DelegationManager()
        bus = mgr._event_bus
        bus.on(EventType.DELEGATION_START, lambda d: events.append(("start", d)))
        bus.on(EventType.DELEGATION_COMPLETE, lambda d: events.append(("complete", d)))

        mgr.delegate_batch(tasks=[{"goal": "a"}, {"goal": "b"}])

        starts = [e for e in events if e[0] == "start"]
        completes = [e for e in events if e[0] == "complete"]
        assert len(starts) == 2
        assert len(completes) == 2

    def test_event_bus_exception_does_not_break_delegation(self):
        from src.conversation.events import EventType

        mgr = DelegationManager()
        bus = mgr._event_bus

        def bad_handler(data):
            raise RuntimeError("handler exploded")

        bus.on(EventType.DELEGATION_START, bad_handler)

        result = mgr.delegate_single(goal="survive")
        assert result.success is True

    def test_emit_event_with_invalid_type_name(self):
        mgr = DelegationManager()
        mgr._emit_event("NONEXISTENT_EVENT", {"key": "value"})


# ── _execute_single_agent 异常处理 ──


class TestExecuteSingleAgentException:

    def test_model_caller_exception(self):
        def bad_caller(*args, **kwargs):
            raise RuntimeError("LLM exploded")

        mgr = DelegationManager(model_caller=bad_caller)
        result = mgr.delegate_single(goal="will fail")
        assert result.success is False
        assert "LLM exploded" in result.error

    def test_active_children_cleaned_on_exception(self):
        def bad_caller(*args, **kwargs):
            raise RuntimeError("fail")

        mgr = DelegationManager(model_caller=bad_caller)
        mgr.delegate_single(goal="fail")
        assert len(mgr.get_active_children()) == 0

    def test_depth_restored_on_exception(self):
        def bad_caller(*args, **kwargs):
            raise RuntimeError("fail")

        mgr = DelegationManager(model_caller=bad_caller, max_spawn_depth=5)
        mgr.delegate_single(goal="fail")
        assert mgr._current_depth == 0


# ── delegate_task 边界 ──


class TestDelegateTaskEdgeCases:

    def test_empty_string_goal_returns_empty(self):
        mgr = DelegationManager()
        results = mgr.delegate_task(goal="")
        assert results == []

    def test_goal_and_tasks_both_provided(self):
        mgr = DelegationManager()
        results = mgr.delegate_task(
            goal="single",
            tasks=[{"goal": "batch1"}],
        )
        assert len(results) == 1
        assert results[0].task_id.startswith("batch_0_")

    def test_none_goal_with_none_tasks(self):
        mgr = DelegationManager()
        results = mgr.delegate_task(goal=None, tasks=None)
        assert results == []

    def test_delegate_task_with_string_role_orchestrator(self):
        mgr = DelegationManager()
        results = mgr.delegate_task(goal="test", role="orchestrator")
        assert len(results) == 1
        assert results[0].role == "orchestrator"


# ── 并发线程安全 ──


class TestConcurrencyThreadSafety:

    def test_semaphore_thread_safety(self):
        sem = Semaphore(max_concurrent=3)
        results = []
        barrier = threading.Barrier(6)

        def worker():
            barrier.wait()
            acquired = sem.acquire_sync()
            results.append(acquired)
            if acquired:
                import time
                time.sleep(0.01)
                sem.release_sync()

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sem.active_count == 0
        assert sum(results) <= 6

    def test_multiple_delegations_accumulate_results(self):
        mgr = DelegationManager(max_concurrent_children=5)
        for i in range(5):
            mgr.delegate_single(goal=f"task {i}")
        assert len(mgr.get_completed_results()) == 5
