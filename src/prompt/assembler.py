"""系统提示组装模块。

三层架构：
1. stable: 身份、工具指导、技能提示、环境提示（缓存友好）
2. context: 上下文文件、system_message
3. volatile: 记忆快照、用户画像、时间戳（每轮变化）
"""

from __future__ import annotations

from typing import Any


class PromptAssembler:
    """三层系统提示组装器。

    stable 部分变化时重建缓存，volatile 部分每轮更新。
    """

    def __init__(self):
        """初始化提示组装器。"""
        self._stable_parts: list[str] = []
        self._context_parts: list[str] = []
        self._volatile_parts: list[str] = []

    def set_stable(self, parts: list[str]) -> None:
        """设置 stable 层（身份、工具指导等）。

        Args:
            parts: stable 层文本片段列表。
        """
        self._stable_parts = parts

    def set_context(self, parts: list[str]) -> None:
        """设置 context 层（上下文文件等）。

        Args:
            parts: context 层文本片段列表。
        """
        self._context_parts = parts

    def set_volatile(self, parts: list[str]) -> None:
        """设置 volatile 层（记忆、画像等）。

        Args:
            parts: volatile 层文本片段列表。
        """
        self._volatile_parts = parts

    def assemble(self) -> str:
        """组装完整系统提示。

        Returns:
            完整的系统提示文本。
        """
        parts = []
        if self._stable_parts:
            parts.append("\n".join(self._stable_parts))
        if self._context_parts:
            parts.append("\n".join(self._context_parts))
        if self._volatile_parts:
            parts.append("\n".join(self._volatile_parts))
        return "\n\n".join(parts)

    def get_stable_hash(self) -> int:
        """获取 stable 层的哈希，用于缓存判断。

        Returns:
            stable 层内容的哈希值。
        """
        return hash("".join(self._stable_parts))
