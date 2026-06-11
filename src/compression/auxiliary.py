"""辅助 LLM 客户端（压缩模块）。

为上下文压缩提供辅助 LLM 调用能力。
复用 src.config.AuxiliaryConfig 配置，委托 src.auxiliary.client.AuxiliaryClient 执行实际调用。

配置来源：nanohermes.json 的 auxiliary 段
```json
{
  "auxiliary": {
    "provider": "main",
    "model": "",
    "max_tokens": null,
    "temperature": null
  }
}
```
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.config import AuxiliaryConfig
from src.auxiliary.client import AuxiliaryClient as BaseAuxiliaryClient
from src.config.models import AuxiliaryConfig as BaseAuxiliaryConfig

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


class CompressionAuxiliaryClient:
    """压缩模块辅助 LLM 客户端。

    封装 src.auxiliary.client.AuxiliaryClient，提供压缩专用的摘要生成和可行性检查。
    配置统一使用 src.config.AuxiliaryConfig（来自 nanohermes.json）。

    Attributes:
        _config: 辅助配置（来自 config 模块）。
        _client: 底层辅助客户端（来自 auxiliary 模块）。
    """

    def __init__(
        self,
        config: Optional[AuxiliaryConfig] = None,
        main_credentials: Any = None,
        main_api_mode: Any = None,
    ):
        """初始化压缩辅助客户端。

        Args:
            config: 辅助配置（来自 nanohermes.json 的 auxiliary 段）。
                    None 时使用默认配置（provider="main"）。
            main_credentials: 主对话凭证（provider="main" 时必需）。
            main_api_mode: 主对话 API Mode（provider="main" 时使用）。
        """
        self._config = config or AuxiliaryConfig()
        self._client = BaseAuxiliaryClient(
            config=self._to_base_config(self._config),
            main_credentials=main_credentials,
            main_api_mode=main_api_mode,
        )

    @staticmethod
    def _to_base_config(config: AuxiliaryConfig) -> BaseAuxiliaryConfig:
        """将 config 模块的 AuxiliaryConfig 转换为 auxiliary 模块的 AuxiliaryConfig。

        两个模块的 AuxiliaryConfig 字段完全一致，只是类型不同。
        """
        return BaseAuxiliaryConfig(
            provider=config.provider,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

    @property
    def model(self) -> str:
        """当前配置的模型名称。"""
        return self._config.model

    @property
    def provider(self) -> str:
        """当前配置的提供商。"""
        return self._config.provider

    def generate_summary(self, prompt: str, max_tokens: int) -> str:
        """生成摘要。

        通过底层 AuxiliaryClient 调用 LLM API 生成结构化摘要。

        Args:
            prompt: 摘要提示文本。
            max_tokens: 最大输出 token 数。

        Returns:
            生成的摘要文本。
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a conversation summarizer. "
                    "Generate a concise, structured summary of the conversation. "
                    "Focus on key decisions, progress, and current state."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response = self._client.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
        )

        return response.content

    def check_feasibility(self, main_context_length: int) -> Dict[str, Any]:
        """检查辅助模型可行性。

        验证辅助模型的上下文窗口是否满足压缩要求。

        Args:
            main_context_length: 主模型上下文窗口大小。

        Returns:
            可行性检查结果字典。
        """
        model = self._config.model
        if not model:
            return {
                "feasible": True,
                "warning": "辅助模型未配置，将使用主模型（provider='main'）",
            }

        aux_context_length = get_model_context_length(model)
        main_compression_threshold = main_context_length * 0.8

        if aux_context_length < MINIMUM_CONTEXT_LENGTH:
            return {
                "feasible": False,
                "reason": (
                    f"辅助模型上下文窗口 ({aux_context_length}) "
                    f"小于最小要求 ({MINIMUM_CONTEXT_LENGTH})"
                ),
            }

        if aux_context_length < main_compression_threshold:
            return {
                "feasible": True,
                "warning": (
                    f"辅助模型上下文窗口 ({aux_context_length}) "
                    f"小于主模型压缩阈值 ({main_compression_threshold})，压缩可能失败"
                ),
            }

        return {"feasible": True}
