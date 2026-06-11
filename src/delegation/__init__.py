"""多 Agent 委托模块。

父 Agent 委托任务给隔离子 Agent：
- 单任务 (goal) 和批量并行 (tasks) 模式
- leaf / orchestrator 角色
- 并发和深度控制
"""

from src.delegation.manager import DelegationManager

__all__ = ["DelegationManager"]
