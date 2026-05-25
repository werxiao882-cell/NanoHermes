"""ConversationLoop - 核心对话循环。

循环流程：
1. 组装系统提示
2. 调用模型
3. 处理工具调用
4. 错误分类和重试
5. 后轮次钩子
6. 压缩触发检查
"""

from __future__ import annotations

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
    """

    def __init__(
        self,
        max_iterations: int = 90,
        model_call: Callable | None = None,
        tool_dispatch: Callable | None = None,
    ):
        """初始化对话循环。

        Args:
            max_iterations: 最大迭代次数。
            model_call: 模型调用函数。
            tool_dispatch: 工具分发函数。
        """
        self.max_iterations = max_iterations
        self._model_call = model_call
        self._tool_dispatch = tool_dispatch
        self._error_classifier = ErrorClassifier()
        self._on_post_turn: Callable | None = None
        self._interrupted = False

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

            # 检查是否有工具调用
            if response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    result = self._dispatch_tool(tool_call)
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
