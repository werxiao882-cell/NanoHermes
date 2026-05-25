"""模型元数据注册表。

本模块维护模型相关的元数据：
1. 上下文长度：每个模型支持的最大 token 窗口
   - 用于判断是否需要触发上下文压缩
   - 用于计算 token 使用百分比

2. 定价数据：每个模型的 token 价格
   - 用于估算每次对话的 USD 成本
   - 用于洞察/指标系统的成本聚合

定价单位：每 1M tokens 的 USD 价格。
例如：input_price=15.0 表示每 1M 输入 token 收费 $15.00。

未知模型处理：
- 上下文长度：返回安全默认值（8192 tokens）
- 定价：返回零（保守估算，不夸大成本）
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelPricing:
    """模型定价数据。

    所有价格单位为 USD / 1M tokens。

    Attributes:
        input_price: 输入 token 价格（prompt）。
        output_price: 输出 token 价格（completion）。
        cache_read_price: 缓存读取价格（通常比输入便宜）。
        cache_write_price: 缓存写入价格（首次缓存时收费）。
    """
    input_price: float = 0.0
    output_price: float = 0.0
    cache_read_price: float = 0.0
    cache_write_price: float = 0.0


@dataclass
class ModelInfo:
    """单个模型的完整元数据。

    Attributes:
        id: 模型标识符（如 "gpt-4o", "claude-sonnet-4-20250514"）。
        context_length: 最大上下文窗口（tokens）。
        pricing: 定价数据。
    """
    id: str
    context_length: int
    pricing: ModelPricing


# ============================================================================
# 模型元数据注册表
# ============================================================================
# 格式：模型 ID → ModelInfo
# 注意：模型 ID 需要完全匹配（区分大小写）
#
# 定价数据来源：各提供商官方定价页面（截至 2025 年 5 月）
# ============================================================================
_MODEL_REGISTRY: dict[str, ModelInfo] = {
    # --- OpenAI 模型 ---
    "gpt-4o": ModelInfo(
        id="gpt-4o",
        context_length=128_000,
        pricing=ModelPricing(
            input_price=5.0,
            output_price=15.0,
            cache_read_price=1.25,
            cache_write_price=2.50,
        ),
    ),
    "gpt-4o-mini": ModelInfo(
        id="gpt-4o-mini",
        context_length=128_000,
        pricing=ModelPricing(
            input_price=0.15,
            output_price=0.60,
            cache_read_price=0.075,
            cache_write_price=0.15,
        ),
    ),
    "gpt-4-turbo": ModelInfo(
        id="gpt-4-turbo",
        context_length=128_000,
        pricing=ModelPricing(
            input_price=10.0,
            output_price=30.0,
        ),
    ),
    "o1": ModelInfo(
        id="o1",
        context_length=200_000,
        pricing=ModelPricing(
            input_price=15.0,
            output_price=60.0,
        ),
    ),
    "o1-mini": ModelInfo(
        id="o1-mini",
        context_length=128_000,
        pricing=ModelPricing(
            input_price=3.0,
            output_price=12.0,
        ),
    ),
    "o3-mini": ModelInfo(
        id="o3-mini",
        context_length=200_000,
        pricing=ModelPricing(
            input_price=1.10,
            output_price=4.40,
        ),
    ),

    # --- Anthropic 模型 ---
    "claude-sonnet-4-20250514": ModelInfo(
        id="claude-sonnet-4-20250514",
        context_length=200_000,
        pricing=ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_read_price=0.30,
            cache_write_price=3.75,
        ),
    ),
    "claude-opus-4-20250514": ModelInfo(
        id="claude-opus-4-20250514",
        context_length=200_000,
        pricing=ModelPricing(
            input_price=15.0,
            output_price=75.0,
            cache_read_price=1.50,
            cache_write_price=18.75,
        ),
    ),
    "claude-haiku-4-20250514": ModelInfo(
        id="claude-haiku-4-20250514",
        context_length=200_000,
        pricing=ModelPricing(
            input_price=0.80,
            output_price=4.0,
            cache_read_price=0.08,
            cache_write_price=1.0,
        ),
    ),
    "claude-3-5-sonnet-20241022": ModelInfo(
        id="claude-3-5-sonnet-20241022",
        context_length=200_000,
        pricing=ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_read_price=0.30,
            cache_write_price=3.75,
        ),
    ),

    # --- 通过 OpenRouter 访问的常见模型 ---
    # 注意：OpenRouter 的模型 ID 格式为 "provider/model"
    "anthropic/claude-sonnet-4": ModelInfo(
        id="anthropic/claude-sonnet-4",
        context_length=200_000,
        pricing=ModelPricing(
            input_price=3.0,
            output_price=15.0,
        ),
    ),
    "openai/gpt-4o": ModelInfo(
        id="openai/gpt-4o",
        context_length=128_000,
        pricing=ModelPricing(
            input_price=5.0,
            output_price=15.0,
        ),
    ),
}

# 未知模型的默认上下文长度（安全值，不会导致溢出）
_DEFAULT_CONTEXT_LENGTH = 8192


def get_context_length(model_id: str) -> int:
    """获取模型的上下文长度。

    如果模型未在注册表中，返回安全默认值（8192 tokens）。

    Args:
        model_id: 模型标识符（如 "gpt-4o", "claude-sonnet-4-20250514"）。

    Returns:
        模型的最大上下文窗口（tokens）。
    """
    info = _MODEL_REGISTRY.get(model_id)
    if info:
        return info.context_length
    return _DEFAULT_CONTEXT_LENGTH


def get_model_info(model_id: str) -> ModelInfo | None:
    """获取模型的完整元数据。

    Args:
        model_id: 模型标识符。

    Returns:
        ModelInfo 实例，如果模型未注册则返回 None。
    """
    return _MODEL_REGISTRY.get(model_id)


def calculate_cost(
    model_id: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """计算单次 API 调用的估算成本（USD）。

    成本计算公式：
        cost = (input_tokens / 1M * input_price)
             + (output_tokens / 1M * output_price)
             + (cache_read_tokens / 1M * cache_read_price)
             + (cache_write_tokens / 1M * cache_write_price)

    如果模型未在注册表中，返回 0.0（保守估算）。

    Args:
        model_id: 模型标识符。
        input_tokens: 输入 token 数量（prompt）。
        output_tokens: 输出 token 数量（completion）。
        cache_read_tokens: 缓存读取 token 数量。
        cache_write_tokens: 缓存写入 token 数量。

    Returns:
        估算的 USD 成本。

    Examples:
        >>> calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        0.0125  # (1000/1M * 5.0) + (500/1M * 15.0) = 0.005 + 0.0075
    """
    info = _MODEL_REGISTRY.get(model_id)
    if not info:
        return 0.0  # 未知模型，保守估算返回 0

    pricing = info.pricing
    cost = 0.0
    cost += (input_tokens / 1_000_000) * pricing.input_price
    cost += (output_tokens / 1_000_000) * pricing.output_price
    cost += (cache_read_tokens / 1_000_000) * pricing.cache_read_price
    cost += (cache_write_tokens / 1_000_000) * pricing.cache_write_price
    return cost


def register_model(info: ModelInfo) -> None:
    """注册一个新的模型元数据。

    用于动态添加自定义模型的元数据。

    Args:
        info: 要注册的 ModelInfo 实例。
    """
    _MODEL_REGISTRY[info.id] = info
