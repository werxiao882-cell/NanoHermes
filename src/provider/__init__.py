"""Provider runtime: credential resolution, API mode routing, client building.

提供商运行时：凭证解析、API 模式路由、客户端构建。
"""

from src.provider.profile import (
    ProviderProfile,
    ProviderRegistry,
    register_provider,
    get_provider_profile,
    list_providers,
    resolve_provider_alias,
    FallbackModel,
)
from src.provider.credentials import resolve_credentials
from src.provider.api_mode import ApiMode, resolve_api_mode
from src.provider.client_factory import build_client
from src.provider.openai_client import OpenAIClient, ChatResponse, TokenUsage, ClassifiedError, ErrorCategory
from src.provider.anthropic_adapter import AnthropicAdapter
from src.provider.fallback import FallbackChain, FallbackEntry
from src.provider.model_metadata import ModelInfo, ModelPricing, get_context_length, calculate_cost

__all__ = [
    "ProviderProfile",
    "ProviderRegistry",
    "register_provider",
    "get_provider_profile",
    "list_providers",
    "resolve_provider_alias",
    "FallbackModel",
    "resolve_credentials",
    "ApiMode",
    "resolve_api_mode",
    "build_client",
    "OpenAIClient",
    "AnthropicAdapter",
    "ChatResponse",
    "TokenUsage",
    "ClassifiedError",
    "ErrorCategory",
    "FallbackChain",
    "FallbackEntry",
    "ModelInfo",
    "ModelPricing",
    "get_context_length",
    "calculate_cost",
]
