"""辅助 LLM 客户端。

本模块为后台任务提供独立的 LLM 调用能力，包括：
- 上下文压缩摘要
- 记忆刷写
- 视觉提取摘要
- 技能审查
- 会话搜索摘要

关键设计：
1. 复用 ProviderResolver：不独立实现凭证逻辑，保持与主对话一致
2. "main" provider 回退：如果辅助配置指定 provider="main"，复用主对话模型
3. max_tokens 保护：强制默认最大 token 数，防止后台任务消耗过多资源
4. 从 Config 对象读取配置：统一使用 src.config 模块的配置模型
"""

from __future__ import annotations

import os
from typing import Any

from src.config.models import AuxiliaryConfig as ConfigAuxiliaryConfig

# Re-export for convenience (tests and other modules import from here)
AuxiliaryConfig = ConfigAuxiliaryConfig
from src.provider.api_mode import ApiMode, resolve_api_mode
from src.provider.client_factory import build_client
from src.provider.credentials import resolve_credentials, CredentialResult
from src.provider.profile import get_provider_profile
from src.provider.openai_client import OpenAIClient, ChatResponse
from src.provider.anthropic_adapter import AnthropicAdapter


# 辅助任务默认最大 token 数
# 后台任务通常不需要很长的输出，限制 token 数可防止资源浪费
_DEFAULT_AUX_MAX_TOKENS = 4000


class AuxiliaryClient:
    """辅助 LLM 客户端。

    为后台任务提供独立的 LLM 调用能力，与主对话模型解耦。

    配置解析流程：
    1. 如果 provider == "main"，使用主对话的凭证和模型
    2. 否则，通过 ProviderResolver 解析辅助配置的凭证
    3. 应用 max_tokens 默认值保护
    4. 构建对应的客户端（OpenAI 或 Anthropic）

    Attributes:
        _config: 辅助配置（来自 src.config.models.AuxiliaryConfig）。
        _main_credentials: 主对话的凭证（用于 "main" provider 回退）。
        _main_api_mode: 主对话的 API Mode（用于 "main" provider 回退）。
        _main_model: 主对话的模型名称（用于 "main" provider 回退）。
        _client: 懒加载的底层客户端。
    """

    def __init__(
        self,
        config: ConfigAuxiliaryConfig | None = None,
        main_credentials: CredentialResult | None = None,
        main_api_mode: ApiMode | None = None,
        main_model: str | None = None,
    ):
        """初始化辅助客户端。

        Args:
            config: 辅助配置（来自 Config 对象的 auxiliary 字段）。
                    None 时使用默认配置（provider="main"）。
            main_credentials: 主对话的凭证（用于 "main" provider 回退）。
            main_api_mode: 主对话的 API Mode（用于 "main" provider 回退）。
            main_model: 主对话的模型名称（用于 "main" provider 回退）。
        """
        self._config = config or ConfigAuxiliaryConfig()
        self._main_credentials = main_credentials
        self._main_api_mode = main_api_mode
        self._main_model = main_model
        self._client: OpenAIClient | AnthropicAdapter | None = None
        self._model: str = ""

    @property
    def provider(self) -> str:
        """当前配置的提供商。"""
        return self._config.provider

    @property
    def model(self) -> str:
        """当前配置的模型名称。"""
        return self._config.model

    def _resolve_main_model(self) -> str:
        """解析主对话模型名称。

        Returns:
            默认返回 "gpt-4o"。子类可覆盖此方法以提供不同的默认值。
        """
        return "gpt-4o"

    def _ensure_client(self) -> None:
        """确保客户端已初始化（懒加载）。

        如果 provider == "main"，复用主对话的凭证和模型。
        否则，从辅助配置解析独立的凭证和模型。
        """
        if self._client is not None:
            return

        # 确定使用的凭证和模型
        if self._config.provider == "main":
            # 复用主对话模型
            if not self._main_credentials:
                raise ValueError(
                    "辅助配置指定 provider='main'，但未提供主对话凭证"
                )
            credentials = self._main_credentials
            # 使用配置中的模型，如果未配置则使用主对话模型
            model = self._config.model or self._main_model or ""
            if not model:
                raise ValueError(
                    "辅助配置未指定模型，且主对话模型也未提供"
                )
            api_mode = self._main_api_mode or ApiMode.CHAT_COMPLETIONS
        else:
            # 独立的辅助提供商
            profile = get_provider_profile(self._config.provider)
            if not profile:
                raise ValueError(
                    f"未知的辅助提供商: {self._config.provider}"
                )

            credentials = resolve_credentials(
                env_vars=profile.env_vars,
                base_url=profile.base_url,
            )
            model = self._config.model
            if not model:
                raise ValueError(
                    f"辅助提供商 {self._config.provider} 未配置模型名称"
                )
            api_mode = resolve_api_mode(
                profile=profile,
                base_url=credentials.base_url,
            )

        self._model = model

        # 构建客户端
        if api_mode == ApiMode.ANTHROPIC_MESSAGES:
            from anthropic import Anthropic
            self._client = AnthropicAdapter(
                client=Anthropic(api_key=credentials.api_key),
                model=model,
            )
        else:
            from openai import OpenAI
            client_kwargs = {"api_key": credentials.api_key}
            if credentials.base_url:
                client_kwargs["base_url"] = credentials.base_url
            self._client = OpenAIClient(
                client=OpenAI(**client_kwargs),
                model=model,
            )

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """执行辅助聊天补全调用。

        Args:
            messages: OpenAI 格式的消息列表。
            max_tokens: 最大输出 token 数。None 时使用配置或默认值。
            **kwargs: 其他传递给客户端的参数。

        Returns:
            ChatResponse 封装的响应。
        """
        self._ensure_client()

        # 应用 max_tokens 保护
        effective_max_tokens = (
            max_tokens
            or self._config.max_tokens
            or _DEFAULT_AUX_MAX_TOKENS
        )

        return self._client.chat_completion(
            messages=messages,
            max_tokens=effective_max_tokens,
            temperature=self._config.temperature,
            **kwargs,
        )
