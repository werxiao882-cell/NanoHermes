"""OpenAI 兼容客户端封装。

本模块封装了 OpenAI SDK 的调用逻辑，提供：
1. chat_completion: 标准聊天补全调用
2. stream_completion: 流式响应
3. interruptible_call: 可中断的 API 调用
4. token usage 提取
5. 错误分类

设计决策说明：
- 为什么使用同步 SDK 而非 asyncio：OpenAI SDK 的同步版本更稳定，且 TUI 界面
  本身运行在独立线程中，使用 threading.Thread 可以更好地与 UI 线程交互。
  asyncio 需要整个调用链都是 async 的，会增加复杂性和调试难度。
- 为什么提供三种调用模式：
  * chat_completion: 简单场景，一次性获取完整响应
  * stream_completion: 需要实时展示响应给用户（TUI 流式输出）
  * interruptible_completion: 用户可能随时取消操作（如按 Ctrl+C）

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

        生成器语义说明：
        - 使用 Generator[str, None, ChatResponse] 类型注解：
          * 第一个参数 str：yield 出的值类型（增量文本）
          * 第二个参数 None：send() 发送的值类型（本实现不使用 send）
          * 第三个参数 ChatResponse：生成器返回值的类型（最终完整响应）
        - 为什么使用生成器而非回调：
          * 生成器保持调用栈的连续性，错误处理更简单
          * 调用方可以使用 for 循环自然消费流，无需管理回调注册
          * 生成器天然支持背压（backpressure），调用方控制消费节奏
        - yield 语义详解：
          * 每次收到 SDK 的 chunk，提取 delta.content 并 yield 出去
          * 调用方可以在每次 yield 后执行 UI 刷新或其他逻辑
          * 最后一个 yield 是 ChatResponse，包含完整内容和 usage 统计
          * 调用方通过捕获 StopIteration 获取最终返回值（或 for 循环自动处理）

        Args:
            messages: OpenAI 格式的消息列表。
            tools: 工具 schema 列表（可选）。
            **kwargs: 其他传递给 SDK 的参数。

        Yields:
            str: 增量 token 文本（每次 SDK 返回一个 chunk 时 yield）。
            ChatResponse: 最后一个 yield 是完整响应（包含 usage、tool_calls 等）。

        Raises:
            ClassifiedError: 分类后的 API 错误。
        """
        try:
            # 构建请求参数：必须设置 stream=True 启用流式模式
            # 流式模式下，SDK 返回 Server-Sent Events (SSE) 流，逐个 chunk 交付
            request_kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "stream": True,
            }
            if tools:
                request_kwargs["tools"] = tools
            request_kwargs.update(kwargs)

            # 创建流式请求，返回一个可迭代的 stream 对象
            # SDK 内部使用 HTTP chunked transfer encoding 逐步接收响应
            stream = self._client.chat.completions.create(**request_kwargs)

            # 累积变量：用于在流结束后构建完整响应
            full_content = ""      # 拼接所有增量文本
            tool_calls = []        # 收集工具调用信息（可能分散在多个 chunk 中）
            usage = None           # token 使用量（通常在最后一个 chunk 中）
            finish_reason = None   # 结束原因（"stop", "tool_calls", "length" 等）

            # 遍历 stream：SDK 每次收到服务器推送的 chunk 时迭代一次
            # 这是生成器的核心循环，每次 yield 后暂停，等待调用方消费
            for chunk in stream:
                # delta 包含当前 chunk 的增量数据
                # chunk.choices[0].delta 可能为 None（某些边缘情况）
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # 提取增量文本：delta.content 是当前 chunk 的文本片段
                # 可能为空字符串（如工具调用 chunk 不含文本）
                if delta.content:
                    full_content += delta.content
                    # yield 暂停生成器，将增量文本传递给调用方
                    # 调用方可以立即刷新 UI 或处理文本
                    yield delta.content

                # 提取工具调用：tool_calls 可能分片传输
                # 每个 chunk 可能包含一个工具调用的部分信息（index, id, function 等）
                # 需要逐个 append，后续由调用方组装完整调用
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_calls.append(tc.model_dump())

                # 提取结束原因：仅在最后一个 chunk 中设置
                # 表示模型为何停止生成（正常结束、工具调用、长度限制等）
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

                # 提取 usage：SDK 通常在最后一个 chunk 中附带 usage 信息
                # 不是所有提供商都支持流式 usage，需要 hasattr 检查
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = extract_usage(chunk.usage)

            # 流结束后，yield 完整响应作为生成器的最终返回值
            # 调用方可以通过 for 循环的最后一个值获取，或捕获 StopIteration.value
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

        闭包设计理由：
        - 为什么使用闭包而非直接方法：
          * ConversationLoop 期望一个签名 (messages, tools) -> dict 的 callable
          * 闭包捕获 self._model 和 self._client，无需每次传递
          * 保持接口简洁，调用方无需知道客户端内部结构
        - 为什么返回流式调用的结果而非生成器：
          * ConversationLoop 内部可能多次调用模型（如工具调用循环）
          * 返回完整字典更易于序列化和日志记录
          * 流式输出由 TUI 层单独处理，此处只关注结果
        - 为什么在此处重新实现流式逻辑而非复用 stream_completion：
          * stream_completion 是生成器，需要调用方迭代消费
          * build_caller 需要阻塞直到流结束，返回完整结果
          * 两处逻辑相似但用途不同，复用会增加生成器状态管理复杂度

        Returns:
            调用函数: (messages, tools) -> dict，包含 content, tool_calls,
                     usage, reasoning, request_body 字段。
        """
        # 闭包：捕获外部 self，内部函数可以访问 _client 和 _model
        def call_model(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> dict[str, Any]:
            # 构建请求参数：注意 tools 格式需要包装为 {"type": "function", "function": ...}
            # 这是 OpenAI API 的标准格式，与内部工具定义格式不同
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "stream": True,
            }
            if tools:
                kwargs["tools"] = [
                    {"type": "function", "function": t} for t in tools
                ]

            # 累积变量：用于构建完整响应
            full_content = ""
            reasoning = ""         # 模型的思考过程（extended thinking / reasoning_content）
            tool_calls = []
            usage = None

            try:
                # 流式调用：逐个 chunk 接收响应
                # 使用流式而非同步调用的原因：
                # 1. 避免长时间阻塞（同步调用可能等待数十秒）
                # 2. 可以逐步提取 reasoning 和 tool_calls
                # 3. 某些提供商对同步调用有更严格的超时限制
                stream = self._client.chat.completions.create(**kwargs)
                for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta is None:
                        continue

                    # 提取增量文本
                    if delta.content:
                        full_content += delta.content

                    # 提取 reasoning：不同提供商使用不同的字段名
                    # - OpenAI o1/o3 系列使用 'reasoning'
                    # - 某些兼容提供商使用 'reasoning_content'
                    # 使用 hasattr 检查以兼容不同 SDK 版本
                    if hasattr(delta, 'reasoning') and delta.reasoning:
                        reasoning += delta.reasoning
                    elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reasoning += delta.reasoning_content

                    # 提取工具调用：累积所有工具调用信息
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            tool_calls.append(tc.model_dump())

                    # 提取 usage：流式最后一个 chunk 可能包含 usage
                    if hasattr(chunk, 'usage') and chunk.usage:
                        usage = chunk.usage
            except Exception as e:
                raise classify_error(e)

            # 格式化工具调用：SDK 返回的格式与 ConversationLoop 期望的格式不同
            # 需要转换为标准格式：id, type, function.{name, arguments}
            # 这是为了统一不同提供商的响应格式
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

            # 返回统一格式的字典，供 ConversationLoop 使用
            # 包含 request_body 用于调试和日志记录
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

        线程安全考量：
        - 为什么使用 threading.Thread 而非 asyncio：
          * 项目整体使用同步架构（TUI 运行在主线程，SDK 是同步的）
          * asyncio 需要整个调用链改为 async，改造成本高
          * threading.Event 是线程安全的，适合跨线程信号传递
          * OpenAI SDK 的同步版本在独立线程中运行稳定
        - 线程安全机制：
          * result 列表作为线程间通信的共享变量
          * 后台线程只写入一次 result（append 是原子操作）
          * 主线程只读取 result，无并发写入竞争
          * daemon=True 确保主线程退出时后台线程自动终止
        - 为什么不使用线程池：
          * 每次调用都是独立的，无需复用线程
          * 线程池会增加复杂度（任务提交、结果获取、异常传播）
          * 直接创建线程更直观，便于控制生命周期

        可中断机制详解：
        1. 创建后台线程执行 API 调用（_run_completion_in_thread）
        2. 主线程通过 join(timeout) 等待后台线程完成
        3. 检查 interrupt_event：如果用户触发取消（如 Ctrl+C），立即抛出 InterruptedError
        4. 检查超时：如果超过 timeout 秒未完成，抛出 TimeoutError
        5. 检查结果：后台线程将结果写入 result 列表，主线程读取并返回

        注意：interrupt_event 和 timeout 是独立的检查条件
        - interrupt_event 优先于 timeout（即使未超时，用户取消也立即返回）
        - timeout 作为兜底保护，防止 API 调用永久挂起

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
        # result 列表作为线程间通信的共享变量
        # 使用列表而非单个变量是因为列表的 append 是线程安全的原子操作
        # 后台线程写入 result[0]，主线程读取 result[0]，无竞争条件
        result: list[ChatResponse | Exception] = []

        # 创建后台线程执行 API 调用
        # daemon=True：主线程退出时，后台线程自动终止，不会阻塞程序退出
        # 这对于用户取消操作或程序异常退出很重要
        api_thread = threading.Thread(
            target=self._run_completion_in_thread,
            args=(messages, tools, result, kwargs),
            daemon=True,
        )
        api_thread.start()

        # 等待后台线程完成、中断或超时
        # join(timeout) 会阻塞主线程，直到：
        # 1. 后台线程完成（join 返回）
        # 2. 超时（join 返回，但线程可能仍在运行）
        # 注意：join 返回后需要检查线程状态判断是哪种情况
        api_thread.join(timeout=timeout)

        # 检查中断：用户主动取消优先于其他条件
        # interrupt_event.is_set() 是线程安全的，可以在任何线程调用
        if interrupt_event and interrupt_event.is_set():
            raise InterruptedError("API 调用被用户中断")

        # 检查超时：如果线程仍在运行，说明超过了 timeout
        # 注意：后台线程不会被强制终止（daemon 线程只是不阻塞退出）
        # 实际的网络请求可能仍在进行，但主线程不再等待结果
        if api_thread.is_alive():
            raise TimeoutError(f"API 调用超时（{timeout}秒）")

        # 检查结果：后台线程应该已经将结果写入 result 列表
        # 如果 result 为空，说明线程异常退出或未执行完成
        if not result:
            raise ClassifiedError(
                category=ErrorCategory.UNKNOWN,
                message="API 调用未返回结果",
            )

        # 读取结果：可能是成功响应或异常
        # 后台线程捕获所有异常并写入 result，主线程统一处理
        outcome = result[0]
        if isinstance(outcome, Exception):
            # 将后台线程的异常转换为分类错误
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

        线程安全说明：
        - 此方法在后台线程中运行，与主线程并发执行
        - result 列表是唯一的共享变量，只使用 append 操作（线程安全）
        - 捕获所有异常并写入 result，避免后台线程未处理异常导致程序崩溃
        - 不直接抛出异常到主线程，而是通过 result 传递，由主线程统一处理

        为什么在此处捕获异常而非让调用方处理：
        - 后台线程的异常不会自动传播到主线程
        - 如果不在这里捕获，异常会导致线程静默终止，主线程无法感知
        - 将异常写入 result 列表，主线程可以通过检查 result 类型来处理

        Args:
            messages: 消息列表。
            tools: 工具 schema。
            result: 输出列表（写入响应或异常）。
            kwargs: 其他参数。
        """
        try:
            # 调用同步版本的 chat_completion，阻塞直到完成或抛出异常
            response = self.chat_completion(messages, tools, **kwargs)
            # 将成功结果写入共享列表（append 是原子操作，线程安全）
            result.append(response)
        except Exception as e:
            # 将异常写入共享列表，主线程会检查并重新抛出
            # 注意：这里捕获的是所有异常，包括网络错误、超时、分类错误等
            result.append(e)

    def _parse_response(self, response: ChatCompletion) -> ChatResponse:
        """解析 OpenAI SDK 响应为 ChatResponse。

        解析逻辑说明：
        - SDK 返回的 ChatCompletion 对象结构复杂，包含多层嵌套
        - 需要提取：content、tool_calls、usage、finish_reason、reasoning
        - 不同提供商可能返回不同的字段（如 reasoning 是扩展字段）
        - 使用 hasattr 检查可选字段，兼容不同 SDK 版本和提供商

        Args:
            response: OpenAI SDK 的 ChatCompletion 对象。

        Returns:
            解析后的 ChatResponse。
        """
        # 提取第一个 choice（通常只有一个，除非使用多输出模型）
        # response.choices 可能为空（边缘情况），需要防御性检查
        choice = response.choices[0] if response.choices else None
        if not choice:
            # 没有 choice 时返回空响应，但仍保留 usage 信息
            return ChatResponse(
                content=None,
                usage=extract_usage(response.usage),
                finish_reason=None,
            )

        message = choice.message
        content = message.content
        tool_calls = None
        reasoning = None

        # 提取工具调用：model_dump() 将 Pydantic 模型转换为字典
        # 便于后续序列化和日志记录
        if message.tool_calls:
            tool_calls = [tc.model_dump() for tc in message.tool_calls]

        # 提取 reasoning：扩展思考功能，不是所有模型都支持
        # 使用 hasattr 检查，避免在不支持的模型上抛出 AttributeError
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

    提取逻辑说明：
    - SDK 返回的 usage 对象字段名与内部 TokenUsage 不一致：
      * prompt_tokens → input_tokens
      * completion_tokens → output_tokens
    - 缓存 token 是嵌套字段（prompt_tokens_details.cached_tokens）
      需要逐层检查，避免 AttributeError
    - 使用 getattr 提供默认值，兼容不同提供商的响应格式
    - cache_write_tokens 无法直接从 SDK 获取，设为 0（OpenAI 不暴露此信息）

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
        # 缓存读取 token：嵌套在 prompt_tokens_details.cached_tokens 中
        # 需要逐层检查：先检查 prompt_tokens_details 是否存在，再检查 cached_tokens
        cache_read_tokens=getattr(usage, 'prompt_tokens_details', None).cached_tokens
            if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details
            else 0,
        # 缓存写入 token：OpenAI API 不直接暴露此信息，暂时设为 0
        # 某些提供商可能在扩展字段中提供，但标准 OpenAI 响应不包含
        cache_write_tokens=0,
    )


