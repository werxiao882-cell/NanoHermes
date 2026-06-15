"""预算追踪器单元测试。

覆盖场景：
- 压缩记录追踪
- 环形缓冲区容量限制
- 统计方法（平均压缩比、总节省 token、成功率）
- 边界条件
"""

import pytest

from src.compression.budget_tracker import BudgetTracker, CompressionRecord


class TestBudgetTrackerInit:
    """测试预算追踪器初始化。"""

    def test_default_max_history(self):
        """默认最大历史记录数为 100。"""
        tracker = BudgetTracker()
        assert tracker._max_history == 100

    def test_custom_max_history(self):
        """自定义最大历史记录数。"""
        tracker = BudgetTracker(max_history=50)
        assert tracker._max_history == 50

    def test_initial_history_count(self):
        """初始历史记录数为 0。"""
        tracker = BudgetTracker()
        assert tracker.history_count == 0


class TestBudgetTrackerTracking:
    """测试压缩记录追踪。"""

    def test_track_compression_success(self):
        """记录成功的压缩事件。"""
        tracker = BudgetTracker()
        record = tracker.track_compression(
            before_tokens=1000,
            after_tokens=600,
            success=True,
        )

        assert isinstance(record, CompressionRecord)
        assert record.before_tokens == 1000
        assert record.after_tokens == 600
        assert record.saved_tokens == 400
        assert record.compression_ratio == 0.6
        assert record.success is True
        assert tracker.history_count == 1

    def test_track_compression_failure(self):
        """记录失败的压缩事件。"""
        tracker = BudgetTracker()
        record = tracker.track_compression(
            before_tokens=1000,
            after_tokens=1000,
            success=False,
        )

        assert record.success is False
        assert record.saved_tokens == 0
        assert tracker.history_count == 1

    def test_track_multiple_compressions(self):
        """记录多次压缩事件。"""
        tracker = BudgetTracker()
        tracker.track_compression(1000, 600, success=True)
        tracker.track_compression(800, 500, success=True)
        tracker.track_compression(1200, 900, success=False)

        assert tracker.history_count == 3


class TestBudgetTrackerRingBuffer:
    """测试环形缓冲区容量限制。"""

    def test_ring_buffer_capacity_limit(self):
        """超过容量限制时自动淘汰旧记录。"""
        tracker = BudgetTracker(max_history=3)

        tracker.track_compression(1000, 600, success=True)
        tracker.track_compression(800, 500, success=True)
        tracker.track_compression(1200, 900, success=True)
        assert tracker.history_count == 3

        # 第 4 条记录会淘汰第 1 条
        tracker.track_compression(1500, 1000, success=True)
        assert tracker.history_count == 3

        # 验证最旧的记录被淘汰
        history = tracker.get_history()
        assert len(history) == 3
        # 最新的在前，所以第一条应该是 1500
        assert history[0].before_tokens == 1500

    def test_ring_buffer_auto_eviction(self):
        """自动淘汰旧数据。"""
        tracker = BudgetTracker(max_history=2)

        tracker.track_compression(100, 50, success=True)
        tracker.track_compression(200, 100, success=True)
        tracker.track_compression(300, 150, success=True)

        history = tracker.get_history()
        assert len(history) == 2
        # 最新的在前
        assert history[0].before_tokens == 300
        assert history[1].before_tokens == 200


class TestBudgetTrackerStatistics:
    """测试统计方法。"""

    def test_average_compression_ratio(self):
        """计算平均压缩比。"""
        tracker = BudgetTracker()
        tracker.track_compression(1000, 500, success=True)  # ratio = 0.5
        tracker.track_compression(1000, 600, success=True)  # ratio = 0.6
        tracker.track_compression(1000, 700, success=True)  # ratio = 0.7

        avg_ratio = tracker.get_average_compression_ratio()
        assert abs(avg_ratio - 0.6) < 0.01

    def test_average_compression_ratio_no_history(self):
        """无历史记录时返回 1.0。"""
        tracker = BudgetTracker()
        assert tracker.get_average_compression_ratio() == 1.0

    def test_average_compression_ratio_only_failures(self):
        """只有失败记录时返回 1.0。"""
        tracker = BudgetTracker()
        tracker.track_compression(1000, 1000, success=False)
        tracker.track_compression(1000, 1000, success=False)

        assert tracker.get_average_compression_ratio() == 1.0

    def test_total_tokens_saved(self):
        """计算总节省 token 数。"""
        tracker = BudgetTracker()
        tracker.track_compression(1000, 600, success=True)  # saved = 400
        tracker.track_compression(800, 500, success=True)   # saved = 300
        tracker.track_compression(1200, 900, success=False) # saved = 0 (失败)

        total_saved = tracker.get_total_tokens_saved()
        assert total_saved == 700

    def test_total_tokens_saved_no_history(self):
        """无历史记录时返回 0。"""
        tracker = BudgetTracker()
        assert tracker.get_total_tokens_saved() == 0

    def test_success_rate(self):
        """计算压缩成功率。"""
        tracker = BudgetTracker()
        tracker.track_compression(1000, 600, success=True)
        tracker.track_compression(800, 500, success=True)
        tracker.track_compression(1200, 900, success=False)
        tracker.track_compression(1500, 1000, success=True)

        success_rate = tracker.get_success_rate()
        assert abs(success_rate - 0.75) < 0.01

    def test_success_rate_no_history(self):
        """无历史记录时返回 1.0。"""
        tracker = BudgetTracker()
        assert tracker.get_success_rate() == 1.0

    def test_success_rate_all_failures(self):
        """全部失败时返回 0.0。"""
        tracker = BudgetTracker()
        tracker.track_compression(1000, 1000, success=False)
        tracker.track_compression(800, 800, success=False)

        assert tracker.get_success_rate() == 0.0


