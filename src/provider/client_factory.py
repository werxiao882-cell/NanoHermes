"""LLM 客户端工厂。

本模块根据 API Mode 创建对应的 SDK 客户端实例：
- chat_completions → openai.OpenAI
- anthropic_messages → anthropic.Anthropic
- codex_responses → openai.OpenAI（使用不同的端点）

工厂函数 build_client 是创建 LLM 客户端的统一入口，
调用方无需关心底层使用哪个 SDK。
"""

from __future__ import annotations

from openai import OpenAI
from anthropic import Anthropic

from src.provider.api_mode import ApiMode
from src.provider.credentials import CredentialResult


def build_client(
    api_mode: ApiMode,
    credentials: CredentialResult,
) -> OpenAI | Anthropic:
    """根据 API Mode 和凭证构建 LLM 客户端。

    构建逻辑：
    1. 根据 api_mode 选择 SDK 类型
    2. 使用 credentials 中的 api_key 和 base_url 初始化客户端
    3. 返回初始化完成的客户端实例

    Args:
        api_mode: API 执行模式，决定使用哪个 SDK。
        credentials: 已解析的凭证，包含 api_key 和 base_url。

    Returns:
        初始化完成的 SDK 客户端（OpenAI 或 Anthropic）。

    Raises:
        ValueError: 如果 api_mode 不受支持。

    Examples:
        >>> from src.provider.credentials import CredentialResult
        >>> from src.provider.api_mode import ApiMode, resolve_api_mode
        >>> creds = CredentialResult(api_key="sk-xxx", base_url=None, source="env")
        >>> client = build_client(ApiMode.CHAT_COMPLETIONS, creds)
        >>> type(client).__name__
        'OpenAI'
    """
    if api_mode == ApiMode.ANTHROPIC_MESSAGES:
        return _build_anthropic_client(credentials)
    else:
        # chat_completions 和 codex_responses 都使用 OpenAI 客户端
        return _build_openai_client(api_mode, credentials)


def _build_openai_client(
    api_mode: ApiMode,
    credentials: CredentialResult,
) -> OpenAI:
    """构建 OpenAI SDK 客户端。

    适用于 chat_completions 和 codex_responses 模式。

    Args:
        api_mode: API 执行模式。
        credentials: 已解析的凭证。

    Returns:
        初始化完成的 OpenAI 客户端实例。
    """
    client_kwargs = {
        "api_key": credentials.api_key,
    }

    # base_url 为 None 时使用 SDK 默认值
    if credentials.base_url:
        client_kwargs["base_url"] = credentials.base_url

    return OpenAI(**client_kwargs)


def _build_anthropic_client(
    credentials: CredentialResult,
) -> Anthropic:
    """构建 Anthropic SDK 客户端。

    Anthropic 客户端不使用 base_url 参数（使用 SDK 默认端点），
    除非显式指定了自定义端点。

    Args:
        credentials: 已解析的凭证。

    Returns:
        初始化完成的 Anthropic 客户端实例。
    """
    client_kwargs = {
        "api_key": credentials.api_key,
    }

    # 只有显式指定的 base_url 才传递
    if credentials.base_url:
        client_kwargs["base_url"] = credentials.base_url

    return Anthropic(**client_kwargs)
