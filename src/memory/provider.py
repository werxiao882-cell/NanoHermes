"""MemoryProvider 抽象基类。

定义记忆提供者的标准生命周期钩子：
- initialize: 初始化
- prefetch: 预取记忆内容
- sync_turn: 每轮对话后同步
- shutdown: 关闭

可选钩子：
- on_turn_start / on_session_end / on_session_switch
- on_pre_compress / on_delegation / on_memory_write
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryProvider(ABC):
    """记忆提供者抽象基类。

    所有记忆后端（文件、honcho、mem0 等）必须实现此接口。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称。"""
        ...

    @property
    def is_external(self) -> bool:
        """是否为外部提供者（非内置）。"""
        return False

    def initialize(self, options: dict[str, Any]) -> None:
        """初始化提供者。

        Args:
            options: 初始化选项。
        """
        pass

    def prefetch(self, query: str) -> str:
        """预取记忆内容。

        Args:
            query: 查询字符串。

        Returns:
            记忆内容文本。
        """
        return ""

    def sync_turn(self, messages: list[dict[str, Any]]) -> None:
        """每轮对话后同步记忆。

        Args:
            messages: 当前轮次的消息列表。
        """
        pass

    def shutdown(self) -> None:
        """关闭提供者，释放资源。"""
        pass

    # --- 可选钩子 ---

    def on_turn_start(self, messages: list[dict[str, Any]]) -> None:
        """轮次开始时调用。"""
        pass

    def on_session_end(self, session_id: str) -> None:
        """会话结束时调用。"""
        pass

    def on_session_switch(self, session_id: str) -> None:
        """会话切换时调用。"""
        pass

    def on_pre_compress(self, session_id: str) -> None:
        """压缩前调用，用于刷写持久记忆。"""
        pass

    def on_delegation(self, task: str) -> str:
        """委托时提供相关记忆。"""
        return ""

    def on_memory_write(self, action: str, content: str) -> None:
        """记忆写入时调用。"""
        pass
