"""API 模式定义和路由逻辑。

API Mode 决定了：
1. 使用哪个 SDK 客户端（OpenAI / Anthropic）
2. 请求消息的格式（OpenAI 格式 / Anthropic 格式）
3. 工具调用的 schema 结构
4. 响应解析方式

支持的 API Mode：
- chat_completions: OpenAI 兼容端点（标准格式，大多数提供商使用此模式）
- anthropic_messages: 原生 Anthropic Messages API（需要格式转换）
- codex_responses: OpenAI Responses API（Codex 专用）

路由优先级：
1. 显式传入的 api_mode（最高优先级）
2. 提供商配置文件中的 api_mode
3. 基于 base_url 的启发式检测
4. 默认值 chat_completions
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.provider.profile import ProviderProfile


class ApiMode(Enum):
    """API 执行模式枚举。

    每个模式对应不同的请求格式、客户端类型和响应解析逻辑。

    成员:
        CHAT_COMPLETIONS: OpenAI 兼容的 Chat Completions API。
            - 客户端: openai.OpenAI
            - 消息格式: OpenAI 标准格式 (role/content/tool_calls)
            - 适用: OpenAI, OpenRouter, 自定义端点等

        ANTHROPIC_MESSAGES: 原生 Anthropic Messages API。
            - 客户端: anthropic.Anthropic
            - 消息格式: 需要转换（system 作为独立参数，tool 格式不同）
            - 适用: Anthropic (Claude)

        CODEX_RESPONSES: OpenAI Responses API（Codex 专用）。
            - 客户端: openai.OpenAI（但使用不同的端点）
            - 消息格式: Responses API 格式（input items）
            - 适用: OpenAI Codex
    """
    CHAT_COMPLETIONS = "chat_completions"
    ANTHROPIC_MESSAGES = "anthropic_messages"
    CODEX_RESPONSES = "codex_responses"


# base_url 启发式检测映射
# 当 api_mode 未显式指定时，根据 base_url 自动推断
_URL_HEURISTICS: list[tuple[str, ApiMode]] = [
    ("api.anthropic.com", ApiMode.ANTHROPIC_MESSAGES),
    ("codex", ApiMode.CODEX_RESPONSES),
]


def resolve_api_mode(
    explicit_mode: str | None = None,
    profile: "ProviderProfile | None" = None,
    base_url: str | None = None,
) -> ApiMode:
    """按优先级解析 API Mode。

    解析顺序：
    1. explicit_mode: 显式传入的 api_mode 字符串（最高优先级）
    2. profile.api_mode: 提供商配置文件中的模式
    3. base_url 启发式: 根据 URL 推断（如 api.anthropic.com → anthropic_messages）
    4. 默认值: chat_completions

    Args:
        explicit_mode: 显式指定的 api_mode 字符串。
        profile: 提供商配置文件，用于获取默认 api_mode。
        base_url: 基础 URL，用于启发式检测。

    Returns:
        解析后的 ApiMode 枚举值。

    Raises:
        ValueError: 如果 explicit_mode 不是有效的 api_mode 值。

    Examples:
        >>> resolve_api_mode("anthropic_messages")
        ApiMode.ANTHROPIC_MESSAGES

        >>> resolve_api_mode(base_url="https://api.anthropic.com")
        ApiMode.ANTHROPIC_MESSAGES

        >>> resolve_api_mode()  # 无任何提示
        ApiMode.CHAT_COMPLETIONS
    """
    # 最高优先级：显式指定的模式
    if explicit_mode:
        try:
            return ApiMode(explicit_mode)
        except ValueError:
            valid = [m.value for m in ApiMode]
            raise ValueError(
                f"不支持的 api_mode: '{explicit_mode}'。"
                f"支持的值: {', '.join(valid)}"
            )

    # 第二优先级：提供商配置文件中的模式
    if profile and profile.api_mode:
        try:
            return ApiMode(profile.api_mode)
        except ValueError:
            pass  # 配置文件中的值无效，继续下一级

    # 第三优先级：基于 base_url 的启发式检测
    if base_url:
        for url_pattern, mode in _URL_HEURISTICS:
            if url_pattern in base_url:
                return mode

    # 默认值
    return ApiMode.CHAT_COMPLETIONS


def get_client_type(mode: ApiMode) -> str:
    """根据 API Mode 获取客户端类型名称。

    Args:
        mode: API Mode 枚举值。

    Returns:
        客户端类型名称字符串：
            - "openai": 使用 openai.OpenAI 客户端
            - "anthropic": 使用 anthropic.Anthropic 客户端
    """
    if mode == ApiMode.ANTHROPIC_MESSAGES:
        return "anthropic"
    return "openai"  # chat_completions 和 codex_responses 都用 OpenAI 客户端