class TestBudgetTrackerHistory:
    """测试历史记录查询。"""

    def test_get_history_all(self):
        """获取全部历史记录。"""
        tracker = BudgetTracker()
        tracker.track_compression(1000, 600, success=True)
        tracker.track_compression(800, 500, success=True)

        history = tracker.get_history()
        assert len(history) == 2

    def test_get_history_with_limit(self):
        """获取最近 N 条记录。"""
        tracker = BudgetTracker()
        tracker.track_compression(100, 50, success=True)
        tracker.track_compression(200, 100, success=True)
        tracker.track_compression(300, 150, success=True)

        history = tracker.get_history(limit=2)
        assert len(history) == 2
        # 最新的在前
        assert history[0].before_tokens == 300
        assert history[1].before_tokens == 200

    def test_get_history_order(self):
        """历史记录按时间倒序排列（最新的在前）。"""
        tracker = BudgetTracker()
        tracker.track_compression(100, 50, success=True)
        tracker.track_compression(200, 100, success=True)
        tracker.track_compression(300, 150, success=True)

        history = tracker.get_history()
        assert history[0].before_tokens == 300
        assert history[1].before_tokens == 200
        assert history[2].before_tokens == 100


class TestBudgetTrackerCompressionEfficiency:
    """测试压缩效率计算。"""

    def test_compression_efficiency(self):
        """计算压缩效率。"""
        tracker = BudgetTracker()
        # ratio = 0.6, success_rate = 1.0
        # efficiency = (1 - 0.6) * 1.0 = 0.4
        tracker.track_compression(1000, 600, success=True)

        efficiency = tracker.get_compression_efficiency()
        assert abs(efficiency - 0.4) < 0.01

    def test_compression_efficiency_with_failures(self):
        """考虑失败率的压缩效率。"""
        tracker = BudgetTracker()
        # 平均 ratio = 0.6, success_rate = 0.5
        # efficiency = (1 - 0.6) * 0.5 = 0.2
        tracker.track_compression(1000, 600, success=True)
        tracker.track_compression(1000, 1000, success=False)

        efficiency = tracker.get_compression_efficiency()
        assert abs(efficiency - 0.2) < 0.01

    def test_compression_efficiency_no_history(self):
        """无历史记录时返回 0.0。"""
        tracker = BudgetTracker()
        # avg_ratio = 1.0, success_rate = 1.0
        # efficiency = (1 - 1.0) * 1.0 = 0.0
        efficiency = tracker.get_compression_efficiency()
        assert efficiency == 0.0


class TestBudgetTrackerReset:
    """测试预算追踪器重置。"""

    def test_reset_clears_history(self):
        """重置清空历史记录。"""
        tracker = BudgetTracker()
        tracker.track_compression(1000, 600, success=True)
        tracker.track_compression(800, 500, success=True)
        assert tracker.history_count == 2

        tracker.reset()
        assert tracker.history_count == 0

    def test_reset_clears_statistics(self):
        """重置后统计数据归零。"""
        tracker = BudgetTracker()
        tracker.track_compression(1000, 600, success=True)

        tracker.reset()
        assert tracker.get_average_compression_ratio() == 1.0
        assert tracker.get_total_tokens_saved() == 0
        assert tracker.get_success_rate() == 1.0


class TestBudgetTrackerEdgeCases:
    """测试预算追踪器边界条件。"""

    def test_zero_before_tokens(self):
        """压缩前 token 数为 0。"""
        tracker = BudgetTracker()
        record = tracker.track_compression(0, 0, success=True)

        assert record.compression_ratio == 1.0
        assert record.saved_tokens == 0

    def test_negative_saved_tokens_clamped(self):
        """节省 token 数不会为负。"""
        tracker = BudgetTracker()
        # after > before 的异常情况
        record = tracker.track_compression(100, 200, success=True)

        assert record.saved_tokens == 0

    def test_repr(self):
        """字符串表示用于调试。"""
        tracker = BudgetTracker(max_history=100)
        tracker.track_compression(1000, 600, success=True)

        repr_str = repr(tracker)
        assert "BudgetTracker" in repr_str
        assert "1/100" in repr_str
