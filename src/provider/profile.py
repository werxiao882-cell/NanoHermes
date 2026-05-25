"""提供商配置文件定义和注册表。

本模块定义了 ProviderProfile 数据结构，用于描述一个 LLM 提供商的完整配置信息，
包括 API 模式、基础 URL、环境变量列表、回退模型列表和别名。

ProviderRegistry 是一个全局注册表，管理所有已注册的提供商配置，并支持别名解析。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FallbackModel:
    """回退模型配置，定义当主模型失败时尝试的 (提供商, 模型) 对。

    Attributes:
        provider: 回退提供商的 ID（如 "openai", "anthropic"）。
        model: 回退模型的名称（如 "gpt-4o", "claude-sonnet-4-6"）。
    """
    provider: str
    model: str


@dataclass
class ProviderProfile:
    """描述一个 LLM 推理提供商的完整配置。

    每个提供商配置文件包含以下信息：
    - 唯一 ID 和显示名称
    - API 模式（chat_completions、anthropic_messages 等）
    - 基础 URL（可选，None 表示使用 SDK 默认值）
    - 环境变量列表（按优先级排序，用于查找 API Key）
    - 回退模型列表（主模型失败时尝试的备用模型）
    - 别名列表（用于简化命令行输入）

    Attributes:
        id: 提供商的唯一标识符（如 "openai", "anthropic"）。
        name: 提供商的显示名称（如 "OpenAI", "Anthropic"）。
        api_mode: API 执行模式，决定请求格式和客户端类型。
            - "chat_completions": OpenAI 兼容端点（标准格式）
            - "anthropic_messages": 原生 Anthropic Messages API
            - "codex_responses": OpenAI Responses API（Codex）
        base_url: 基础 URL，None 表示使用 SDK 默认值。
        env_vars: 环境变量名称列表，按优先级排序，用于查找 API Key。
        fallback_models: 回退模型列表，主模型失败时按顺序尝试。
        aliases: 别名列表，用于简化命令行输入（如 "oai" → "openai"）。
    """
    id: str
    name: str
    api_mode: str
    base_url: str | None = None
    env_vars: list[str] = field(default_factory=list)
    fallback_models: list[FallbackModel] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)


class ProviderRegistry:
    """提供商配置的全局注册表和别名映射。

    这是一个单例模式的类，使用类变量存储所有已注册的提供商配置。
    支持通过 ID 查找、列出所有提供商、以及解析别名到标准 ID。

    类变量:
        _profiles: 存储 provider_id → ProviderProfile 的映射。
        _aliases: 存储 alias → provider_id 的映射。
    """

    _profiles: dict[str, ProviderProfile] = {}
    _aliases: dict[str, str] = {}

    @classmethod
    def register(cls, profile: ProviderProfile) -> None:
        """注册一个提供商配置文件。

        如果该 ID 已存在，则覆盖旧配置。同时注册所有别名。

        Args:
            profile: 要注册的 ProviderProfile 实例。
        """
        cls._profiles[profile.id] = profile
        # 注册所有别名，指向该提供商 ID
        for alias in profile.aliases:
            cls._aliases[alias] = profile.id

    @classmethod
    def get_profile(cls, provider_id: str) -> ProviderProfile | None:
        """根据提供商 ID 获取配置文件。

        Args:
            provider_id: 提供商的唯一标识符。

        Returns:
            对应的 ProviderProfile 实例，如果未找到则返回 None。
        """
        return cls._profiles.get(provider_id)

    @classmethod
    def list_ids(cls) -> list[str]:
        """返回所有已注册的提供商 ID 列表。

        Returns:
            字符串列表，包含所有已注册的提供商 ID。
        """
        return list(cls._profiles.keys())

    @classmethod
    def resolve_alias(cls, alias: str) -> str | None:
        """将别名解析为标准的提供商 ID。

        Args:
            alias: 别名（如 "oai", "claude"）。

        Returns:
            对应的标准提供商 ID，如果别名不存在则返回 None。
        """
        return cls._aliases.get(alias)

    @classmethod
    def clear(cls) -> None:
        """清除所有注册信息。仅用于测试。"""
        cls._profiles.clear()
        cls._aliases.clear()


def register_provider(profile: ProviderProfile) -> None:
    """便捷函数：注册一个提供商配置文件。

    这是 ProviderRegistry.register() 的便捷包装，方便模块级调用。

    Args:
        profile: 要注册的 ProviderProfile 实例。
    """
    ProviderRegistry.register(profile)


def get_provider_profile(provider_id: str) -> ProviderProfile | None:
    """便捷函数：根据提供商 ID 获取配置文件。

    Args:
        provider_id: 提供商的唯一标识符。

    Returns:
        对应的 ProviderProfile 实例，如果未找到则返回 None。
    """
    return ProviderRegistry.get_profile(provider_id)


def list_providers() -> list[str]:
    """便捷函数：列出所有已注册的提供商 ID。

    Returns:
        字符串列表，包含所有已注册的提供商 ID。
    """
    return ProviderRegistry.list_ids()


def resolve_provider_alias(alias: str) -> str | None:
    """便捷函数：将别名解析为标准的提供商 ID。

    Args:
        alias: 别名（如 "oai", "claude"）。

    Returns:
        对应的标准提供商 ID，如果别名不存在则返回 None。
    """
    return ProviderRegistry.resolve_alias(alias)
