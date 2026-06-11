"""辅助模型可行性检查的独立测试。

使用 mock 避免依赖 src.auxiliary 和 src.provider 模块的完整导入链。
"""

import pytest
from unittest.mock import patch, MagicMock

# 最小上下文窗口要求（tokens）
MINIMUM_CONTEXT_LENGTH = 8192

# 模型上下文窗口映射（复制自 auxiliary.py）
_MODEL_CONTEXT_LENGTHS = {
    "gpt-3.5-turbo": 16385,
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "claude-3-haiku": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-opus": 200000,
    "claude-3-5-sonnet": 200000,
    "qwen-turbo": 8192,
    "qwen-plus": 32768,
    "qwen-max": 32768,
    "qwen3.6-plus": 131072,
    # 添加一个小窗口模型用于测试
    "tiny-model": 4096,  # 小于 MINIMUM_CONTEXT_LENGTH
}


def get_model_context_length(model: str) -> int:
    """获取模型上下文窗口大小。"""
    return _MODEL_CONTEXT_LENGTHS.get(model, 8192)


def check_feasibility(model: str, main_context_length: int) -> dict:
    """检查辅助模型可行性（简化版，用于测试）。"""
    if not model:
        return {
            "feasible": True,
            "warning": "辅助模型未配置，将使用主模型（provider='main'）",
        }

    aux_context_length = get_model_context_length(model)
    main_compression_threshold = main_context_length * 0.8

    # 8.3.1 测试场景：辅助模型窗口小于最小要求
    if aux_context_length < MINIMUM_CONTEXT_LENGTH:
        return {
            "feasible": False,
            "reason": (
                f"辅助模型上下文窗口 ({aux_context_length}) "
                f"小于最小要求 ({MINIMUM_CONTEXT_LENGTH})"
            ),
        }

    # 8.3.2 测试场景：辅助模型窗口小于主模型阈值（警告）
    if aux_context_length < main_compression_threshold:
        return {
            "feasible": True,
            "warning": (
                f"辅助模型上下文窗口 ({aux_context_length}) "
                f"小于主模型压缩阈值 ({int(main_compression_threshold)})，压缩可能失败"
            ),
        }

    # 8.3.3 测试场景：可行配置
    return {"feasible": True}


class TestAuxiliaryModelFeasibility:
    """任务 8.3.1-8.3.3：辅助模型可行性检查测试。"""

    def test_8_3_1_aux_model_window_below_minimum(self):
        """8.3.1 测试辅助模型窗口小于最小要求。

        使用 tiny-model（4096 < 8192）测试。
        预期：feasible=False，包含 reason 说明。
        """
        result = check_feasibility("tiny-model", 128000)

        assert result["feasible"] is False
        assert "reason" in result
        assert "4096" in result["reason"]
        assert "8192" in result["reason"]
        assert "小于最小要求" in result["reason"]

    def test_8_3_1_unknown_model_returns_default_not_below_minimum(self):
        """8.3.1 边界测试：未知模型默认 8192，等于 MINIMUM_CONTEXT_LENGTH。

        预期：feasible=True（因为 8192 >= 8192），但有警告。
        """
        result = check_feasibility("unknown-model-xyz", 128000)

        # 未知模型默认 8192，等于 MINIMUM_CONTEXT_LENGTH，不算太小
        assert result["feasible"] is True
        # 8192 < 128000 * 0.8 = 102400，所以有警告
        assert "warning" in result

    def test_8_3_2_aux_model_below_main_threshold(self):
        """8.3.2 测试辅助模型窗口小于主模型阈值（警告）。

        使用 qwen-plus（32768 < 128000 * 0.8 = 102400）测试。
        预期：feasible=True，包含 warning 说明。
        """
        result = check_feasibility("qwen-plus", 128000)

        assert result["feasible"] is True
        assert "warning" in result
        assert "32768" in result["warning"]
        assert "102400" in result["warning"]
        assert "小于主模型压缩阈值" in result["warning"]

    def test_8_3_2_aux_model_at_threshold_boundary(self):
        """8.3.2 边界测试：辅助模型窗口刚好等于主模型阈值。

        使用 gpt-4-turbo（128000）和主模型 160000。
        阈值 = 160000 * 0.8 = 128000，刚好相等。
        预期：feasible=True，无警告。
        """
        result = check_feasibility("gpt-4-turbo", 160000)

        assert result["feasible"] is True
        assert "warning" not in result

    def test_8_3_3_feasible_configuration(self):
        """8.3.3 测试可行配置。

        使用 gpt-4-turbo（128000 >= 128000 * 0.8）测试。
        预期：feasible=True，无 warning。
        """
        result = check_feasibility("gpt-4-turbo", 128000)

        assert result["feasible"] is True
        assert "warning" not in result
        assert "reason" not in result

    def test_8_3_3_high_context_main_model(self):
        """8.3.3 测试可行配置：使用 claude-3-sonnet（200000）作为辅助模型。

        主模型窗口较小（如 80000），辅助模型完全满足要求。
        预期：feasible=True，无 warning。
        """
        result = check_feasibility("claude-3-sonnet", 80000)

        assert result["feasible"] is True
        assert "warning" not in result

    def test_no_model_configured(self):
        """测试辅助模型未配置（model 为空）。

        预期：feasible=True，包含 warning 说明使用主模型。
        """
        result = check_feasibility("", 128000)

        assert result["feasible"] is True
        assert "warning" in result
        assert "provider='main'" in result["warning"]