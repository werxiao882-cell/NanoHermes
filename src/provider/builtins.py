"""内置提供商配置文件。

本模块注册 NanoHermes 默认支持的 LLM 提供商：
- OpenAI: 标准 chat_completions 模式，支持 GPT-4、GPT-4o 等模型
- Anthropic: 原生 anthropic_messages 模式，支持 Claude 系列模型
- OpenRouter: 通过 OpenRouter 网关访问多个提供商的模型
- Custom: 用户自定义的 OpenAI 兼容端点

每个提供商在模块导入时自动注册到 ProviderRegistry。
"""

from src.provider.profile import ProviderProfile, FallbackModel, register_provider

# ============================================================================
# OpenAI 提供商
# ============================================================================
# 使用标准 chat_completions API 模式，兼容所有 OpenAI 模型。
# 基础 URL 指向 api.openai.com，API Key 从 OPENAI_API_KEY 环境变量读取。
# 别名 "oai" 可用于命令行简化输入。
register_provider(ProviderProfile(
    id="openai",
    name="OpenAI",
    api_mode="chat_completions",
    base_url="https://api.openai.com/v1",
    env_vars=["OPENAI_API_KEY"],
    fallback_models=[
        FallbackModel(provider="openai", model="gpt-4o"),
        FallbackModel(provider="openai", model="gpt-4o-mini"),
    ],
    aliases=["oai"],
))

# ============================================================================
# Anthropic 提供商（原生 Messages API）
# ============================================================================
# 使用原生 anthropic_messages API 模式，需要 Anthropic SDK 适配。
# base_url 为 None，因为 Anthropic SDK 使用自己的默认端点。
# API Key 从 ANTHROPIC_API_KEY 环境变量读取。
# 别名 "claude" 可用于命令行简化输入。
register_provider(ProviderProfile(
    id="anthropic",
    name="Anthropic",
    api_mode="anthropic_messages",
    base_url=None,  # Anthropic SDK 使用自己的默认端点
    env_vars=["ANTHROPIC_API_KEY"],
    fallback_models=[
        FallbackModel(provider="anthropic", model="claude-sonnet-4-20250514"),
        FallbackModel(provider="anthropic", model="claude-haiku-4-20250514"),
    ],
    aliases=["claude"],
))

# ============================================================================
# OpenRouter 提供商
# ============================================================================
# 通过 OpenRouter 网关访问多个提供商的模型，使用 chat_completions 模式。
# API Key 从 OPENROUTER_API_KEY 环境变量读取。
# 别名 "or" 可用于命令行简化输入。
register_provider(ProviderProfile(
    id="openrouter",
    name="OpenRouter",
    api_mode="chat_completions",
    base_url="https://openrouter.ai/api/v1",
    env_vars=["OPENROUTER_API_KEY"],
    fallback_models=[
        FallbackModel(provider="openrouter", model="anthropic/claude-sonnet-4"),
        FallbackModel(provider="openrouter", model="openai/gpt-4o"),
    ],
    aliases=["or"],
))

# ============================================================================
# Custom 提供商（用户自定义 OpenAI 兼容端点）
# ============================================================================
# 用于任何 OpenAI 兼容的 API 端点（如本地 Ollama、LM Studio 等）。
# base_url 为 None，需要用户在配置中指定。
# API Key 从 CUSTOM_API_KEY 环境变量读取。
register_provider(ProviderProfile(
    id="custom",
    name="Custom",
    api_mode="chat_completions",
    base_url=None,  # 需要用户在配置中指定
    env_vars=["CUSTOM_API_KEY"],
    fallback_models=[],
    aliases=[],
))
