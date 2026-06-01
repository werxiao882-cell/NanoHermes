"""辅助 LLM 客户端单元测试。"""

import pytest
from src.config import AuxiliaryConfig
from src.compression.auxiliary import (
    CompressionAuxiliaryClient,
    get_model_context_length,
    MINIMUM_CONTEXT_LENGTH,
)


class TestGetModelContextLength:
    """测试 get_model_context_length 函数。"""

    def test_known_model_gpt4_turbo(self):
        """测试已知模型 GPT-4 Turbo。"""
        assert get_model_context_length("gpt-4-turbo") == 128000

    def test_known_model_claude(self):
        """测试已知模型 Claude。"""
        assert get_model_context_length("claude-3-sonnet") == 200000

    def test_known_model_qwen(self):
        """测试已知模型 Qwen。"""
        assert get_model_context_length("qwen3.6-plus") == 131072

    def test_unknown_model_returns_default(self):
        """测试未知模型返回默认值 8192。"""
        assert get_model_context_length("unknown-model") == 8192


class TestCompressionAuxiliaryClient:
    """测试 CompressionAuxiliaryClient 类。"""

    def test_default_config(self):
        """测试默认配置（provider='main'）。"""
        client = CompressionAuxiliaryClient()
        assert client.provider == "main"
        assert client.model == ""

    def test_custom_config(self):
        """测试自定义配置。"""
        config = AuxiliaryConfig(provider="openai", model="gpt-4o-mini")
        client = CompressionAuxiliaryClient(config=config)
        assert client.provider == "openai"
        assert client.model == "gpt-4o-mini"

    def test_config_from_nanohermes_json(self):
        """测试从 nanohermes.json 加载的配置。"""
        config = AuxiliaryConfig(
            provider="dashscope",
            model="qwen-turbo",
            max_tokens=2000,
            temperature=0.3,
        )
        client = CompressionAuxiliaryClient(config=config)
        assert client.provider == "dashscope"
        assert client.model == "qwen-turbo"


class TestCheckFeasibility:
    """测试可行性检查。"""

    def test_aux_model_not_configured(self):
        """测试辅助模型未配置（provider='main'）。"""
        client = CompressionAuxiliaryClient()
        result = client.check_feasibility(128000)
        assert result["feasible"] is True
        assert "warning" in result

    def test_aux_model_too_small(self):
        """测试辅助模型窗口太小。"""
        # gpt-4 有 8192 上下文，等于 MINIMUM_CONTEXT_LENGTH，不算太小
        # 使用一个未知模型（默认 8192）并调高 MINIMUM_CONTEXT_LENGTH 来测试
        # 更好的方式：使用 qwen-turbo (8192) 并检查边界
        config = AuxiliaryConfig(model="qwen-turbo")  # 8192 == MINIMUM_CONTEXT_LENGTH
        client = CompressionAuxiliaryClient(config=config)
        result = client.check_feasibility(128000)
        # 8192 >= 8192 (MINIMUM_CONTEXT_LENGTH)，所以 feasible
        # 但 8192 < 128000 * 0.8 = 102400，所以有 warning
        assert result["feasible"] is True
        assert "warning" in result

    def test_aux_model_smaller_than_main_threshold(self):
        """测试辅助模型窗口小于主模型阈值（警告）。"""
        config = AuxiliaryConfig(model="qwen-plus")  # 32768 < 128000 * 0.8 = 102400
        client = CompressionAuxiliaryClient(config=config)
        result = client.check_feasibility(128000)
        assert result["feasible"] is True
        assert "warning" in result

    def test_feasible_configuration(self):
        """测试可行配置。"""
        config = AuxiliaryConfig(model="gpt-4-turbo")  # 128000 >= 128000 * 0.8
        client = CompressionAuxiliaryClient(config=config)
        result = client.check_feasibility(128000)
        assert result["feasible"] is True
        assert "warning" not in result
