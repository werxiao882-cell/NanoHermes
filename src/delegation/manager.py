"""DelegationManager - 多 Agent 委托管理器。

支持：
- 单任务委托 (goal)
- 批量并行委托 (tasks 数组)
- leaf / orchestrator 角色
- 并发限制和深度限制
- Semaphore 并发控制
- 子 Agent 上下文隔离
- 自动批准/拒绝回调
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 子 Agent 角色
# ─────────────────────────────────────────────
class AgentRole(Enum):
    """子 Agent 角色。

    LEAF: 普通工作者，不能委托、访问记忆等。
    ORCHESTRATOR: 编排者，可以进一步委托子任务。
    """
    LEAF = "leaf"
    ORCHESTRATOR = "orchestrator"


# ─────────────────────────────────────────────
# 被阻止的工具列表
# ─────────────────────────────────────────────
DELEGATE_BLOCKED_TOOLS: frozenset[str] = frozenset([
    "delegate_task",    # 禁止递归委托（leaf）
    "clarify",          # 禁止用户交互
    "memory",           # 禁止写入共享 MEMORY.md
    "execute_code",     # 子 Agent 应逐步推理，而非编写脚本
])

# Orchestrator 可以使用的额外工具
ORCHESTRATOR_ALLOWED_TOOLS: frozenset[str] = frozenset([
    "delegate_task",    # 允许进一步委托
])


# ─────────────────────────────────────────────
# 委托结果
# ─────────────────────────────────────────────
@dataclass
class DelegationResult:
    """委托结果。

    Attributes:
        task_id: 任务 ID。
        success: 是否成功。
        summary: 结果摘要。
        error: 错误信息（如果失败）。
        role: 子 Agent 角色。
        duration: 执行耗时（秒）。
        tool_calls: 工具调用次数。
    """
    task_id: str
    success: bool
    summary: str = ""
    error: str = ""
    role: str = "leaf"
    duration: float = 0.0
    tool_calls: int = 0


# ─────────────────────────────────────────────
# 子 Agent 配置
# ─────────────────────────────────────────────
@dataclass
class ChildAgentConfig:
    """子 Agent 配置。

    Attributes:
        task_id: 任务 ID。
        role: 角色。
        goal: 目标描述。
        context: 上下文信息。
        allowed_toolsets: 允许的工具集。
        blocked_tools: 被阻止的工具。
        system_prompt: 系统提示。
        max_depth: 最大委托深度。
        timeout: 超时时间。
        auto_approve: 是否自动批准。
    """
    task_id: str
    role: str
    goal: str
    context: str = ""
    allowed_toolsets: list[str] = field(default_factory=list)
    blocked_tools: list[str] = field(default_factory=list)
    system_prompt: str = ""
    max_depth: int = 2
    timeout: float = 300.0
    auto_approve: bool = False


# ─────────────────────────────────────────────
# Semaphore 并发控制
# ─────────────────────────────────────────────
class Semaphore:
    """异步信号量，用于控制并发子 Agent 数量。

    支持同步和异步两种模式。
    """

    def __init__(self, max_concurrent: int = 3):
        """初始化信号量。

        Args:
            max_concurrent: 最大并发数。
        """
        self.max_concurrent = max(1, max_concurrent)
        self._active = 0
        self._waiters: deque[asyncio.Event] = deque()
        try:
            self._lock = asyncio.Lock() if asyncio.current_task() else None
        except RuntimeError:
            # No running event loop (e.g., in synchronous context)
            self._lock = None

    @property
    def active_count(self) -> int:
        """当前活跃任务数。"""
        return self._active

    @property
    def available_slots(self) -> int:
        """可用槽位数。"""
        return max(0, self.max_concurrent - self._active)

    def acquire_sync(self) -> bool:
        """同步获取许可。

        Returns:
            是否成功获取。
        """
        if self._active < self.max_concurrent:
            self._active += 1
            return True
        return False

    def release_sync(self) -> None:
        """同步释放许可。"""
        if self._active > 0:
            self._active -= 1

    async def acquire(self) -> None:
        """异步获取许可。"""
        while True:
            if self._active < self.max_concurrent:
                self._active += 1
                return
            # 等待释放
            await asyncio.sleep(0.01)

    async def release(self) -> None:
        """异步释放许可。"""
        if self._active > 0:
            self._active -= 1

    def __enter__(self) -> "Semaphore":
        self.acquire_sync()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release_sync()

    def __repr__(self) -> str:
        return f"Semaphore({self._active}/{self.max_concurrent})"


# ─────────────────────────────────────────────
# DelegationManager 类
# ─────────────────────────────────────────────
class DelegationManager:
    """委托管理器。

    管理子 Agent 的 spawn、并发控制和结果收集。
    """

    def __init__(
        self,
        max_concurrent_children: int = 3,
        max_spawn_depth: int = 2,
        child_timeout_seconds: float = 300.0,
        subagent_auto_approve: bool = False,
    ):
        """初始化委托管理器。

        Args:
            max_concurrent_children: 最大并发子 Agent 数。
            max_spawn_depth: 最大委托深度。
            child_timeout_seconds: 子 Agent 超时时间。
            subagent_auto_approve: 是否自动批准危险命令。
        """
        self.max_concurrent_children = max(1, max_concurrent_children)
        self.max_spawn_depth = max(0, max_spawn_depth)
        self.child_timeout_seconds = max(1.0, child_timeout_seconds)
        self.subagent_auto_approve = subagent_auto_approve

        self._current_depth = 0
        self._semaphore = Semaphore(max_concurrent_children)
        self._active_children: dict[str, dict[str, Any]] = {}
        self._completed_results: list[DelegationResult] = []

        # 回调
        self._auto_deny_callback: Callable[[dict], bool] | None = None
        self._auto_approve_callback: Callable[[dict], bool] | None = None

    # ── 公共 API ──

    def delegate_task(
        self,
        goal: str | None = None,
        tasks: list[dict[str, Any]] | None = None,
        role: AgentRole | str = AgentRole.LEAF,
        toolsets: list[str] | None = None,
        context: str | None = None,
    ) -> list[DelegationResult]:
        """委托任务。

        Args:
            goal: 单任务目标描述。
            tasks: 批量任务列表。
            role: 子 Agent 角色。
            toolsets: 允许使用的工具集。
            context: 上下文信息。

        Returns:
            委托结果列表。
        """
        # 检查深度
        if self._current_depth >= self.max_spawn_depth:
            return [DelegationResult(
                task_id="depth_limit",
                success=False,
                error=f"达到最大委托深度 ({self.max_spawn_depth})，无法生成子 Agent。",
            )]

        # 角色标准化
        if isinstance(role, str):
            role = AgentRole(role.lower())

        # 单任务模式
        if goal and not tasks:
            return [self.delegate_single(
                goal=goal,
                role=role,
                toolsets=toolsets,
                context=context,
            )]

        # 批量模式
        if tasks:
            return self.delegate_batch(
                tasks=tasks,
                role=role,
                toolsets=toolsets,
            )

        return []

    def delegate_single(
        self,
        goal: str,
        role: AgentRole | str = AgentRole.LEAF,
        toolsets: list[str] | None = None,
        context: str | None = None,
    ) -> DelegationResult:
        """委托单个任务。

        Args:
            goal: 目标描述。
            role: 角色。
            toolsets: 工具集。
            context: 上下文。

        Returns:
            委托结果。
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        # 检查深度
        if self._current_depth >= self.max_spawn_depth:
            return DelegationResult(
                task_id="depth_limit",
                success=False,
                error=f"达到最大委托深度 ({self.max_spawn_depth})",
            )

        # 构建子 Agent 配置
        config = self.build_child_agent_config(
            goal=goal,
            role=role,
            toolsets=toolsets,
            context=context,
        )

        # 使用 Semaphore 控制并发
        with self._semaphore:
            self._current_depth += 1
            start_time = time.time()

            try:
                result = self._execute_single_agent(config)
                result.duration = time.time() - start_time
                self._completed_results.append(result)
                return result
            finally:
                self._current_depth -= 1

    def delegate_batch(
        self,
        tasks: list[dict[str, Any]],
        role: AgentRole | str = AgentRole.LEAF,
        toolsets: list[str] | None = None,
    ) -> list[DelegationResult]:
        """批量并行委托任务。

        Args:
            tasks: 任务列表，每项包含 goal/description 和可选 context。
            role: 角色。
            toolsets: 工具集。

        Returns:
            委托结果列表。
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        # 限制并发数量
        limited_tasks = tasks[:self.max_concurrent_children]

        results = []
        for i, task in enumerate(limited_tasks):
            goal = task.get("goal", task.get("description", ""))
            task_context = task.get("context", "")
            task_toolsets = task.get("toolsets", toolsets)

            result = self.delegate_single(
                goal=goal,
                role=role,
                toolsets=task_toolsets,
                context=task_context,
            )
            result.task_id = f"batch_{i}_{result.task_id}"
            results.append(result)

        return results

    # ── 角色系统 ──

    def build_child_agent_config(
        self,
        goal: str,
        role: AgentRole | str,
        toolsets: list[str] | None = None,
        context: str | None = None,
        task_id: str | None = None,
    ) -> ChildAgentConfig:
        """构建子 Agent 配置。

        Args:
            goal: 目标描述。
            role: 角色。
            toolsets: 工具集。
            context: 上下文。
            task_id: 任务 ID（自动生成）。

        Returns:
            子 Agent 配置。
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        tid = task_id or str(uuid.uuid4())[:8]
        blocked = self.filter_blocked_tools(role, toolsets)
        system_prompt = self._build_system_prompt(role, goal, context)

        return ChildAgentConfig(
            task_id=tid,
            role=role.value,
            goal=goal,
            context=context or "",
            allowed_toolsets=toolsets or [],
            blocked_tools=list(blocked),
            system_prompt=system_prompt,
            max_depth=self.max_spawn_depth,
            timeout=self.child_timeout_seconds,
            auto_approve=self.subagent_auto_approve,
        )

    def filter_blocked_tools(
        self,
        role: AgentRole | str,
        toolsets: list[str] | None = None,
    ) -> list[str]:
        """过滤被阻止的工具。

        Args:
            role: 角色。
            toolsets: 原始工具集。

        Returns:
            过滤后的工具列表。
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        blocked = set(DELEGATE_BLOCKED_TOOLS)

        # Orchestrator 可以 delegate_task
        if role == AgentRole.ORCHESTRATOR:
            blocked -= ORCHESTRATOR_ALLOWED_TOOLS

        if toolsets:
            # 过滤掉被阻止的工具
            return [t for t in toolsets if t not in blocked]

        return list(blocked)

    # ── 系统提示构建 ──

    def _build_system_prompt(
        self,
        role: AgentRole,
        goal: str,
        context: str | None = None,
    ) -> str:
        """构建子 Agent 系统提示。

        Args:
            role: 角色。
            goal: 目标。
            context: 上下文。

        Returns:
            系统提示。
        """
        if role == AgentRole.LEAF:
            return self._build_leaf_system_prompt(goal, context)
        else:
            return self._build_orchestrator_system_prompt(goal, context)

    def _build_leaf_system_prompt(self, goal: str, context: str | None) -> str:
        """构建 Leaf 角色系统提示。

        Args:
            goal: 目标。
            context: 上下文。

        Returns:
            系统提示。
        """
        parts = [
            "# Leaf Agent",
            "",
            "你是一个专注的工作者 Agent，负责完成分配的特定任务。",
            "",
            "## 限制",
            "- 你不能委托任务给其他 Agent（delegate_task 不可用）",
            "- 你不能与用户交互（clarify 不可用）",
            "- 你不能写入共享记忆（memory 不可用）",
            "- 你应该逐步推理，而非编写脚本（execute_code 不可用）",
            "",
            "## 任务",
            f"{goal}",
        ]

        if context:
            parts.extend(["", "## 上下文", context])

        return "\n".join(parts)

    def _build_orchestrator_system_prompt(self, goal: str, context: str | None) -> str:
        """构建 Orchestrator 角色系统提示。

        Args:
            goal: 目标。
            context: 上下文。

        Returns:
            系统提示。
        """
        parts = [
            "# Orchestrator Agent",
            "",
            "你是一个编排者 Agent，负责分解任务并委托给子 Agent。",
            "",
            "## 能力",
            "- 你可以委托任务给子 Agent（delegate_task 可用）",
            "- 你应该将大任务分解为小任务",
            "- 你应该合并子 Agent 的结果",
            "",
            "## 任务",
            f"{goal}",
        ]

        if context:
            parts.extend(["", "## 上下文", context])

        return "\n".join(parts)

    # ── 并发控制 ──

    @property
    def max_concurrent(self) -> int:
        """最大并发数（兼容属性）。"""
        return self.max_concurrent_children

    @property
    def max_depth(self) -> int:
        """最大深度（兼容属性）。"""
        return self.max_spawn_depth

    @property
    def timeout_seconds(self) -> float:
        """超时时间（兼容属性）。"""
        return self.child_timeout_seconds

    @property
    def auto_approve(self) -> bool:
        """自动批准（兼容属性）。"""
        return self.subagent_auto_approve

    def set_auto_deny_callback(self, callback: Callable[[dict], bool]) -> None:
        """设置自动拒绝回调。

        Args:
            callback: 回调函数，接收工具调用信息，返回是否拒绝。
        """
        self._auto_deny_callback = callback

    def set_auto_approve_callback(self, callback: Callable[[dict], bool]) -> None:
        """设置自动批准回调。

        Args:
            callback: 回调函数，接收工具调用信息，返回是否批准。
        """
        self._auto_approve_callback = callback

    def _subagent_auto_deny(self, tool_call: dict) -> bool:
        """子 Agent 自动拒绝回调。

        Args:
            tool_call: 工具调用信息。

        Returns:
            是否拒绝。
        """
        if self._auto_deny_callback:
            return self._auto_deny_callback(tool_call)
        # 默认：拒绝危险操作
        dangerous = {"terminal", "execute_code", "write_file", "delete_file"}
        tool_name = tool_call.get("name", tool_call.get("tool", ""))
        return tool_name in dangerous

    def _subagent_auto_approve(self, tool_call: dict) -> bool:
        """子 Agent 自动批准回调。

        Args:
            tool_call: 工具调用信息。

        Returns:
            是否批准。
        """
        if self._auto_approve_callback:
            return self._auto_approve_callback(tool_call)
        return self.subagent_auto_approve

    # ── 执行 ──

    def _execute_single_agent(self, config: ChildAgentConfig) -> DelegationResult:
        """执行单个子 Agent。

        Args:
            config: 子 Agent 配置。

        Returns:
            委托结果。
        """
        task_id = config.task_id

        # 注册活跃子 Agent
        self._active_children[task_id] = {
            "config": config,
            "start_time": time.time(),
            "status": "running",
        }

        try:
            # 模拟执行（实际应 spawn 子进程）
            summary = self._simulate_execution(config)

            result = DelegationResult(
                task_id=task_id,
                success=True,
                summary=summary,
                role=config.role,
            )

            self._active_children[task_id]["status"] = "completed"
            return result

        except Exception as e:
            logger.error(f"子 Agent 执行失败 [{task_id}]: {e}", exc_info=True)
            self._active_children[task_id]["status"] = "failed"

            return DelegationResult(
                task_id=task_id,
                success=False,
                error=str(e),
                role=config.role,
            )
        finally:
            # 清理
            if task_id in self._active_children:
                del self._active_children[task_id]

    def _simulate_execution(self, config: ChildAgentConfig) -> str:
        """模拟子 Agent 执行。

        Args:
            config: 配置。

        Returns:
            执行摘要。
        """
        goal_preview = config.goal[:80] if len(config.goal) > 80 else config.goal
        return f"已完成任务: {goal_preview}"

    # ── 批量内部方法（兼容） ──

    def _spawn_single(
        self,
        goal: str,
        role: AgentRole,
        toolsets: list[str] | None,
        context: str | None,
    ) -> DelegationResult:
        """Spawn 单个子 Agent（兼容方法）。

        Args:
            goal: 目标描述。
            role: 角色。
            toolsets: 工具集。
            context: 上下文。

        Returns:
            委托结果。
        """
        return self.delegate_single(
            goal=goal,
            role=role,
            toolsets=toolsets,
            context=context,
        )

    def _spawn_batch(
        self,
        tasks: list[dict[str, Any]],
        role: AgentRole,
        toolsets: list[str] | None,
    ) -> list[DelegationResult]:
        """批量 Spawn 子 Agent（兼容方法）。

        Args:
            tasks: 任务列表。
            role: 角色。
            toolsets: 工具集。

        Returns:
            委托结果列表。
        """
        return self.delegate_batch(
            tasks=tasks,
            role=role,
            toolsets=toolsets,
        )

    # ── 状态查询 ──

    def get_active_children(self) -> dict[str, dict[str, Any]]:
        """获取活跃子 Agent 信息。

        Returns:
            活跃子 Agent 字典。
        """
        return dict(self._active_children)

    def get_completed_results(self) -> list[DelegationResult]:
        """获取已完成的结果。

        Returns:
            结果列表。
        """
        return list(self._completed_results)

    def reset(self) -> None:
        """重置管理器状态。"""
        self._current_depth = 0
        self._active_children.clear()
        self._completed_results.clear()
