"""Anthropic Messages API 适配器。

本模块负责将 OpenAI 格式的消息和工具 schema 转换为 Anthropic 格式，
并将 Anthropic 响应转换回 OpenAI 格式。

格式差异：
1. System message:
   - OpenAI: messages 列表中的 {"role": "system", "content": "..."}
   - Anthropic: 独立的 system 参数

2. 工具调用格式:
   - OpenAI: tool_calls 数组，每个包含 function.name 和 function.arguments
   - Anthropic: content 数组中的 {"type": "tool_use", "id", "name", "input"}

3. 工具结果格式:
   - OpenAI: {"role": "tool", "tool_call_id": "...", "content": "..."}
   - Anthropic: content 数组中的 {"type": "tool_result", "tool_use_id", "content"}

4. 响应格式:
   - OpenAI: choices[0].message.content + tool_calls
   - Anthropic: content 数组（text / tool_use / tool_result）
"""

from __future__ import annotations

from typing import Any

from anthropic import Anthropic

from src.provider.openai_client import ChatResponse, TokenUsage, classify_error


class AnthropicAdapter:
    """Anthropic Messages API 适配器。

    负责 OpenAI ↔ Anthropic 格式的双向转换。

    Attributes:
        _client: Anthropic SDK 客户端实例。
        _model: 当前使用的模型名称。
    """

    def __init__(self, client: Anthropic, model: str):
        """初始化 Anthropic 适配器。

        Args:
            client: 已初始化的 Anthropic SDK 客户端实例。
            model: 要使用的模型名称。
        """
        self._client = client
        self._model = model

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """执行 Anthropic 聊天补全调用。

        内部流程：
        1. 将 OpenAI 格式消息转换为 Anthropic 格式
        2. 将工具 schema 转换为 Anthropic 格式
        3. 调用 Anthropic API
        4. 将响应转换回 OpenAI 格式

        Args:
            messages: OpenAI 格式的消息列表。
            tools: OpenAI 格式的工具 schema 列表。
            temperature: 温度参数（可选）。
            max_tokens: 最大输出 token 数（可选）。
            **kwargs: 其他传递给 SDK 的参数。

        Returns:
            ChatResponse 封装的响应（OpenAI 格式）。

        Raises:
            ClassifiedError: 分类后的 API 错误。
        """
        try:
            # 步骤 1: 转换消息格式
            system_prompt, anthropic_messages = self._convert_messages(messages)

            # 步骤 2: 转换工具 schema
            anthropic_tools = None
            if tools:
                anthropic_tools = self._convert_tools(tools)

            # 步骤 3: 构建请求参数
            request_kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens or 4096,  # Anthropic 要求必须指定
            }
            if system_prompt:
                request_kwargs["system"] = system_prompt
            if anthropic_tools:
                request_kwargs["tools"] = anthropic_tools
            if temperature is not None:
                request_kwargs["temperature"] = temperature
            request_kwargs.update(kwargs)

            # 步骤 4: 调用 API
            response = self._client.messages.create(**request_kwargs)

            # 步骤 5: 转换响应格式
            return self._convert_response(response)

        except Exception as e:
            raise classify_error(e)

    def _convert_messages(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """将 OpenAI 格式消息转换为 Anthropic 格式。

        处理逻辑：
        1. 提取 system message 作为独立的 system 参数
        2. 转换 tool 角色消息为 tool_result 格式
        3. 转换 assistant 消息的 tool_calls 为 tool_use 格式

        Args:
            messages: OpenAI 格式的消息列表。

        Returns:
            (system_prompt, anthropic_messages) 元组。
        """
        system_prompt = None
        converted = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                # system message 提取为独立参数
                system_prompt = content if isinstance(content, str) else str(content)
                continue

            if role == "tool":
                # tool 结果转换为 tool_result 格式
                converted.append({
                    "role": "user",  # Anthropic 中 tool_result 属于 user 消息
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": str(content),
                    }],
                })
                continue

            if role == "assistant":
                # assistant 消息可能包含 tool_calls
                content_blocks = []
                if content:
                    content_blocks.append({
                        "type": "text",
                        "text": str(content),
                    })

                # 转换 tool_calls
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            func = tc.get("function", {})
                            content_blocks.append({
                                "type": "tool_use",
                                "id": tc.get("id", ""),
                                "name": func.get("name", ""),
                                "input": self._safe_parse_json(func.get("arguments", "{}")),
                            })

                converted.append({
                    "role": "assistant",
                    "content": content_blocks,
                })
                continue

            # user 消息直接传递
            converted.append({
                "role": "user",
                "content": str(content) if content else "",
            })

        return system_prompt, converted

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """将 OpenAI 格式的工具 schema 转换为 Anthropic 格式。

        OpenAI 格式:
            {"name": "tool_name", "description": "...", "parameters": {...}}

        Anthropic 格式:
            {"name": "tool_name", "description": "...", "input_schema": {...}}

        Args:
            tools: OpenAI 格式的工具 schema 列表。

        Returns:
            Anthropic 格式的工具 schema 列表。
        """
        converted = []
        for tool in tools:
            # OpenAI 的 tool schema 可能在 function 字段下
            func = tool.get("function", tool)
            converted.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
            })
        return converted

    def _convert_response(self, response) -> ChatResponse:
        """将 Anthropic 响应转换为 OpenAI 格式。

        处理逻辑：
        1. 提取文本内容（text 类型的 content block）
        2. 提取工具调用（tool_use 类型的 content block）
        3. 提取 token 使用量
        4. 提取结束原因

        Args:
            response: Anthropic SDK 的 Message 响应。

        Returns:
            OpenAI 格式的 ChatResponse。
        """
        content = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": self._safe_to_json(block.input),
                    },
                })

        # 提取 token 使用量
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0,
        )

        return ChatResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage,
            finish_reason=response.stop_reason,
        )

    @staticmethod
    def _safe_parse_json(text: str) -> dict[str, Any]:
        """安全地解析 JSON 字符串。

        Args:
            text: JSON 字符串。

        Returns:
            解析后的字典，解析失败返回空字典。
        """
        import json
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _safe_to_json(obj: Any) -> str:
        """安全地将对象转换为 JSON 字符串。

        Args:
            obj: 要转换的对象。

        Returns:
            JSON 字符串，转换失败返回 "{}"。
        """
        import json
        try:
            return json.dumps(obj)
        except (TypeError, ValueError):
            return "{}"
