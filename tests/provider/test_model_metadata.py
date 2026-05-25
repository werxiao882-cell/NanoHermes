"""测试: 模型元数据注册表。"""

import pytest

from src.provider.model_metadata import (
    ModelInfo,
    ModelPricing,
    get_context_length,
    get_model_info,
    calculate_cost,
    register_model,
    _MODEL_REGISTRY,
)


class TestGetContextLength:
    """测试 get_context_length 函数。"""

    def test_known_model_gpt4o(self):
        """测试已知模型 GPT-4o 的上下文长度。"""
        assert get_context_length("gpt-4o") == 128_000

    def test_known_model_claude_sonnet_4(self):
        """测试已知模型 Claude Sonnet 4 的上下文长度。"""
        assert get_context_length("claude-sonnet-4-20250514") == 200_000

    def test_unknown_model_returns_default(self):
        """测试未知模型返回默认上下文长度。"""
        assert get_context_length("unknown-model-xyz") == 8192


class TestGetModelInfo:
    """测试 get_model_info 函数。"""

    def test_known_model_returns_info(self):
        """测试已知模型返回完整信息。"""
        info = get_model_info("gpt-4o")
        assert info is not None
        assert info.id == "gpt-4o"
        assert info.context_length == 128_000
        assert info.pricing.input_price == 5.0

    def test_unknown_model_returns_none(self):
        """测试未知模型返回 None。"""
        assert get_model_info("nonexistent-model") is None


class TestCalculateCost:
    """测试 calculate_cost 函数。"""

    def test_gpt4o_cost_calculation(self):
        """测试 GPT-4o 成本计算。

        GPT-4o 定价: input=$5/M, output=$15/M
        1000 input + 500 output = (1000/1M * 5) + (500/1M * 15) = 0.005 + 0.0075 = 0.0125
        """
        cost = calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        assert abs(cost - 0.0125) < 0.0001

    def test_cost_with_cache_tokens(self):
        """测试包含缓存 token 的成本计算。

        GPT-4o 定价: cache_read=$1.25/M, cache_write=$2.50/M
        1000 cache_read + 500 cache_write = (1000/1M * 1.25) + (500/1M * 2.50) = 0.00125 + 0.00125 = 0.0025
        """
        cost = calculate_cost(
            "gpt-4o",
            cache_read_tokens=1000,
            cache_write_tokens=500,
        )
        assert abs(cost - 0.0025) < 0.0001

    def test_unknown_model_zero_cost(self):
        """测试未知模型成本为零。"""
        cost = calculate_cost("unknown-xyz", input_tokens=10000, output_tokens=5000)
        assert cost == 0.0

    def test_zero_tokens_zero_cost(self):
        """测试零 token 时成本为零。"""
        cost = calculate_cost("gpt-4o")
        assert cost == 0.0

    def test_claude_sonnet_4_cost(self):
        """测试 Claude Sonnet 4 成本计算。

        定价: input=$3/M, output=$15/M
        2000 input + 1000 output = (2000/1M * 3) + (1000/1M * 15) = 0.006 + 0.015 = 0.021
        """
        cost = calculate_cost(
            "claude-sonnet-4-20250514",
            input_tokens=2000,
            output_tokens=1000,
        )
        assert abs(cost - 0.021) < 0.0001


class TestRegisterModel:
    """测试 register_model 函数。"""

    def test_register_custom_model(self):
        """测试注册自定义模型。"""
        info = ModelInfo(
            id="my-custom-model",
            context_length=32_000,
            pricing=ModelPricing(input_price=1.0, output_price=3.0),
        )
        register_model(info)

        assert get_context_length("my-custom-model") == 32_000
        cost = calculate_cost("my-custom-model", input_tokens=1_000_000)
        assert abs(cost - 1.0) < 0.0001
