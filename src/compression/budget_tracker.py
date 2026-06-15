"""预算追踪器实现。

监控压缩前后的 token 使用情况，计算压缩效率和历史统计。

设计理由：
- 使用环形缓冲区（collections.deque + maxlen）存储压缩历史
- 固定内存占用，自动淘汰旧数据，无需手动清理
- 支持快速计算滑动窗口统计（平均效率、成功率、总节省 token）
- 提供可观测性，帮助优化压缩策略和配置
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CompressionRecord:
    """压缩记录数据类。

    Attributes:
        before_tokens: 压缩前的 token 数。
        after_tokens: 压缩后的 token 数。
        saved_tokens: 节省的 token 数。
        compression_ratio: 压缩比（after / before）。
        success: 是否成功。
        timestamp: 记录时间（Unix 时间戳）。
        duration_ms: 压缩耗时（毫秒）。
    """
    before_tokens: int
    after_tokens: int
    saved_tokens: int
    compression_ratio: float
    success: bool
    timestamp: float
    duration_ms: float = 0.0


class BudgetTracker:
    """预算追踪器，用于监控压缩效率。

    使用环形缓冲区存储压缩历史，提供统计接口。

    设计理由：
    - max_history 默认 100：保留最近 100 次压缩记录，平衡内存占用和统计准确性
    - 环形缓冲区自动淘汰旧数据，避免内存泄漏
    - 统计方法使用 O(n) 遍历，n <= 100，性能可接受
    """

    def __init__(self, max_history: int = 100):
        """初始化预算追踪器。

        Args:
            max_history: 最大历史记录数，超过后自动淘汰最旧的记录。
        """
        self._max_history = max_history
        self._history: deque[CompressionRecord] = deque(maxlen=max_history)

    @property
    def history_count(self) -> int:
        """当前历史记录数量。"""
        return len(self._history)

    def track_compression(
        self,
        before_tokens: int,
        after_tokens: int,
        success: bool = True,
        duration_ms: float = 0.0,
    ) -> CompressionRecord:
        """记录一次压缩事件。

        Args:
            before_tokens: 压缩前的 token 数。
            after_tokens: 压缩后的 token 数。
            success: 是否成功。
            duration_ms: 压缩耗时（毫秒）。

        Returns:
            创建的压缩记录。
        """
        saved_tokens = max(0, before_tokens - after_tokens)
        compression_ratio = after_tokens / before_tokens if before_tokens > 0 else 1.0

        record = CompressionRecord(
            before_tokens=before_tokens,
            after_tokens=after_tokens,
            saved_tokens=saved_tokens,
            compression_ratio=compression_ratio,
            success=success,
            timestamp=time.time(),
            duration_ms=duration_ms,
        )

        self._history.append(record)
        return record

    def get_average_compression_ratio(self) -> float:
        """计算平均压缩比。

        压缩比 = after_tokens / before_tokens，值越小表示压缩效果越好。
        例如：0.6 表示压缩后保留了 60% 的 token。

        Returns:
            平均压缩比，无历史记录时返回 1.0（无压缩）。
        """
        if not self._history:
            return 1.0

        # 只计算成功的记录
        successful_records = [r for r in self._history if r.success]
        if not successful_records:
            return 1.0

        total_ratio = sum(r.compression_ratio for r in successful_records)
        return total_ratio / len(successful_records)

    def get_total_tokens_saved(self) -> int:
        """计算总节省的 token 数。

        Returns:
            总节省 token 数，只计算成功的记录。
        """
        return sum(r.saved_tokens for r in self._history if r.success)

    def get_success_rate(self) -> float:
        """计算压缩成功率。

        Returns:
            成功率（0.0 ~ 1.0），无历史记录时返回 1.0。
        """
        if not self._history:
            return 1.0

        successful_count = sum(1 for r in self._history if r.success)
        return successful_count / len(self._history)

    def get_average_duration_ms(self) -> float:
        """计算平均压缩耗时。

        Returns:
            平均耗时（毫秒），无历史记录时返回 0.0。
        """
        if not self._history:
            return 0.0

        total_duration = sum(r.duration_ms for r in self._history)
        return total_duration / len(self._history)

    def get_history(self, limit: Optional[int] = None) -> List[CompressionRecord]:
        """获取历史记录。

        Args:
            limit: 返回最近 N 条记录，None 表示返回全部。

        Returns:
            历史记录列表（按时间倒序，最新的在前）。
        """
        records = list(self._history)
        records.reverse()  # 最新的在前

        if limit is not None:
            records = records[:limit]

        return records

    def get_compression_efficiency(self) -> float:
        """计算压缩效率（综合指标）。

        效率 = (1 - 平均压缩比) * 成功率
        例如：平均压缩比 0.6，成功率 0.9，效率 = (1 - 0.6) * 0.9 = 0.36

        Returns:
            压缩效率（0.0 ~ 1.0），值越高表示压缩效果越好。
        """
        avg_ratio = self.get_average_compression_ratio()
        success_rate = self.get_success_rate()
        return (1.0 - avg_ratio) * success_rate

    def reset(self) -> None:
        """清空历史记录。"""
        self._history.clear()

    def __repr__(self) -> str:
        """字符串表示，用于调试。"""
        return (
            f"BudgetTracker(history={self.history_count}/{self._max_history}, "
            f"avg_ratio={self.get_average_compression_ratio():.2f}, "
            f"saved={self.get_total_tokens_saved()}, "
            f"success_rate={self.get_success_rate():.1%})"
        )
