"""对话循环事件系统。

提供事件总线机制，解耦对话循环逻辑与外部处理器。
支持的事件类型：
- turn_start: 每轮对话开始
- tool_start: 工具开始执行
- tool_end: 工具执行结束
- message_append: 消息追加到历史
- turn_complete: 每轮模型调用完成
- post_turn: 后轮次钩子
- interrupt: 对话循环被中断
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, List


class EventType(Enum):
    """事件类型枚举。"""
    TURN_START = "turn_start"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    MESSAGE_APPEND = "message_append"
    TURN_COMPLETE = "turn_complete"
    POST_TURN = "post_turn"
    INTERRUPT = "interrupt"


# 事件处理器类型：接收事件数据，返回 None
EventHandler = Callable[[Dict[str, Any]], None]


class EventBus:
    """事件总线，管理事件处理器的订阅和触发。

    支持多个处理器订阅同一事件类型，按订阅顺序触发。
    处理器异常会被捕获并记录日志，不影响其他处理器。
    """

    def __init__(self):
        """初始化事件总线。"""
        self._handlers: Dict[EventType, List[EventHandler]] = {}

    def on(self, event_type: EventType, handler: EventHandler) -> None:
        """订阅事件。

        Args:
            event_type: 事件类型。
            handler: 事件处理器函数。
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def off(self, event_type: EventType, handler: EventHandler) -> None:
        """取消订阅事件。

        Args:
            event_type: 事件类型。
            handler: 要移除的事件处理器函数。
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def emit(self, event_type: EventType, data: Dict[str, Any] | None = None) -> None:
        """触发事件，调用所有订阅的处理器。

        Args:
            event_type: 事件类型。
            data: 事件数据字典。
        """
        if event_type not in self._handlers:
            return

        if data is None:
            data = {}

        for handler in self._handlers[event_type]:
            try:
                handler(data)
            except Exception as e:
                # 记录异常但不中断其他处理器
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Event handler failed for {event_type.value}: {e}")

    def clear(self, event_type: EventType | None = None) -> None:
        """清除事件订阅。

        Args:
            event_type: 指定事件类型。None 时清除所有订阅。
        """
        if event_type is None:
            self._handlers.clear()
        elif event_type in self._handlers:
            self._handlers[event_type].clear()
