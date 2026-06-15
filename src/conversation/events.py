"""对话循环事件系统。

提供事件总线机制，解耦对话循环逻辑与外部处理器。

事件分类（18 种）：
- 生命周期事件：loop_start, loop_end, iteration_start, iteration_end
- 模型调用事件：model_request, model_response, model_error, model_retry
- 工具事件：tool_start, tool_end, tool_error
- 消息事件：message_append
- 上下文事件：pre_compress
- 控制事件：interrupt, max_iterations
- 委托事件：delegation_start, delegation_complete, delegation_fail
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型枚举。"""

    # 生命周期事件
    LOOP_START = "loop_start"
    LOOP_END = "loop_end"
    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"

    # 模型调用事件
    MODEL_REQUEST = "model_request"
    MODEL_RESPONSE = "model_response"
    MODEL_ERROR = "model_error"
    MODEL_RETRY = "model_retry"

    # 工具事件
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"

    # 消息事件
    MESSAGE_APPEND = "message_append"

    # 上下文事件
    PRE_COMPRESS = "pre_compress"

    # 控制事件
    INTERRUPT = "interrupt"
    MAX_ITERATIONS = "max_iterations"

    # 委托事件
    DELEGATION_START = "delegation_start"
    DELEGATION_COMPLETE = "delegation_complete"
    DELEGATION_FAIL = "delegation_fail"


EventHandler = Callable[[Dict[str, Any]], None]


class EventBus:
    """事件总线，管理事件处理器的订阅和触发。

    支持多个处理器订阅同一事件类型，按订阅顺序触发。
    处理器异常会被捕获并记录日志，不影响其他处理器和循环本身。
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}

    def on(self, event_type: EventType, handler: EventHandler) -> None:
        """订阅事件。"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def off(self, event_type: EventType, handler: EventHandler) -> None:
        """取消订阅事件。"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def emit(self, event_type: EventType, data: Dict[str, Any] | None = None) -> None:
        """触发事件，调用所有订阅的处理器。

        处理器异常会被捕获并记录日志，不影响其他处理器。
        """
        if event_type not in self._handlers:
            return

        if data is None:
            data = {}

        for handler in self._handlers[event_type]:
            try:
                handler(data)
            except Exception as e:
                logger.warning(f"Event handler failed for {event_type.value}: {e}")

    def clear(self, event_type: EventType | None = None) -> None:
        """清除事件订阅。None 时清除所有。"""
        if event_type is None:
            self._handlers.clear()
        elif event_type in self._handlers:
            self._handlers[event_type].clear()
