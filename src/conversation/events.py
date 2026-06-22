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

责任链拦截机制：
- intercept() 注册拦截器，签名 (data, next) -> None
- emit() 先执行拦截器链（责任链递归），再触发观察者
- 拦截器不调用 next() 表示阻断，返回 ChainResult(blocked=True)
- 拦截器阻断后观察者仍触发（保证持久化/日志不丢失）
- emit() 返回 ChainResult，调用方可检查 blocked 状态
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
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


@dataclass
class ChainResult:
    """责任链执行结果。

    由 emit() 返回，调用方可据此决定是否跳过后续操作。

    Attributes:
        blocked: 是否有拦截器阻断了责任链。
        message: 拦截器提供的阻断原因（用于注入对话或日志）。
    """
    blocked: bool = False
    message: str = ""


# 观察者 handler 签名：(data) -> None
EventHandler = Callable[[Dict[str, Any]], None]

# 拦截器 handler 签名：(data, next_fn) -> None
# next_fn 无参数无返回值，调用即放行，不调用即阻断
ChainInterceptor = Callable[[Dict[str, Any], Callable[[], None]], None]


class EventBus:
    """事件总线，管理事件处理器的订阅和触发。

    支持两种 handler 角色：
    - 拦截器（interceptor）：通过 intercept() 注册，签名 (data, next) -> None
      可修改 data dict，可调用 next() 放行或阻断流程，可执行前后置逻辑（洋葱模型）
    - 观察者（observer）：通过 on() 注册，签名 (data) -> None（不变）
      只读观察，拦截器链完成后触发（无论是否被阻断）

    emit() 执行流程：
    1. 按 priority 升序构建拦截器链
    2. 递归执行拦截器链（责任链模式）
    3. 拦截器链完成后，触发所有观察者
    4. 返回 ChainResult(blocked, message)

    故障隔离：拦截器/观察者异常均被捕获并记录日志，不影响其他 handler。
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        # 拦截器存储：Dict[EventType, List[tuple[priority, ChainInterceptor]]]
        self._interceptors: Dict[EventType, List[tuple[int, ChainInterceptor]]] = {}

    def on(self, event_type: EventType, handler: EventHandler) -> None:
        """订阅事件（观察者模式，fire-and-forget）。"""
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

    def intercept(self, event_type: EventType, handler: ChainInterceptor, priority: int = 0) -> None:
        """注册拦截器（责任链模式）。

        拦截器签名：(data: dict, next_fn: Callable[[], None]) -> None
        - 调用 next_fn() 放行，不调用 next_fn() 阻断
        - 可修改 data dict（可变上下文）
        - 可在 next_fn() 前后执行逻辑（洋葱模型）

        Args:
            event_type: 事件类型。
            handler: 拦截器函数。
            priority: 优先级，越小越先执行（默认 0）。
        """
        if event_type not in self._interceptors:
            self._interceptors[event_type] = []
        self._interceptors[event_type].append((priority, handler))
        # 按 priority 升序排序，相同 priority 保持注册顺序
        self._interceptors[event_type].sort(key=lambda x: x[0])

    def unintercept(self, event_type: EventType, handler: ChainInterceptor) -> None:
        """取消注册拦截器。"""
        if event_type in self._interceptors:
            self._interceptors[event_type] = [
                (p, h) for p, h in self._interceptors[event_type]
                if h is not handler
            ]

    def emit(self, event_type: EventType, data: Dict[str, Any] | None = None) -> ChainResult:
        """触发事件，执行拦截器链后触发观察者。

        执行顺序：
        1. 拦截器链（责任链递归，按 priority 升序）
        2. 观察者（原有 on() handler，无论是否被阻断都触发）

        拦截器不调用 next() 表示阻断，后续拦截器不执行，
        但观察者仍然触发（保证持久化、日志不丢失）。

        Args:
            event_type: 事件类型。
            data: 事件数据（可变上下文，拦截器可修改）。

        Returns:
            ChainResult，包含 blocked 和 message。
        """
        if data is None:
            data = {}

        interceptors = self._interceptors.get(event_type, [])
        result = ChainResult()

        if interceptors:
            # 构建责任链并递归执行
            self._run_chain(interceptors, 0, data, result)

        # 拦截器链完成后，触发所有观察者（无论是否被阻断）
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logger.warning(f"Event handler failed for {event_type.value}: {e}")

        return result

    def _run_chain(
        self,
        interceptors: list[tuple[int, ChainInterceptor]],
        index: int,
        data: Dict[str, Any],
        result: ChainResult,
    ) -> None:
        """递归执行拦截器链。

        设计理由：
        责任链模式让每个拦截器可以：
        1. 修改 data dict（所有后续拦截器和观察者可见）
        2. 调用 next_fn 将控制权交给下一个拦截器
        3. 不调用 next_fn 阻断后续拦截器
        4. 在 next_fn 前后执行逻辑（洋葱模型）

        故障隔离：单个拦截器异常被捕获，跳过该拦截器继续下一个。

        Args:
            interceptors: 已排序的拦截器列表。
            index: 当前执行的拦截器索引。
            data: 可变上下文。
            result: 共享的 ChainResult，用于记录阻断状态。
        """
        if index >= len(interceptors):
            return  # 链尾：放行

        if result.blocked:
            return  # 已被阻断，停止执行

        _, handler = interceptors[index]
        next_called = False

        def next_fn() -> None:
            nonlocal next_called
            next_called = True
            self._run_chain(interceptors, index + 1, data, result)

        try:
            handler(data, next_fn)
        except Exception as e:
            logger.warning(f"Interceptor failed at index {index}: {e}")
            # 故障隔离：跳过该拦截器，继续下一个
            # 异常不视为阻断，继续执行链
            if not next_called:
                self._run_chain(interceptors, index + 1, data, result)
            return  # 异常后不再检查阻断

        # 如果拦截器没有调用 next_fn，表示阻断
        if not next_called and not result.blocked:
            result.blocked = True

    def clear(self, event_type: EventType | None = None) -> None:
        """清除事件订阅。None 时清除所有。"""
        if event_type is None:
            self._handlers.clear()
            self._interceptors.clear()
        elif event_type in self._handlers:
            self._handlers[event_type].clear()
            if event_type in self._interceptors:
                self._interceptors[event_type].clear()
