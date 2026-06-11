"""辅助客户端模块。

辅助 LLM 客户端，为后台任务提供独立于主对话的 LLM 调用能力。
"""

from src.auxiliary.client import AuxiliaryClient

__all__ = ["AuxiliaryClient"]
