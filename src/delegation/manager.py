"""DelegationManager - 多 Agent 委托管理器。

支持：
- 单任务委托 (goal)
- 批量并行委托 (tasks 数组)
- leaf / orchestrator 角色
- 并发限制和深度限制
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AgentRole(Enum):
    """子 Agent 角色。

    LEAF: 普通工作者，不能委托、访问记忆等。
    ORCHESTRATOR: 编排者，可以进一步委托子任务。
    """
    LEAF = "leaf"
    ORCHESTRATOR = "orchestrator"


@dataclass
class DelegationResult:
    """委托结果。

    Attributes:
        task_id: 任务 ID。
        success: 是否成功。
        summary: 结果摘要。
        error: 错误信息（如果失败）。
    """
    task_id: str
    success: bool
    summary: str = ""
    error: str = ""


class DelegationManager:
    """委托管理器。

    管理子 Agent 的 spawn、并发控制和结果收集。
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        max_depth: int = 2,
        timeout_seconds: float = 300.0,
        auto_approve: bool = False,
    ):
        """初始化委托管理器。

        Args:
            max_concurrent: 最大并发子 Agent 数。
            max_depth: 最大委托深度。
            timeout_seconds: 子 Agent 超时时间。
            auto_approve: 是否自动批准危险命令。
        """
        self.max_concurrent = max_concurrent
        self.max_depth = max_depth
        self.timeout_seconds = timeout_seconds
        self.auto_approve = auto_approve
        self._current_depth = 0

    def delegate_task(
        self,
        goal: str | None = None,
        tasks: list[dict[str, Any]] | None = None,
        role: AgentRole = AgentRole.LEAF,
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
        if self._current_depth >= self.max_depth:
            return [DelegationResult(
                task_id="depth_limit",
                success=False,
                error=f"达到最大委托深度 ({self.max_depth})",
            )]

        # 单任务模式
        if goal and not tasks:
            return [self._spawn_single(goal, role, toolsets, context)]

        # 批量模式
        if tasks:
            return self._spawn_batch(tasks, role, toolsets)

        return []

    def _spawn_single(
        self,
        goal: str,
        role: AgentRole,
        toolsets: list[str] | None,
        context: str | None,
    ) -> DelegationResult:
        """Spawn 单个子 Agent。

        Args:
            goal: 目标描述。
            role: 角色。
            toolsets: 工具集。
            context: 上下文。

        Returns:
            委托结果。
        """
        # TODO: 实际实现需要 spawn 子进程/线程
        return DelegationResult(
            task_id="single",
            success=True,
            summary=f"已完成: {goal[:50]}...",
        )

    def _spawn_batch(
        self,
        tasks: list[dict[str, Any]],
        role: AgentRole,
        toolsets: list[str] | None,
    ) -> list[DelegationResult]:
        """批量 Spawn 子 Agent。

        Args:
            tasks: 任务列表。
            role: 角色。
            toolsets: 工具集。

        Returns:
            委托结果列表。
        """
        results = []
        for i, task in enumerate(tasks[:self.max_concurrent]):
            goal = task.get("goal", task.get("description", ""))
            result = self._spawn_single(goal, role, toolsets, task.get("context"))
            result.task_id = f"batch_{i}"
            results.append(result)
        return results


# ============================================================
# 角色系统实现 (任务 3.1-3.5)
# ============================================================

# 被阻止的工具集合 - leaf 角色不能使用这些工具
DELEGATE_BLOCKED_TOOLS = frozenset([
    'delegate_task',    # 阻止递归委托
    'clarify',          # 阻止用户交互
    'memory',           # 阻止写入共享 MEMORY.md
    'send_message',     # 阻止跨平台副作用
    'execute_code',     # 子 Agent 应逐步推理，而非写脚本
])


def filter_blocked_tools(toolsets: list[str] | None) -> list[str]:
    """过滤掉 leaf 角色不允许使用的工具。

    Args:
        toolsets: 原始工具集列表。

    Returns:
        过滤后的工具集列表。
    """
    if toolsets is None:
        return []
    return [t for t in toolsets if t not in DELEGATE_BLOCKED_TOOLS]


def build_child_agent_config(
    goal: str,
    role: AgentRole,
    toolsets: list[str] | None = None,
    context: str | None = None,
) -> dict:
    """构建子 Agent 配置。

    根据角色过滤工具集并生成对应的系统提示。

    Args:
        goal: 任务目标。
        role: 子 Agent 角色。
        toolsets: 请求的工具集。
        context: 额外上下文。

    Returns:
        子 Agent 配置字典。
    """
    if role == AgentRole.LEAF:
        allowed = filter_blocked_tools(toolsets)
        system_prompt = build_leaf_system_prompt()
    else:
        allowed = toolsets or []
        system_prompt = build_orchestrator_system_prompt()

    return {
        "goal": goal,
        "role": role.value,
        "toolsets": allowed,
        "context": context or "",
        "system_prompt": system_prompt,
    }


def build_leaf_system_prompt() -> str:
    """构建 leaf 角色的系统提示。

    Leaf 角色是普通工作者，不能：
    - 委托任务给其他 Agent
    - 与用户交互 (clarify)
    - 写入共享记忆
    - 发送跨平台消息
    """
    return (
        "你是 NanoHermes 的子 Agent (leaf 角色)。"
        "你被限制使用以下工具: " + ", ".join(sorted(DELEGATE_BLOCKED_TOOLS)) + "。"
        "请专注于完成分配给你的任务，不要尝试委托、澄清或发送消息。"
        "你的回答应该只包含任务完成的摘要。"
    )


def build_orchestrator_system_prompt() -> str:
    """构建 orchestrator 角色的系统提示。

    Orchestrator 角色是编排者，可以：
    - 委托子任务
    - 使用所有工具
    - 但不能直接与用户交互
    """
    return (
        "你是 NanoHermes 的编排子 Agent (orchestrator 角色)。"
        "你可以委托子任务给 leaf 角色来完成复杂工作。"
        "请合理分解任务，控制并发数量，确保在超时前完成。"
        "你的最终回答应该包含所有子任务的汇总结果。"
    )

