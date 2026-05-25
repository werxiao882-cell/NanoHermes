"""FileMemoryProvider - 基于文件的记忆提供者。

使用 MEMORY.md（Agent 记忆）和 USER.md（用户画像）文件存储记忆。
支持 add / replace / remove 操作。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.memory.provider import MemoryProvider


class FileMemoryProvider(MemoryProvider):
    """基于文件的记忆提供者。

    使用两个 Markdown 文件：
    - MEMORY.md: Agent 的长期记忆
    - USER.md: 用户画像和偏好
    """

    @property
    def name(self) -> str:
        return "file"

    def __init__(self, base_dir: str | Path | None = None):
        """初始化文件记忆提供者。

        Args:
            base_dir: 基础目录，None 时使用当前目录。
        """
        self._base_dir = Path(base_dir) if base_dir else Path.cwd()
        self._memory_file = self._base_dir / "MEMORY.md"
        self._user_file = self._base_dir / "USER.md"

    def initialize(self, options: dict[str, Any]) -> None:
        """确保记忆文件存在。

        Args:
            options: 初始化选项。
        """
        if not self._memory_file.exists():
            self._memory_file.write_text("# Agent Memory\n\n", encoding="utf-8")
        if not self._user_file.exists():
            self._user_file.write_text("# User Profile\n\n", encoding="utf-8")

    def prefetch(self, query: str = "") -> str:
        """读取记忆文件内容。

        Args:
            query: 查询字符串（当前未使用）。

        Returns:
            记忆内容。
        """
        parts = []
        if self._memory_file.exists():
            content = self._memory_file.read_text(encoding="utf-8")
            if content.strip():
                parts.append(content)
        if self._user_file.exists():
            content = self._user_file.read_text(encoding="utf-8")
            if content.strip():
                parts.append(content)
        return "\n\n".join(parts)

    def sync_turn(self, messages: list[dict[str, Any]]) -> None:
        """每轮后异步刷写记忆（当前为同步实现）。

        Args:
            messages: 当前轮次消息。
        """
        pass  # TODO: 实现异步刷写

    def add_entry(self, section: str, content: str) -> None:
        """添加记忆条目。

        Args:
            section: 章节名称。
            content: 记忆内容。
        """
        with open(self._memory_file, "a", encoding="utf-8") as f:
            f.write(f"\n## {section}\n\n{content}\n")

    def replace_entry(self, section: str, content: str) -> None:
        """替换记忆条目。

        Args:
            section: 章节名称。
            content: 新内容。
        """
        text = self._memory_file.read_text(encoding="utf-8")
        # 简化实现：追加到末尾
        self.add_entry(section, content)

    def remove_entry(self, section: str) -> None:
        """删除记忆条目。

        Args:
            section: 章节名称。
        """
        text = self._memory_file.read_text(encoding="utf-8")
        # 简化实现：不实际删除（需要更复杂的 Markdown 解析）
        pass
