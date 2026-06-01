"""Debug 事件处理器。

订阅 ConversationLoop 的事件，输出调试日志。
仅在 debug=True 时注册，与核心循环完全解耦。
"""

from __future__ import annotations

import json
from typing import Any


class DebugHandler:
    """调试输出处理器，订阅事件总线输出详细日志。"""

    def on_model_request(self, data: dict[str, Any]) -> None:
        """输出发送到模型的完整请求体。"""
        iteration = data["iteration"]
        messages = data["messages"]
        tools = data.get("tools")

        request_body = {"messages": messages}
        if tools:
            request_body["tools"] = tools

        print(f"\n{'='*70}")
        print(f"[DEBUG] >>> 第 {iteration} 轮 - 请求体 (Request Body)")
        print(f"{'='*70}")
        print(json.dumps(request_body, ensure_ascii=False, indent=2))
        print(f"{'='*70}\n")

    def on_model_response(self, data: dict[str, Any]) -> None:
        """输出模型返回的完整响应体和思考内容。"""
        iteration = data["iteration"]
        response = data["response"]
        elapsed = data.get("elapsed", 0)

        # 输出 reasoning
        reasoning = response.get("reasoning")
        if reasoning:
            print(f"\n{'='*70}")
            print(f"[DEBUG] 第 {iteration} 轮 - 思考内容 (Reasoning)")
            print(f"{'='*70}")
            print(reasoning)
            print(f"{'='*70}\n")

        # 输出完整响应体
        raw_response = response.get("raw_response")
        if raw_response:
            print(f"\n{'='*70}")
            print(f"[DEBUG] <<< 第 {iteration} 轮 - 响应体 (Response Body) [{elapsed:.2f}s]")
            print(f"{'='*70}")
            if isinstance(raw_response, dict):
                print(json.dumps(raw_response, ensure_ascii=False, indent=2))
            else:
                print(raw_response)
            print(f"{'='*70}\n")
        else:
            print(f"\n{'='*70}")
            print(f"[DEBUG] <<< 第 {iteration} 轮 - 响应摘要 [{elapsed:.2f}s]")
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

    def on_model_error(self, data: dict[str, Any]) -> None:
        """输出模型调用错误。"""
        iteration = data["iteration"]
        error = data["error"]
        classified = data.get("classified")

        print(f"\n{'='*70}")
        print(f"[DEBUG] !!! 第 {iteration} 轮 - 模型调用失败")
        print(f"{'='*70}")
        print(f"错误: {type(error).__name__}: {error}")
        if classified:
            print(f"分类: {classified.reason.value}, 可重试: {classified.retryable}")
        print(f"{'='*70}\n")

    def on_tool_end(self, data: dict[str, Any]) -> None:
        """输出工具执行结果。"""
        tool_name = data["tool_name"]
        result = data["result"]
        elapsed = data.get("elapsed", 0)

        display_result = result
        if len(display_result) > 300:
            display_result = display_result[:300] + "..."

        print(f"[DEBUG] 工具执行: {tool_name} [{elapsed:.2f}s]")
        print(f"  结果: {display_result}")
        print()

    def on_tool_error(self, data: dict[str, Any]) -> None:
        """输出工具执行错误。"""
        tool_name = data["tool_name"]
        error = data["error"]
        elapsed = data.get("elapsed", 0)

        print(f"[DEBUG] 工具失败: {tool_name} [{elapsed:.2f}s]")
        print(f"  错误: {type(error).__name__}: {error}")
        print()

    def register(self, events) -> None:
        """将所有调试处理器注册到事件总线。"""
        from src.conversation.events import EventType

        events.on(EventType.MODEL_REQUEST, self.on_model_request)
        events.on(EventType.MODEL_RESPONSE, self.on_model_response)
        events.on(EventType.MODEL_ERROR, self.on_model_error)
        events.on(EventType.TOOL_END, self.on_tool_end)
        events.on(EventType.TOOL_ERROR, self.on_tool_error)
