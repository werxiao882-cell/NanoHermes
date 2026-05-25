"""MemoryManager 编排器。

管理记忆提供者生命周期：
- 注册提供者（内置 + 外部）
- 强制执行单外部提供者限制
- 编排 initialize / prefetch / sync_turn / shutdown
- 构建系统提示中的记忆上下文
- 上下文隔离标签 (<memory-context>)
"""

from __future__ import annotations

from typing import Any

from src.memory.provider import MemoryProvider


# 上下文隔离标签
MEMORY_CONTEXT_OPEN = "<memory-context>"
MEMORY_CONTEXT_CLOSE = "</memory-context>"


class MemoryManager:
    """记忆管理器。

    编排所有记忆提供者，确保：
    - 最多一个外部提供者
    - 正确的生命周期调用顺序
    - 上下文隔离
    """

    def __init__(self):
        """初始化记忆管理器。"""
        self._providers: list[MemoryProvider] = []
        self._external_count = 0

    def add_provider(self, provider: MemoryProvider) -> None:
        """注册一个记忆提供者。

        Args:
            provider: MemoryProvider 实例。

        Raises:
            ValueError: 如果尝试注册第二个外部提供者。
        """
        if provider.is_external and self._external_count >= 1:
            raise ValueError("只允许注册一个外部记忆提供者")

        self._providers.append(provider)
        if provider.is_external:
            self._external_count += 1

    def initialize_all(self, options: dict[str, Any]) -> None:
        """初始化所有提供者。

        Args:
            options: 初始化选项。
        """
        for provider in self._providers:
            provider.initialize(options)

    def prefetch_all(self, query: str) -> str:
        """预取所有提供者的记忆内容。

        Args:
            query: 查询字符串。

        Returns:
            包裹在 <memory-context> 标签中的记忆内容。
        """
        parts = []
        for provider in self._providers:
            content = provider.prefetch(query)
            if content:
                parts.append(f"<!-- from: {provider.name} -->\n{content}")

        if not parts:
            return ""

        return f"{MEMORY_CONTEXT_OPEN}\n" + "\n\n".join(parts) + f"\n{MEMORY_CONTEXT_CLOSE}"

    def sync_all(self, messages: list[dict[str, Any]]) -> None:
        """同步所有提供者。

        Args:
            messages: 当前轮次消息。
        """
        for provider in self._providers:
            provider.sync_turn(messages)

    def shutdown_all(self) -> None:
        """关闭所有提供者。"""
        for provider in self._providers:
            provider.shutdown()

    def build_system_prompt_section(self, query: str = "") -> str:
        """构建系统提示中的记忆部分。

        Args:
            query: 可选查询字符串。

        Returns:
            记忆上下文字符串。
        """
        return self.prefetch_all(query)
