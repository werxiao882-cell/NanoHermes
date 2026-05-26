"""ConversationLoop - 核心对话循环。

循环流程：
1. 组装系统提示
2. 调用模型
3. 处理工具调用
4. 错误分类和重试
5. 后轮次钩子
6. 压缩触发检查

Debug 模式：
- 输出发送到模型的完整请求体（JSON）
- 输出模型返回的完整响应体（JSON）
- 输出模型的思考内容（reasoning）
- 输出工具调用和结果
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from src.conversation.error_classifier import ErrorClassifier, ErrorCategory

logger = logging.getLogger(__name__)


class ConversationLoop:
    """核心对话循环。

    管理模型调用、工具分发、重试、压缩触发的完整循环。

    Attributes:
        max_iterations: 最大迭代次数。
        model_call: 模型调用函数。
        tool_dispatch: 工具分发函数。
        error_classifier: 错误分类器。
        on_post_turn: 后轮次钩子。
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
        self._on_post_turn: Callable | None = None
        self._interrupted = False
        self.debug = debug

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

        while iteration < self.max_iterations:
            if self._interrupted:
                break

            iteration += 1

            # Debug: 输出请求体
            if self.debug:
                self._debug_print_request(iteration, messages, tools)

            # 调用模型
            try:
                response = self._call_model(messages, tools)
            except Exception as e:
                classified = self._error_classifier.classify(
                    getattr(e, "status_code", None),
                    str(e),
                )
                if classified.retryable and iteration < self.max_iterations:
                    logger.warning(f"可重试错误，重试中: {classified.message}")
                    continue
                raise

            # Debug: 输出响应体和 reasoning
            if self.debug:
                self._debug_print_response(iteration, response)

            # 检查是否有工具调用
            if response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    result = self._dispatch_tool(tool_call)

                    # Debug: 输出工具结果
                    if self.debug:
                        self._debug_print_tool(tool_call, result)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": result,
                    })
                continue

            # 文本响应，结束循环
            return {
                "final_response": response.get("content", ""),
                "iterations": iteration,
                "usage": response.get("usage"),
            }

        # 达到最大迭代
        return {
            "final_response": "[达到最大迭代次数]",
            "iterations": iteration,
            "usage": None,
        }

    def _debug_print_request(
        self,
        iteration: int,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> None:
        """Debug: 打印发送到模型的完整请求体（JSON）。

        Args:
            iteration: 当前迭代次数。
            messages: 消息列表。
            tools: 工具 schema 列表。
        """
        request_body = {
            "messages": messages,
        }
        if tools:
            request_body["tools"] = tools

        print(f"\n{'='*70}")
        print(f"[DEBUG] >>> 第 {iteration} 轮 - 请求体 (Request Body)")
        print(f"{'='*70}")
        print(json.dumps(request_body, ensure_ascii=False, indent=2))
        print(f"{'='*70}\n")

    def _debug_print_response(self, iteration: int, response: dict[str, Any]) -> None:
        """Debug: 打印模型返回的完整响应体（JSON）和思考内容。

        Args:
            iteration: 当前迭代次数。
            response: 模型响应。
        """
        # 打印 reasoning（思考内容）
        reasoning = response.get("reasoning")
        if reasoning:
            print(f"\n{'='*70}")
            print(f"[DEBUG] 第 {iteration} 轮 - 思考内容 (Reasoning)")
            print(f"{'='*70}")
            print(reasoning)
            print(f"{'='*70}\n")

        # 打印完整响应体
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
            # 如果没有 raw_response，打印摘要
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

    def _debug_print_tool(self, tool_call: dict[str, Any], result: str) -> None:
        """Debug: 打印工具执行结果。

        Args:
            tool_call: 工具调用信息。
            result: 工具执行结果。
        """
        func = tool_call.get("function", {})
        name = func.get("name", "unknown")

        # 截断长结果
        display_result = result
        if len(display_result) > 300:
            display_result = display_result[:300] + "..."

        print(f"[DEBUG] 工具执行: {name}")
        print(f"  参数: {func.get('arguments', '')}")
        print(f"  结果: {display_result}")
        print()

    def _call_model(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """调用模型。

        Args:
            messages: 消息列表。
            tools: 工具 schema。

        Returns:
            模型响应。
        """
        if self._model_call:
            return self._model_call(messages, tools)
        raise NotImplementedError("未设置 model_call 函数")

    def _dispatch_tool(self, tool_call: dict[str, Any]) -> str:
        """分发工具调用。

        Args:
            tool_call: 工具调用信息。

        Returns:
            工具执行结果。
        """
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

    def set_post_turn_hook(self, hook: Callable) -> None:
        """设置后轮次钩子。

        Args:
            hook: 钩子函数。
        """
        self._on_post_turn = hook
