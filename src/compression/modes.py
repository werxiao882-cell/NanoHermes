"""压缩模式实现。

提供多种压缩触发策略，适应不同场景需求：
- Reactive（响应式）：基于 token 阈值触发，适合长对话
- Micro（微压缩）：基于对话轮次触发，适合持续对话
- Snip（裁剪）：基于消息内容特征触发，适合精准裁剪

设计理由：
- 不同场景需要不同的压缩触发策略
- Reactive 模式简单直观，但可能突然触发
- Micro 模式频繁小压缩，用户感知平滑
- Snip 模式精准裁剪特定内容，保留对话连贯性
- 通过配置选择模式，灵活适应各种需求
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class CompressionMode(Enum):
    """压缩模式枚举。"""
    REACTIVE = "reactive"
    MICRO = "micro"
    SNIP = "snip"


class BaseCompressionMode(ABC):
    """压缩模式基类。

    所有压缩模式必须实现 should_compress() 方法，
    根据当前状态判断是否触发压缩。
    """

    @abstractmethod
    def should_compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        turn_count: Optional[int] = None,
    ) -> bool:
        """判断是否应该触发压缩。

        Args:
            messages: 当前对话消息列表。
            current_tokens: 当前 token 数（可选）。
            max_tokens: 最大 token 数（可选）。
            turn_count: 当前对话轮次（可选）。

        Returns:
            True 表示应该触发压缩，False 表示不触发。
        """
        pass

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """模式名称。"""
        pass


class ReactiveMode(BaseCompressionMode):
    """响应式压缩模式。

    基于 token 使用率触发压缩，当 current_tokens >= threshold * max_tokens 时触发。

    适用场景：
    - 长对话，token 接近上限时触发
    - 简单直观，节省计算资源

    缺点：
    - 可能突然触发，用户感知明显
    """

    def __init__(self, threshold: float = 0.5):
        """初始化响应式模式。

        Args:
            threshold: 触发阈值（0.0 ~ 1.0），默认 0.5（50%）。
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be between 0.0 and 1.0, got {threshold}")
        self._threshold = threshold

    @property
    def mode_name(self) -> str:
        return CompressionMode.REACTIVE.value

    @property
    def threshold(self) -> float:
        """触发阈值。"""
        return self._threshold

    def should_compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        turn_count: Optional[int] = None,
    ) -> bool:
        """判断是否应该触发压缩。

        Args:
            messages: 当前对话消息列表（未使用）。
            current_tokens: 当前 token 数。
            max_tokens: 最大 token 数。
            turn_count: 当前对话轮次（未使用）。

        Returns:
            True 表示应该触发压缩。
        """
        if current_tokens is None or max_tokens is None:
            return False

        if max_tokens <= 0:
            return False

        usage_ratio = current_tokens / max_tokens
        return usage_ratio >= self._threshold


class MicroMode(BaseCompressionMode):
    """微压缩模式。

    基于对话轮次触发压缩，每 N 轮触发一次。

    适用场景：
    - 持续对话，保持上下文流畅
    - 频繁小压缩，用户感知平滑

    缺点：
    - 压缩频率高，增加计算开销
    """

    def __init__(self, interval: int = 10):
        """初始化微压缩模式。

        Args:
            interval: 触发间隔（轮次），默认 10。
        """
        if interval <= 0:
            raise ValueError(f"interval must be positive, got {interval}")
        self._interval = interval

    @property
    def mode_name(self) -> str:
        return CompressionMode.MICRO.value

    @property
    def interval(self) -> int:
        """触发间隔（轮次）。"""
        return self._interval

    def should_compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        turn_count: Optional[int] = None,
    ) -> bool:
        """判断是否应该触发压缩。

        Args:
            messages: 当前对话消息列表（未使用）。
            current_tokens: 当前 token 数（未使用）。
            max_tokens: 最大 token 数（未使用）。
            turn_count: 当前对话轮次。

        Returns:
            True 表示应该触发压缩。
        """
        if turn_count is None:
            return False

        return turn_count > 0 and turn_count % self._interval == 0


class SnipMode(BaseCompressionMode):
    """裁剪模式。

    基于消息内容特征触发压缩，检测到特定模式时触发。

    适用场景：
    - 工具输出过长，需要精准裁剪
    - 检测到代码块、日志、traceback 等长内容

    缺点：
    - 需要消息分类逻辑
    - 模式匹配可能误判
    """

    # 默认裁剪模式：代码块、日志、输出、traceback
    DEFAULT_PATTERNS = [
        r"```",           # 代码块
        r"logs?:",        # 日志
        r"output:",       # 输出
        r"traceback:",    # 错误追踪
        r"error:",        # 错误
        r"warning:",      # 警告
    ]

    def __init__(self, patterns: Optional[List[str]] = None):
        """初始化裁剪模式。

        Args:
            patterns: 触发模式列表（正则表达式），默认使用 DEFAULT_PATTERNS。
        """
        if patterns is None:
            patterns = self.DEFAULT_PATTERNS

        self._patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    @property
    def mode_name(self) -> str:
        return CompressionMode.SNIP.value

    @property
    def patterns(self) -> List[str]:
        """触发模式列表（原始字符串）。"""
        return [p.pattern for p in self._patterns]

    def should_compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        turn_count: Optional[int] = None,
    ) -> bool:
        """判断是否应该触发压缩。

        检查最近 5 条消息是否匹配任何触发模式。

        Args:
            messages: 当前对话消息列表。
            current_tokens: 当前 token 数（未使用）。
            max_tokens: 最大 token 数（未使用）。
            turn_count: 当前对话轮次（未使用）。

        Returns:
            True 表示应该触发压缩。
        """
        if not messages:
            return False

        # 检查最近 5 条消息
        recent_messages = messages[-5:]

        for msg in recent_messages:
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue

            for pattern in self._patterns:
                if pattern.search(content):
                    return True

        return False


def create_mode(
    mode_name: str,
    reactive_threshold: float = 0.5,
    micro_interval: int = 10,
    snip_patterns: Optional[List[str]] = None,
) -> BaseCompressionMode:
    """创建压缩模式实例（工厂函数）。

    Args:
        mode_name: 模式名称（"reactive"、"micro"、"snip"）。
        reactive_threshold: Reactive 模式的触发阈值。
        micro_interval: Micro 模式的触发间隔。
        snip_patterns: Snip 模式的触发模式列表。

    Returns:
        压缩模式实例。

    Raises:
        ValueError: 无效的模式名称。
    """
    mode_name_lower = mode_name.lower()

    if mode_name_lower == CompressionMode.REACTIVE.value:
        return ReactiveMode(threshold=reactive_threshold)

    elif mode_name_lower == CompressionMode.MICRO.value:
        return MicroMode(interval=micro_interval)

    elif mode_name_lower == CompressionMode.SNIP.value:
        return SnipMode(patterns=snip_patterns)

    else:
        valid_modes = [m.value for m in CompressionMode]
        raise ValueError(
            f"Invalid compression mode: {mode_name}. "
            f"Valid modes are: {', '.join(valid_modes)}"
        )
