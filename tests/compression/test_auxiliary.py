"""压缩模块辅助工具单元测试。"""

import pytest
from src.compression.auxiliary import (
    get_model_context_length,
    MINIMUM_CONTEXT_LENGTH,
)
from src.compression.feasibility import check_compression_model_feasibility


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


class TestCheckFeasibility:
    """测试可行性检查。"""

    def test_model_too_small(self):
        """测试模型窗口太小。"""
        # qwen-turbo 有 8192 上下文，等于 MINIMUM_CONTEXT_LENGTH
        result = check_compression_model_feasibility("qwen-turbo", 128000)
        # 8192 >= 8192 (MINIMUM_CONTEXT_LENGTH)，所以 feasible
        # 但 8192 < 128000 * 0.8 = 102400，所以有 warning
        assert result["feasible"] is True
        assert "warning" in result

    def test_model_smaller_than_main_threshold(self):
        """测试模型窗口小于主模型阈值（警告）。"""
        # qwen-plus 32768 < 128000 * 0.8 = 102400
        result = check_compression_model_feasibility("qwen-plus", 128000)
        assert result["feasible"] is True
        assert "warning" in result

    def test_feasible_configuration(self):
        """测试可行配置。"""
        # gpt-4-turbo 128000 >= 128000 * 0.8
        result = check_compression_model_feasibility("gpt-4-turbo", 128000)
        assert result["feasible"] is True
        assert "warning" not in result

    def test_unknown_model(self):
        """测试未知模型（默认 8192）。"""
        result = check_compression_model_feasibility("unknown-model", 128000)
        # 8192 >= 8192 (MINIMUM_CONTEXT_LENGTH)，所以 feasible
        assert result["feasible"] is True
        assert "warning" in result
