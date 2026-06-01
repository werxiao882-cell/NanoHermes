"""ConversationLoop - 核心对话循环。

循环流程：
1. 组装系统提示
2. 调用模型
3. 处理工具调用
4. 错误分类和重试
5. 后轮次钩子
6. 压缩触发检查

事件系统：
- 使用 EventBus 解耦循环逻辑与外部处理器
- 支持 16 种事件类型，覆盖完整生命周期
- 外部功能通过 loop.events.on() 订阅事件接入

Debug 模式：
- 输出发送到模型的完整请求体（JSON）
- 输出模型返回的完整响应体（JSON）
- 输出模型的思考内容（reasoning）
- 输出工具调用和结果
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from src.conversation.error_classifier import ErrorClassifier, ErrorCategory
from src.conversation.events import EventBus, EventType

logger = logging.getLogger(__name__)


class ConversationLoop:
    """核心对话循环。

    管理模型调用、工具分发、重试、压缩触发的完整循环。
    通过 EventBus 与外部功能解耦。

    Attributes:
        max_iterations: 最大迭代次数。
        events: 事件总线，用于订阅和触发事件。
        debug: 是否开启 debug 模式。
    """

    def __init__(
        self,
        max_iterations: int = 90,
        model_call: Callable | None = None,
        tool_dispatch: Callable | None = None,
        debug: bool = False,
    ):
        """初始化对话循环。

        Args:
            max_iterations: 最大迭代次数。
            model_call: 模型调用函数。
            tool_dispatch: 工具分发函数。
            debug: 是否开启 debug 模式，输出请求/响应详情。
        """
        self.max_iterations = max_iterations
        self._model_call = model_call
        self._tool_dispatch = tool_dispatch
        self._error_classifier = ErrorClassifier()
        self._interrupted = False
        self.debug = debug

        self.events = EventBus()

    def run(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """运行对话循环。

        Args:
            messages: 消息列表。
            tools: 工具 schema 列表。

        Returns:
            包含最终响应和元数据的字典。
        """
        iteration = 0
        start_time = time.time()

        self.events.emit(EventType.LOOP_START, {
            "messages": messages,
            "tools": tools,
            "max_iterations": self.max_iterations,
        })

        while iteration < self.max_iterations:
            if self._interrupted:
                self.events.emit(EventType.INTERRUPT, {"iteration": iteration})
                break

            iteration += 1

            self.events.emit(EventType.ITERATION_START, {
                "iteration": iteration,
                "messages": messages,
            })

            # Debug: 输出请求体
            if self.debug:
                self._debug_print_request(iteration, messages, tools)

            # 调用模型
            model_start = time.time()
            try:
                self.events.emit(EventType.MODEL_REQUEST, {
                    "messages": messages,
                    "tools": tools,
                    "iteration": iteration,
                })
                response = self._call_model(messages, tools)
                model_elapsed = time.time() - model_start

                self.events.emit(EventType.MODEL_RESPONSE, {
                    "response": response,
                    "iteration": iteration,
                    "elapsed": model_elapsed,
                })
            except Exception as e:
                model_elapsed = time.time() - model_start
                classified = self._error_classifier.classify(
                    getattr(e, "status_code", None),
                    str(e),
                )
                self.events.emit(EventType.MODEL_ERROR, {
                    "error": e,
                    "classified": classified,
                    "iteration": iteration,
                    "elapsed": model_elapsed,
                })
                if classified.retryable and iteration < self.max_iterations:
                    logger.warning(f"可重试错误，重试中: {classified.message}")
                    self.events.emit(EventType.MODEL_RETRY, {
                        "error": e,
                        "attempt": iteration,
                        "iteration": iteration,
                    })
                    continue
                raise

            # Debug: 输出响应体和 reasoning
            if self.debug:
                self._debug_print_response(iteration, response)

            self.events.emit(EventType.ITERATION_END, {
                "iteration": iteration,
                "response": response,
            })

            # 检查是否有工具调用
            if response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    func = tool_call.get("function", {})
                    tool_name = func.get("name", "unknown")
                    tool_args = func.get("arguments", "{}")

                    tool_start = time.time()

                    self.events.emit(EventType.TOOL_START, {
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "tool_call": tool_call,
                    })

                    try:
                        result = self._dispatch_tool(tool_call)
                    except Exception as e:
                        tool_elapsed = time.time() - tool_start
                        self.events.emit(EventType.TOOL_ERROR, {
                            "tool_name": tool_name,
                            "error": e,
                            "tool_call": tool_call,
                            "elapsed": tool_elapsed,
                        })
                        result = json.dumps({"error": str(e)})

                    tool_elapsed = time.time() - tool_start

                    self.events.emit(EventType.TOOL_END, {
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "result": result,
                        "elapsed": tool_elapsed,
                        "tool_call": tool_call,
                    })

                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": result,
                    }
                    messages.append(tool_message)

                    self.events.emit(EventType.MESSAGE_APPEND, {
                        "message": tool_message,
                        "messages": messages,
                    })
                continue

            # 文本响应，结束循环
            total_elapsed = time.time() - start_time
            result = {
                "final_response": response.get("content", ""),
                "reasoning": response.get("reasoning"),
                "iterations": iteration,
                "usage": response.get("usage"),
                "raw_response": response.get("raw_response"),
            }

            self.events.emit(EventType.LOOP_END, {
                "result": result,
                "iterations": iteration,
                "total_elapsed": total_elapsed,
            })

            return result

        # 达到最大迭代
        total_elapsed = time.time() - start_time
        self.events.emit(EventType.MAX_ITERATIONS, {"iterations": iteration})

        result = {
            "final_response": "[达到最大迭代次数]",
            "reasoning": None,
            "iterations": iteration,
            "usage": None,
            "raw_response": None,
        }

        self.events.emit(EventType.LOOP_END, {
            "result": result,
            "iterations": iteration,
            "total_elapsed": total_elapsed,
        })

        return result

    # ========================================================================
    # Debug 输出
    # ========================================================================

    def _debug_print_request(
        self,
        iteration: int,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> None:
        """Debug: 打印发送到模型的完整请求体（JSON）。"""
        request_body = {"messages": messages}
        if tools:
            request_body["tools"] = tools

        print(f"\n{'='*70}")
        print(f"[DEBUG] >>> 第 {iteration} 轮 - 请求体 (Request Body)")
        print(f"{'='*70}")
        print(json.dumps(request_body, ensure_ascii=False, indent=2))
        print(f"{'='*70}\n")

    def _debug_print_response(self, iteration: int, response: dict[str, Any]) -> None:
        """Debug: 打印模型返回的完整响应体（JSON）和思考内容。"""
        reasoning = response.get("reasoning")
        if reasoning:
            print(f"\n{'='*70}")
            print(f"[DEBUG] 第 {iteration} 轮 - 思考内容 (Reasoning)")
            print(f"{'='*70}")
            print(reasoning)
            print(f"{'='*70}\n")

        raw_response = response.get("raw_response")
        if raw_response:
            print(f"\n{'='*70}")
            print(f"[DEBUG] <<< 第 {iteration} 轮 - 响应体 (Response Body)")
            print(f"{'='*70}")
            if isinstance(raw_response, dict):
                print(json.dumps(raw_response, ensure_ascii=False, indent=2))
            else:
                print(raw_response)
            print(f"{'='*70}\n")
        else:
            print(f"\n{'='*70}")
            print(f"[DEBUG] <<< 第 {iteration} 轮 - 响应摘要")
            print(f"{'='*70}")

            content = response.get("content", "")
            if content:
                if len(content) > 500:
                    content = content[:500] + "..."
                print(f"内容: {content}")

            tool_calls = response.get("tool_calls")
            if tool_calls:
                print(f"\n工具调用: {len(tool_calls)} 个")
                for tc in tool_calls:
                    func = tc.get("function", {})
                    print(f"  - {func.get('name', '')}({func.get('arguments', '')})")

            usage = response.get("usage")
            if usage:
                print(f"\nToken 用量: 输入 {usage.get('input_tokens', 0)}, 输出 {usage.get('output_tokens', 0)}")
            print()

    # ========================================================================
    # 内部方法
    # ========================================================================

    def _call_model(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """调用模型。"""
        if self._model_call:
            return self._model_call(messages, tools)
        raise NotImplementedError("未设置 model_call 函数")

    def _dispatch_tool(self, tool_call: dict[str, Any]) -> str:
        """分发工具调用。"""
        if self._tool_dispatch:
            func = tool_call.get("function", {})
            return self._tool_dispatch(
                func.get("name", ""),
                func.get("arguments", {}),
            )
        return '{"error": "工具分发未实现"}'

    def interrupt(self) -> None:
        """中断对话循环。"""
        self._interrupted = True
