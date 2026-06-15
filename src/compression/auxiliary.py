"""压缩模块辅助工具。

提供模型上下文窗口查询等辅助功能。
摘要生成已集成到主对话的 model_caller，不再需要独立的辅助 LLM 客户端。
"""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# 最小上下文窗口要求（tokens）
MINIMUM_CONTEXT_LENGTH = 8192

# 模型上下文窗口映射
_MODEL_CONTEXT_LENGTHS: Dict[str, int] = {
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
}


def get_model_context_length(model: str) -> int:
    """获取模型上下文窗口大小。

    Args:
        model: 模型名称。

    Returns:
        上下文窗口大小（tokens），未知模型返回 8192。
    """
    return _MODEL_CONTEXT_LENGTHS.get(model, 8192)



