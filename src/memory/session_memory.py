"""Session Memory Provider - 会话级记忆。

基于阈值的会话记忆管理：
- 当对话达到一定轮次时，自动提取关键信息
- 维护会话摘要，避免上下文丢失
- 与内置文件记忆互补，提供更智能的会话历史管理
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.memory.provider import MemoryProvider
from src.memory.memory_store import get_session_summary_path

logger = logging.getLogger(__name__)


class SessionMemoryProvider(MemoryProvider):
    """会话级记忆提供者。

    职责：
    - 跟踪会话进度（轮次、token 使用）
    - 达到阈值时触发摘要提取
    - 维护会话历史摘要
    """

    # 触发摘要的默认阈值
    DEFAULT_SUMMARY_THRESHOLD = 20  # 轮次
    DEFAULT_SUMMARY_TOKEN_THRESHOLD = 8000  # token 数

    def __init__(
        self,
        memory_dir: Optional[Path] = None,
        summary_threshold: int = DEFAULT_SUMMARY_THRESHOLD,
        token_threshold: int = DEFAULT_SUMMARY_TOKEN_THRESHOLD,
    ):
        self._memory_dir = memory_dir or Path.home() / ".nanohermes" / "memory"
        self._summary_threshold = summary_threshold
        self._token_threshold = token_threshold
        self._session_id: str = ""
        self._turn_count: int = 0
        self._token_count: int = 0
        self._summary: str = ""
        self._initialized: bool = False

    @property
    def name(self) -> str:
        return "session"

    @property
    def is_external(self) -> bool:
        return True

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """初始化会话记忆。

        加载已有会话摘要（如果存在）。
        """
        self._session_id = session_id
        self._turn_count = 0
        self._token_count = 0
        self._summary = ""
        self._initialized = True

        # 加载已有摘要
        try:
            summary_path = get_session_summary_path(session_id, self._memory_dir)
            if summary_path.exists():
                self._summary = summary_path.read_text(encoding="utf-8")
                logger.info(f"Session memory loaded for {session_id}")
        except Exception as e:
            logger.warning(f"Failed to load session summary: {e}")

    def system_prompt_block(self) -> str:
        """返回会话摘要注入到系统提示。"""
        if not self._summary:
            return ""

        return (
            f"<session-summary>\n"
            f"Previous session context:\n{self._summary}\n"
            f"</session-summary>"
        )

    def prefetch(self, query: str, **kwargs) -> str:
        """预取会话记忆（当前仅返回摘要）。"""
        return self._summary

    def sync_turn(self, user_content: str, assistant_content: str, **kwargs) -> None:
        """同步轮次数据，检查是否触发摘要。"""
        self._turn_count += 1

        # 估算 token（简单字符估算）
        self._token_count += len(user_content) + len(assistant_content)

        # 检查是否触发摘要
        if self._should_generate_summary():
            self._trigger_summary(user_content, assistant_content)

    def shutdown(self) -> None:
        """会话结束时保存摘要。"""
        if self._summary and self._session_id:
            try:
                summary_path = get_session_summary_path(self._session_id, self._memory_dir)
                summary_path.parent.mkdir(parents=True, exist_ok=True)
                summary_path.write_text(self._summary, encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to save session summary: {e}")

    def _should_generate_summary(self) -> bool:
        """检查是否应该生成摘要。"""
        return (
            self._turn_count >= self._summary_threshold
            or self._token_count >= self._token_threshold
        )

    def _trigger_summary(self, user_content: str, assistant_content: str) -> None:
        """触发摘要生成（标记需要摘要，实际由后台任务完成）。"""
        logger.info(
            f"Session summary triggered at turn {self._turn_count} "
            f"({self._token_count} tokens)"
        )
        # 标记需要摘要，实际提取由后台任务完成
        self._turn_count = 0
        self._token_count = 0

    def update_summary(self, new_summary: str) -> None:
        """更新会话摘要（由后台任务调用）。"""
        self._summary = new_summary
        logger.info(f"Session summary updated ({len(new_summary)} chars)")

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """不提供工具。"""
        return []
