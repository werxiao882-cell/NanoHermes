"""OpenAI 兼容客户端封装。

本模块封装了 OpenAI SDK 的调用逻辑，提供：
1. chat_completion: 标准聊天补全调用
2. stream_completion: 流式响应
3. interruptible_call: 可中断的 API 调用
4. token usage 提取
5. 错误分类

错误分类学：
- auth: 401/403 认证/授权错误
- billing: 402 付费/额度不足
- rate_limit: 429 速率限制
- context_overflow: 上下文溢出（token 超出窗口）
- server_error: 5xx 服务器错误
- network_error: 网络连接错误
- format_error: 响应格式错误
- unknown: 未知错误
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generator

from openai import OpenAI, APIError, APIConnectionError
from openai.types.chat import ChatCompletion, ChatCompletionChunk


class ErrorCategory(Enum):
    """API 错误分类。

    每个分类对应不同的恢复策略：
    - AUTH: 需要刷新凭证或切换提供商
    - BILLING: 需要检查账户余额或切换模型
    - RATE_LIMIT: 需要等待重试或切换提供商
    - CONTEXT_OVERFLOW: 需要触发上下文压缩
    - SERVER_ERROR: 需要等待重试或切换提供商
    - NETWORK_ERROR: 需要重试
    - FORMAT_ERROR: 需要检查请求格式
    - UNKNOWN: 需要记录日志并上报
    """
    AUTH = "auth"
    BILLING = "billing"
    RATE_LIMIT = "rate_limit"
    CONTEXT_OVERFLOW = "context_overflow"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    FORMAT_ERROR = "format_error"
    UNKNOWN = "unknown"


@dataclass
class TokenUsage:
    """Token 使用量统计。

    Attributes:
        input_tokens: 输入 token 数量（prompt，不含缓存）。
        output_tokens: 输出 token 数量（completion）。
        cache_read_tokens: 缓存读取 token 数量（命中提示缓存）。
        cache_write_tokens: 缓存写入 token 数量（首次写入缓存）。
        total_tokens: 总 token 数量（input + output）。
    """
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """总 token 数量（input + output）。"""
        return self.input_tokens + self.output_tokens


@dataclass
class ClassifiedError:
    """分类后的 API 错误。

    Attributes:
        category: 错误分类。
        message: 错误描述信息。
        retryable: 是否建议重试（rate_limit 和 server_error 通常可重试）。
        original: 原始异常对象（如果有）。
    """
    category: ErrorCategory
    message: str
    retryable: bool = False
    original: Exception | None = None


@dataclass
class ChatResponse:
    """聊天响应封装。

    Attributes:
        content: 模型返回的文本内容。
        tool_calls: 模型返回的工具调用列表（如果有）。
        usage: Token 使用量统计。
        finish_reason: 结束原因（"stop", "tool_calls", "length", "content_filter"）。
        reasoning: 模型的推理内容（如果模型支持 extended thinking）。
    """
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    usage: TokenUsage | None = None
    finish_reason: str | None = None
    reasoning: str | None = None


class OpenAIClient:
    """OpenAI 兼容客户端封装。

    封装 OpenAI SDK 的调用逻辑，提供统一的接口和错误处理。

    Attributes:
        _client: 底层 OpenAI SDK 客户端实例。
        _model: 当前使用的模型名称。
    """

    def __init__(self, client: OpenAI, model: str):
        """初始化 OpenAI 客户端。

        Args:
            client: 已初始化的 OpenAI SDK 客户端实例。
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
        """执行一次聊天补全调用。

        Args:
            messages: OpenAI 格式的消息列表。
            tools: 工具 schema 列表（可选）。
            temperature: 温度参数（可选）。
            max_tokens: 最大输出 token 数（可选）。
            **kwargs: 其他传递给 SDK 的参数。

        Returns:
            ChatResponse 封装的响应。

        Raises:
            ClassifiedError: 分类后的 API 错误。
        """
        try:
            request_kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
            }
            if tools:
                request_kwargs["tools"] = tools
            if temperature is not None:
                request_kwargs["temperature"] = temperature
            if max_tokens is not None:
                request_kwargs["max_tokens"] = max_tokens
            request_kwargs.update(kwargs)

            response = self._client.chat.completions.create(**request_kwargs)
            return self._parse_response(response)

        except Exception as e:
            raise classify_error(e)

    def stream_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Generator[str, None, ChatResponse]:
        """执行流式聊天补全调用。

        生成器逐个 yield 增量 token，最后 yield 完整的 ChatResponse。

        Args:
            messages: OpenAI 格式的消息列表。
            tools: 工具 schema 列表（可选）。
            **kwargs: 其他传递给 SDK 的参数。

        Yields:
            str: 增量 token 文本。
            ChatResponse: 最后一个 yield 是完整响应（包含 usage）。

        Raises:
            ClassifiedError: 分类后的 API 错误。
        """
        try:
            request_kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "stream": True,
            }
            if tools:
                request_kwargs["tools"] = tools
            request_kwargs.update(kwargs)

            stream = self._client.chat.completions.create(**request_kwargs)

            full_content = ""
            tool_calls = []
            usage = None
            finish_reason = None

            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # 提取增量文本
                if delta.content:
                    full_content += delta.content
                    yield delta.content

                # 提取工具调用
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_calls.append(tc.model_dump())

                # 提取结束原因
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

                # 提取 usage（通常在最后一个 chunk）
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = extract_usage(chunk.usage)

            # 最后 yield 完整响应
            yield ChatResponse(
                content=full_content,
                tool_calls=tool_calls if tool_calls else None,
                usage=usage,
                finish_reason=finish_reason,
            )

        except Exception as e:
            raise classify_error(e)

    def build_caller(self):
        """构建适配 ConversationLoop 接口的模型调用函数。

        使用流式调用，返回包含 content, tool_calls, usage, reasoning, request_body 的字典。

        Returns:
            调用函数: (messages, tools) -> dict
        """
        def call_model(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> dict[str, Any]:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "stream": True,
            }
            if tools:
                kwargs["tools"] = [
                    {"type": "function", "function": t} for t in tools
                ]

            full_content = ""
            reasoning = ""
            tool_calls = []
            usage = None

            stream = self._client.chat.completions.create(**kwargs)
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                if delta.content:
                    full_content += delta.content

                if hasattr(delta, 'reasoning') and delta.reasoning:
                    reasoning += delta.reasoning
                elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning += delta.reasoning_content

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_calls.append(tc.model_dump())

                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = chunk.usage

            formatted_tool_calls = None
            if tool_calls:
                formatted_tool_calls = [
                    {
                        "id": tc.get("id", ""),
                        "type": tc.get("type", "function"),
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", ""),
                        },
                    }
                    for tc in tool_calls
                ]

            return {
                "content": full_content,
                "tool_calls": formatted_tool_calls,
                "reasoning": reasoning if reasoning else None,
                "usage": {
                    "input_tokens": usage.prompt_tokens if usage else 0,
                    "output_tokens": usage.completion_tokens if usage else 0,
                },
                "request_body": kwargs,
            }

        return call_model

    def interruptible_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        interrupt_event: threading.Event | None = None,
        timeout: float = 300.0,
        **kwargs: Any,
    ) -> ChatResponse:
        """执行可中断的聊天补全调用。

        在后台线程中执行 API 调用，主线程监控中断事件。

        Args:
            messages: OpenAI 格式的消息列表。
            tools: 工具 schema 列表（可选）。
            interrupt_event: 中断事件对象。设置时取消调用。
            timeout: 超时时间（秒），默认 300 秒。
            **kwargs: 其他传递给 SDK 的参数。

        Returns:
            ChatResponse 封装的响应。

        Raises:
            ClassifiedError: 分类后的 API 错误。
            TimeoutError: 调用超时。
            InterruptedError: 调用被中断。
        """
        result: list[ChatResponse | Exception] = []
        api_thread = threading.Thread(
            target=self._run_completion_in_thread,
            args=(messages, tools, result, kwargs),
            daemon=True,
        )
        api_thread.start()

        # 等待完成、中断或超时
        api_thread.join(timeout=timeout)

        if interrupt_event and interrupt_event.is_set():
            raise InterruptedError("API 调用被用户中断")

        if api_thread.is_alive():
            raise TimeoutError(f"API 调用超时（{timeout}秒）")

        if not result:
            raise ClassifiedError(
                category=ErrorCategory.UNKNOWN,
                message="API 调用未返回结果",
            )

        outcome = result[0]
        if isinstance(outcome, Exception):
            raise classify_error(outcome)
        return outcome

    def _run_completion_in_thread(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        result: list[ChatResponse | Exception],
        kwargs: dict[str, Any],
    ) -> None:
        """在后台线程中执行 API 调用。

        Args:
            messages: 消息列表。
            tools: 工具 schema。
            result: 输出列表（写入响应或异常）。
            kwargs: 其他参数。
        """
        try:
            response = self.chat_completion(messages, tools, **kwargs)
            result.append(response)
        except Exception as e:
            result.append(e)

    def _parse_response(self, response: ChatCompletion) -> ChatResponse:
        """解析 OpenAI SDK 响应为 ChatResponse。

        Args:
            response: OpenAI SDK 的 ChatCompletion 对象。

        Returns:
            解析后的 ChatResponse。
        """
        choice = response.choices[0] if response.choices else None
        if not choice:
            return ChatResponse(
                content=None,
                usage=extract_usage(response.usage),
                finish_reason=None,
            )

        message = choice.message
        content = message.content
        tool_calls = None
        reasoning = None

        # 提取工具调用
        if message.tool_calls:
            tool_calls = [tc.model_dump() for tc in message.tool_calls]

        # 提取 reasoning（如果模型支持 extended thinking）
        if hasattr(message, 'reasoning') and message.reasoning:
            reasoning = message.reasoning

        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            usage=extract_usage(response.usage),
            finish_reason=choice.finish_reason,
            reasoning=reasoning,
        )


