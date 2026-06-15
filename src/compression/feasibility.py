"""压缩可行性检查。

验证模型上下文窗口是否满足压缩要求。
"""

from typing import Dict

from src.compression.auxiliary import get_model_context_length, MINIMUM_CONTEXT_LENGTH


def check_compression_model_feasibility(
    model: str,
    main_context_length: int = 8192,
) -> Dict[str, any]:
    """检查压缩模型可行性。

    Args:
        model: 模型名称。
        main_context_length: 主模型上下文窗口大小。

    Returns:
        可行性检查结果。
    """
    context_length = get_model_context_length(model)
    main_compression_threshold = main_context_length * 0.8

    if context_length < MINIMUM_CONTEXT_LENGTH:
        return {
            "feasible": False,
            "reason": (
                f"模型上下文窗口 ({context_length}) "
                f"小于最小要求 ({MINIMUM_CONTEXT_LENGTH})"
            ),
        }

    if context_length < main_compression_threshold:
        return {
            "feasible": True,
            "warning": (
                f"模型上下文窗口 ({context_length}) "
                f"小于主模型压缩阈值 ({main_compression_threshold})，压缩可能失败"
            ),
        }

    return {"feasible": True}
