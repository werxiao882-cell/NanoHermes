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
)
from src.provider.credentials import resolve_credentials
from src.provider.api_mode import ApiMode, resolve_api_mode
from src.provider.client_factory import build_client
from src.provider.fallback import FallbackChain
from src.provider.model_metadata import ModelMetadata, get_context_length, calculate_cost

__all__ = [
    "ProviderProfile",
    "ProviderRegistry",
    "register_provider",
    "get_provider_profile",
    "list_providers",
    "resolve_provider_alias",
    "resolve_credentials",
    "ApiMode",
    "resolve_api_mode",
    "build_client",
    "FallbackChain",
    "ModelMetadata",
    "get_context_length",
    "calculate_cost",
]
