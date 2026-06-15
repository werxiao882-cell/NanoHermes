"""委托系统类型定义和常量。

定义子 Agent 角色、工具阻止列表、结果和配置数据类。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AgentRole(Enum):
    """子 Agent 角色。

    设计理由：
    - LEAF（叶子节点）：普通工作者，只能完成分配的特定任务，不能进一步委托。
      这防止了无限递归委托导致的资源耗尽，也简化了子 Agent 的权限模型。
    - ORCHESTRATOR（编排者）：可以分解任务并进一步委托给子 Agent。
      适用于需要将大任务拆解为多个子任务的场景，但受 max_spawn_depth 限制。

    安全考量：
    - 角色决定了子 Agent 可以访问哪些工具，这是权限控制的第一道防线。
    - LEAF 角色被明确禁止访问危险工具（见 DELEGATE_BLOCKED_TOOLS）。
    """
    LEAF = "leaf"
    ORCHESTRATOR = "orchestrator"


# 子 Agent 绝不能访问的工具
DELEGATE_BLOCKED_TOOLS: frozenset[str] = frozenset([
    "delegate_task",    # 禁止递归委托：防止 LEAF 角色继续生成子 Agent 导致无限递归
    "clarify",          # 禁止用户交互：子 Agent 不应直接打扰用户，澄清应由主 Agent 处理
    "memory",           # 禁止写入共享记忆：防止多个子 Agent 同时写入 MEMORY.md 导致冲突
    "execute_code",     # 子 Agent 应逐步推理，而非编写脚本：降低代码执行的安全风险
])

# Orchestrator 可以使用的额外工具
ORCHESTRATOR_ALLOWED_TOOLS: frozenset[str] = frozenset([
    "delegate_task",    # 允许进一步委托：ORCHESTRATOR 的核心能力是任务分解和分发
])


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
    parent_session_id: str = ""
