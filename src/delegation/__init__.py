"""多 Agent 委托模块。

父 Agent 委托任务给隔离子 Agent：
- 单任务 (goal) 和批量并行 (tasks) 模式
- leaf / orchestrator 角色
- 并发和深度控制
- 超时终止和事件总线集成

单例访问：
    from src.delegation import get_manager, init_manager

    # TUI 初始化时调用一次
    init_manager(model_caller=..., tool_dispatch=..., tool_schemas=...)

    # 其他模块直接获取
    mgr = get_manager()
"""

from src.delegation.types import (
    AgentRole,
    ChildAgentConfig,
    DelegationResult,
    DELEGATE_BLOCKED_TOOLS,
    ORCHESTRATOR_ALLOWED_TOOLS,
)
from src.delegation.semaphore import Semaphore
from src.delegation.manager import DelegationManager

# 全局单例
_manager: DelegationManager | None = None


def init_manager(
    model_caller=None,
    tool_dispatch=None,
    tool_schemas=None,
    max_concurrent_children: int = 3,
    max_spawn_depth: int = 2,
    child_timeout_seconds: float = 300.0,
    subagent_auto_approve: bool = False,
    parent_event_bus=None,
    parent_session_id: str = "",
) -> DelegationManager:
    """初始化全局 DelegationManager 单例。

    由 TUI 启动时调用一次。内部自动创建 EventBus，无需外部传入。

    Args:
        model_caller: LLM 调用函数。
        tool_dispatch: 工具分发函数。
        tool_schemas: 完整工具 schema 列表。
        max_concurrent_children: 最大并发子 Agent 数。
        max_spawn_depth: 最大委托深度。
        child_timeout_seconds: 子 Agent 超时时间（秒）。
        subagent_auto_approve: 是否自动批准危险命令。
        parent_event_bus: 父 Agent 的事件总线，用于转发子 Agent 事件到 TUI。
        parent_session_id: 父 Agent 的会话 ID，用于子 Agent JSONL 命名关联。

    Returns:
        创建的 DelegationManager 实例。
    """
    global _manager
    _manager = DelegationManager(
        max_concurrent_children=max_concurrent_children,
        max_spawn_depth=max_spawn_depth,
        child_timeout_seconds=child_timeout_seconds,
        subagent_auto_approve=subagent_auto_approve,
        model_caller=model_caller,
        tool_dispatch=tool_dispatch,
        tool_schemas=tool_schemas,
        parent_event_bus=parent_event_bus,
        parent_session_id=parent_session_id,
    )
    return _manager


def get_manager() -> DelegationManager | None:
    """获取全局 DelegationManager 单例。

    Returns:
        DelegationManager 实例，未初始化时返回 None。
    """
    return _manager


def reset_manager() -> None:
    """重置全局单例（用于测试）。"""
    global _manager
    _manager = None


__all__ = [
    "AgentRole",
    "ChildAgentConfig",
    "DelegationResult",
    "DELEGATE_BLOCKED_TOOLS",
    "ORCHESTRATOR_ALLOWED_TOOLS",
    "Semaphore",
    "DelegationManager",
    "init_manager",
    "get_manager",
    "reset_manager",
]
