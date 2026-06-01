"""Memory 事件处理器。

订阅 ConversationLoop 的事件总线，在合适的时机调用 MemoryManager。

集成点（参考 hermes-agent-ref）：
- LOOP_START: 初始化所有 memory providers
- ITERATION_START (首次): on_turn_start + prefetch_all，注入记忆上下文
- LOOP_END: sync_all + queue_prefetch_all（仅完成的轮次）
- INTERRUPT: 跳过 sync（中断的轮次不同步）
- PRE_COMPRESS: on_pre_compress，压缩前提取信息
"""

from __future__ import annotations

import logging
from typing import Any

from src.conversation.events import EventBus, EventType
from src.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class MemoryEventHandler:
    """Memory 事件处理器，桥接 MemoryManager 与 ConversationLoop。

    通过订阅 EventBus 事件，在对话循环的关键节点调用 MemoryManager，
    实现记忆的注入、同步和生命周期管理。
    """

    def __init__(self, memory_manager: MemoryManager, session_id: str = ""):
        """初始化 Memory 事件处理器。

        Args:
            memory_manager: MemoryManager 实例。
            session_id: 当前会话 ID。
        """
        self._memory_manager = memory_manager
        self._session_id = session_id
        self._turn_count = 0
        self._interrupted = False
        self._last_user_message = ""
        self._prefetch_cache = ""

    @property
    def prefetch_cache(self) -> str:
        """获取预取的记忆上下文（供外部注入到消息中）。"""
        return self._prefetch_cache

    def register(self, events: EventBus) -> None:
        """将所有处理器注册到事件总线。"""
        events.on(EventType.LOOP_START, self._on_loop_start)
        events.on(EventType.ITERATION_START, self._on_iteration_start)
        events.on(EventType.LOOP_END, self._on_loop_end)
        events.on(EventType.INTERRUPT, self._on_interrupt)
        events.on(EventType.PRE_COMPRESS, self._on_pre_compress)

    def _on_loop_start(self, data: dict[str, Any]) -> None:
        """循环开始：初始化所有 memory providers。"""
        self._turn_count = 0
        self._interrupted = False
        self._prefetch_cache = ""

        try:
            self._memory_manager.initialize_all(self._session_id)
        except Exception as e:
            logger.warning(f"Memory providers initialization failed: {e}")

    def _on_iteration_start(self, data: dict[str, Any]) -> None:
        """迭代开始：首次迭代时执行 on_turn_start + prefetch_all。

        只在首次迭代（iteration=1）时执行，避免每轮工具调用都重复预取。
        """
        iteration = data.get("iteration", 0)
        messages = data.get("messages", [])

        if iteration != 1:
            return

        self._turn_count += 1

        # 提取用户消息（最后一条 user 消息）
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        self._last_user_message = user_message

        # on_turn_start: 通知 providers 当前轮次
        try:
            self._memory_manager.on_turn_start_all(
                self._turn_count, user_message,
                session_id=self._session_id,
            )
        except Exception as e:
            logger.warning(f"Memory on_turn_start failed: {e}")

        # prefetch_all: 预取记忆上下文（缓存，不重复调用）
        try:
            self._prefetch_cache = self._memory_manager.prefetch_all(
                user_message, session_id=self._session_id,
            ) or ""
        except Exception as e:
            logger.warning(f"Memory prefetch failed: {e}")
            self._prefetch_cache = ""

    def _on_loop_end(self, data: dict[str, Any]) -> None:
        """循环结束：sync_all + queue_prefetch_all（仅完成的轮次）。

        中断的轮次不同步——部分助手输出、中止的工具链不是持久的对话事实。
        """
        if self._interrupted:
            return

        result = data.get("result", {})
        final_response = result.get("final_response", "")

        if not final_response or not self._last_user_message:
            return

        try:
            self._memory_manager.sync_all(
                self._last_user_message,
                final_response,
                session_id=self._session_id,
            )
        except Exception as e:
            logger.warning(f"Memory sync failed: {e}")

        try:
            self._memory_manager.queue_prefetch_all(
                self._last_user_message,
                session_id=self._session_id,
            )
        except Exception as e:
            logger.warning(f"Memory queue_prefetch failed: {e}")

    def _on_interrupt(self, data: dict[str, Any]) -> None:
        """循环被中断：标记中断，跳过 sync。"""
        self._interrupted = True

    def _on_pre_compress(self, data: dict[str, Any]) -> None:
        """压缩前：通知 providers 提取信息。"""
        messages = data.get("messages", [])
        try:
            extracted = self._memory_manager.on_pre_compress_all(messages)
            if extracted:
                data["extracted_memory"] = extracted
        except Exception as e:
            logger.warning(f"Memory on_pre_compress failed: {e}")

    def shutdown(self, messages: list[dict[str, Any]] | None = None) -> None:
        """会话结束：on_session_end + shutdown_all。

        在 CLI 退出、会话重置时调用。
        """
        try:
            self._memory_manager.on_session_end_all(messages or [])
        except Exception as e:
            logger.warning(f"Memory on_session_end failed: {e}")

        try:
            self._memory_manager.shutdown_all()
        except Exception as e:
            logger.warning(f"Memory shutdown failed: {e}")

    def commit_session(self, messages: list[dict[str, Any]] | None = None) -> None:
        """提交会话记忆（不关闭 providers）。

        在 session_id 轮换时调用（如 /new、上下文压缩），
        providers 保持状态继续运行，只是立即刷出待提取的内容。
        """
        try:
            self._memory_manager.on_session_end_all(messages or [])
        except Exception as e:
            logger.warning(f"Memory commit_session failed: {e}")