def extract_usage(usage: Any | None) -> TokenUsage:
    """从 SDK 响应中提取 token 使用量。

    Args:
        usage: SDK 响应的 usage 对象（可能为 None）。

    Returns:
        TokenUsage 实例。
    """
    if not usage:
        return TokenUsage()

    return TokenUsage(
        input_tokens=getattr(usage, 'prompt_tokens', 0),
        output_tokens=getattr(usage, 'completion_tokens', 0),
        cache_read_tokens=getattr(usage, 'prompt_tokens_details', None).cached_tokens
            if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details
            else 0,
        cache_write_tokens=0,  # OpenAI 不直接暴露缓存写入 token
    )


def classify_error(error: Exception) -> ClassifiedError:
    """将 API 错误分类为 ErrorCategory。

    分类逻辑：
    1. 检查 HTTP 状态码（401 → auth, 429 → rate_limit, 500 → server_error）
    2. 检查错误消息关键词
    3. 默认为 unknown

    Args:
        error: 捕获到的异常。

    Returns:
        分类后的 ClassifiedError。
    """
    # 网络连接错误
    if isinstance(error, APIConnectionError):
        return ClassifiedError(
            category=ErrorCategory.NETWORK_ERROR,
            message=f"网络连接错误: {error}",
            retryable=True,
            original=error,
        )

    # API 错误（有 HTTP 状态码）
    if isinstance(error, APIError):
        # 新版 SDK 可能没有 status_code 属性
        status_code = getattr(error, 'status_code', None)
        # 尝试从 body 中获取状态码
        if status_code is None and isinstance(getattr(error, 'body', None), dict):
            status_code = error.body.get('status_code') or error.body.get('code')
        message = str(error)
        msg_lower = message.lower()

        if status_code == 401 or status_code == 403:
            return ClassifiedError(
                category=ErrorCategory.AUTH,
                message=f"认证错误 (HTTP {status_code}): {message}",
                retryable=False,
                original=error,
            )
        if status_code == 402:
            return ClassifiedError(
                category=ErrorCategory.BILLING,
                message=f"计费错误 (HTTP {status_code}): {message}",
                retryable=False,
                original=error,
            )
        if status_code == 429:
            return ClassifiedError(
                category=ErrorCategory.RATE_LIMIT,
                message=f"速率限制 (HTTP {status_code}): {message}",
                retryable=True,
                original=error,
            )
        if status_code == 400 and ("context" in msg_lower and ("length" in msg_lower or "overflow" in msg_lower or "exceed" in msg_lower or "maximum" in msg_lower)):
            return ClassifiedError(
                category=ErrorCategory.CONTEXT_OVERFLOW,
                message=f"上下文溢出: {message}",
                retryable=False,
                original=error,
            )
        if status_code and status_code >= 500:
            return ClassifiedError(
                category=ErrorCategory.SERVER_ERROR,
                message=f"服务器错误 (HTTP {status_code}): {message}",
                retryable=True,
                original=error,
            )

    # 默认未知错误
    return ClassifiedError(
        category=ErrorCategory.UNKNOWN,
        message=f"未知错误: {type(error).__name__}: {error}",
        retryable=False,
        original=error,
    )