def classify_error(error: Exception) -> ClassifiedError:
    """将 API 错误分类为 ErrorCategory。

    分类逻辑设计：
    1. 优先检查异常类型（APIConnectionError vs APIError）
    2. 对于 APIError，检查 HTTP 状态码（最可靠的分类依据）
    3. 状态码不可用时，回退到错误消息关键词匹配
    4. 默认分类为 UNKNOWN，确保所有错误都被捕获

    为什么使用状态码而非消息关键词作为主要分类依据：
    - HTTP 状态码是标准化的，不同提供商一致
    - 错误消息可能因语言、版本、提供商而异
    - 状态码更可靠，不易受消息格式变化影响

    重试策略说明：
    - retryable=True 的错误：rate_limit, server_error, network_error
      这些通常是临时性问题，等待后重试可能成功
    - retryable=False 的错误：auth, billing, context_overflow
      这些需要用户干预或修改请求，重试无意义

    Args:
        error: 捕获到的异常。

    Returns:
        分类后的 ClassifiedError。
    """
    # 网络连接错误：优先级最高，因为 APIConnectionError 是独立类型
    # 不包含 HTTP 状态码，直接分类为 NETWORK_ERROR
    # retryable=True：网络抖动通常是暂时的，重试可能成功
    if isinstance(error, APIConnectionError):
        return ClassifiedError(
            category=ErrorCategory.NETWORK_ERROR,
            message=f"网络连接错误: {error}",
            retryable=True,
            original=error,
        )

    # API 错误：包含 HTTP 状态码和响应体信息
    if isinstance(error, APIError):
        # 提取状态码：新版 SDK 可能没有 status_code 属性
        # 需要从 body 中获取，兼容不同 SDK 版本
        status_code = getattr(error, 'status_code', None)
        # 回退方案：从 body 字典中获取状态码
        # 某些提供商将状态码放在 body['status_code'] 或 body['code']
        if status_code is None and isinstance(getattr(error, 'body', None), dict):
            status_code = error.body.get('status_code') or error.body.get('code')
        message = str(error)
        msg_lower = message.lower()

        # 401/403：认证/授权错误
        # retryable=False：凭证问题不会自行恢复，需要用户刷新凭证
        if status_code == 401 or status_code == 403:
            return ClassifiedError(
                category=ErrorCategory.AUTH,
                message=f"认证错误 (HTTP {status_code}): {message}",
                retryable=False,
                original=error,
            )
        # 402：计费错误（账户余额不足、未订阅等）
        # retryable=False：需要用户充值或升级账户
        if status_code == 402:
            return ClassifiedError(
                category=ErrorCategory.BILLING,
                message=f"计费错误 (HTTP {status_code}): {message}",
                retryable=False,
                original=error,
            )
        # 429：速率限制（请求过于频繁）
        # retryable=True：等待一段时间后重试可能成功
        # 回退链可以利用此分类切换到其他提供商
        if status_code == 429:
            return ClassifiedError(
                category=ErrorCategory.RATE_LIMIT,
                message=f"速率限制 (HTTP {status_code}): {message}",
                retryable=True,
                original=error,
            )
        # 400 + 上下文溢出关键词：输入超过模型上下文窗口
        # retryable=False：需要压缩上下文或减少输入，重试无意义
        # 使用关键词匹配因为某些提供商返回 400 而非特定状态码
        if status_code == 400 and ("context" in msg_lower and ("length" in msg_lower or "overflow" in msg_lower or "exceed" in msg_lower or "maximum" in msg_lower)):
            return ClassifiedError(
                category=ErrorCategory.CONTEXT_OVERFLOW,
                message=f"上下文溢出: {message}",
                retryable=False,
                original=error,
            )
        # 5xx：服务器错误（500, 502, 503, 504 等）
        # retryable=True：服务器临时故障，等待后重试可能成功
        if status_code and status_code >= 500:
            return ClassifiedError(
                category=ErrorCategory.SERVER_ERROR,
                message=f"服务器错误 (HTTP {status_code}): {message}",
                retryable=True,
                original=error,
            )

    # 默认分类：未知错误
    # 包含所有未匹配上述条件的异常（如 ValueError、TypeError 等）
    # retryable=False：未知错误重试可能无意义，需要记录日志并上报
    return ClassifiedError(
        category=ErrorCategory.UNKNOWN,
        message=f"未知错误: {type(error).__name__}: {error}",
        retryable=False,
        original=error,
    )
