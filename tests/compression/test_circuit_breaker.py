"""熔断器单元测试。

覆盖场景：
- 状态转换（CLOSED → OPEN → HALF_OPEN → CLOSED）
- 冷却期机制
- 手动重置
- 边界条件
"""

import time
import pytest

from src.compression.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreakerInit:
    """测试熔断器初始化。"""

    def test_default_state_is_closed(self):
        """默认状态为 CLOSED。"""
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    def test_custom_threshold(self):
        """自定义失败阈值。"""
        cb = CircuitBreaker(failure_threshold=5)
        assert cb._failure_threshold == 5

    def test_custom_cooldown(self):
        """自定义冷却期。"""
        cb = CircuitBreaker(cooldown_seconds=120.0)
        assert cb._cooldown_seconds == 120.0


class TestCircuitBreakerStateTransitions:
    """测试熔断器状态转换。"""

    def test_closed_allows_compression(self):
        """CLOSED 状态允许压缩。"""
        cb = CircuitBreaker()
        assert cb.can_compress() is True

    def test_consecutive_failures_trigger_open(self):
        """连续失败触发熔断。"""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 1

        cb.record_failure()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 2

        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.failure_count == 3

    def test_open_rejects_compression(self):
        """OPEN 状态拒绝压缩。"""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_compress() is False

    def test_cooldown_transitions_to_half_open(self):
        """冷却期后进入 HALF_OPEN 状态。"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # 等待冷却期
        time.sleep(0.15)

        # 检查状态转换
        assert cb.can_compress() is True
        assert cb.state == "HALF_OPEN"

    def test_half_open_allows_compression(self):
        """HALF_OPEN 状态允许压缩。"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)

        assert cb.can_compress() is True
        assert cb.state == "HALF_OPEN"

    def test_half_open_success_transitions_to_closed(self):
        """HALF_OPEN 状态成功则恢复为 CLOSED。"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)

        cb.can_compress()  # 触发状态转换为 HALF_OPEN
        cb.record_success()

        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_half_open_failure_transitions_to_open(self):
        """HALF_OPEN 状态失败则继续 OPEN。"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)

        cb.can_compress()  # 触发状态转换为 HALF_OPEN
        cb.record_failure()

        assert cb.state == "OPEN"


class TestCircuitBreakerReset:
    """测试熔断器重置。"""

    def test_reset_clears_state(self):
        """手动重置清空所有状态。"""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        cb.reset()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    def test_reset_allows_compression(self):
        """重置后允许压缩。"""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.can_compress() is False

        cb.reset()
        assert cb.can_compress() is True


class TestCircuitBreakerEdgeCases:
    """测试熔断器边界条件。"""

    def test_success_in_closed_resets_failure_count(self):
        """CLOSED 状态下成功重置失败计数。"""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0

    def test_last_failure_time_updated(self):
        """失败时更新最后失败时间。"""
        cb = CircuitBreaker()
        assert cb.last_failure_time is None

        cb.record_failure()
        assert cb.last_failure_time is not None
        assert isinstance(cb.last_failure_time, float)

    def test_repr(self):
        """字符串表示用于调试。"""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
        repr_str = repr(cb)
        assert "CircuitBreaker" in repr_str
        assert "CLOSED" in repr_str
        assert "0/3" in repr_str
        assert "60" in repr_str


class TestCircuitBreakerIntegration:
    """测试熔断器集成场景。"""

    def test_full_cycle(self):
        """完整生命周期：CLOSED → OPEN → HALF_OPEN → CLOSED。"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)

        # 初始状态
        assert cb.state == "CLOSED"
        assert cb.can_compress() is True

        # 连续失败触发熔断
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_compress() is False

        # 等待冷却期
        time.sleep(0.15)

        # 进入探测状态
        assert cb.can_compress() is True
        assert cb.state == "HALF_OPEN"

        # 探测成功恢复
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.can_compress() is True

    def test_multiple_cycles(self):
        """多次熔断和恢复。"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.05)

        # 第一次熔断
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        time.sleep(0.1)
        cb.can_compress()
        cb.record_success()
        assert cb.state == "CLOSED"

        # 第二次熔断
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        time.sleep(0.1)
        cb.can_compress()
        cb.record_success()
        assert cb.state == "CLOSED"
