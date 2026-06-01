"""压缩可行性检查。

验证辅助模型上下文窗口是否满足压缩要求。
配置统一使用 src.config.AuxiliaryConfig（来自 nanohermes.json）。
"""

from typing import Any, Dict, Optional

from src.config import AuxiliaryConfig
from src.compression.auxiliary import CompressionAuxiliaryClient


def check_compression_model_feasibility(
    auxiliary_config: Optional[AuxiliaryConfig] = None,
    main_context_length: int = 8192,
    main_credentials: Any = None,
    main_api_mode: Any = None,
) -> Dict[str, Any]:
    """检查压缩模型可行性。

    Args:
        auxiliary_config: 辅助 LLM 配置（来自 nanohermes.json 的 auxiliary 段）。
        main_context_length: 主模型上下文窗口大小。
        main_credentials: 主对话凭证（provider="main" 时必需）。
        main_api_mode: 主对话 API Mode（provider="main" 时使用）。

    Returns:
        可行性检查结果。
    """
    client = CompressionAuxiliaryClient(
        config=auxiliary_config,
        main_credentials=main_credentials,
        main_api_mode=main_api_mode,
    )
    return client.check_feasibility(main_context_length)
