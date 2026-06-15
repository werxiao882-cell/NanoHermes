"""熔断器模式实现。

防止压缩循环，支持三状态转换：CLOSED → OPEN → HALF_OPEN → CLOSED。

设计理由：
- 连续压缩失败时，系统可能进入循环重试，消耗资源且无法恢复
- 熔断器在连续失败后自动"断开"，拒绝后续压缩请求
- 冷却期后进入探测状态，允许单次尝试，成功则恢复，失败则继续熔断
- 这种模式借鉴了电路保险丝的设计理念，保护系统免受级联故障影响
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    """熔断器状态枚举。

    - CLOSED: 正常状态，允许压缩
    - OPEN: 熔断状态，拒绝压缩
    - HALF_OPEN: 探测状态，允许单次尝试
    """
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """熔断器，用于防止压缩循环。

    状态转换规则：
    1. CLOSED → OPEN: 连续失败次数达到 failure_threshold
    2. OPEN → HALF_OPEN: 距离上次失败时间超过 cooldown_seconds
    3. HALF_OPEN → CLOSED: 探测成功
    4. HALF_OPEN → OPEN: 探测失败

    设计理由：
    - failure_threshold 默认 3：连续 3 次失败通常意味着系统性问题，而非偶发故障
    - cooldown_seconds 默认 60：给予系统足够的恢复时间，同时不会让用户等待过久
    - success_threshold 默认 1：单次成功即可证明问题已解决，快速恢复服务
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
        success_threshold: int = 1,
    ):
        """初始化熔断器。

        Args:
            failure_threshold: 连续失败次数阈值，达到后触发熔断。
            cooldown_seconds: 熔断后的冷却期（秒），超过后进入探测状态。
            success_threshold: 探测状态下的成功次数阈值，达到后恢复。
        """
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> str:
        """当前状态（字符串形式）。"""
        return self._state.value

    @property
    def failure_count(self) -> int:
        """当前连续失败次数。"""
        return self._failure_count

    @property
    def last_failure_time(self) -> Optional[float]:
        """最后失败时间（Unix 时间戳）。"""
        return self._last_failure_time

    def can_compress(self) -> bool:
        """判断是否允许压缩。

        状态判断逻辑：
        - CLOSED: 允许
        - OPEN: 检查冷却期，超过则转为 HALF_OPEN 并允许，否则拒绝
        - HALF_OPEN: 允许（探测状态）

        Returns:
            True 表示允许压缩，False 表示拒绝。
        """
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # 检查冷却期
            if self._last_failure_time is None:
                # 异常情况：没有失败时间记录，重置为 CLOSED
                self._state = CircuitState.CLOSED
                return True

            elapsed = time.time() - self._last_failure_time
            if elapsed >= self._cooldown_seconds:
                # 冷却期已过，进入探测状态
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                return True
            else:
                # 仍在冷却期，拒绝压缩
                return False

        if self._state == CircuitState.HALF_OPEN:
            # 探测状态，允许单次尝试
            return True

        # 未知状态，默认拒绝
        return False

    def record_success(self) -> None:
        """记录压缩成功。

        状态转换逻辑：
        - CLOSED: 重置失败计数
        - HALF_OPEN: 增加成功计数，达到阈值后转为 CLOSED
        - OPEN: 不应发生（can_compress 会拒绝），但仍处理
        """
        if self._state == CircuitState.CLOSED:
            # 正常状态，重置失败计数
            self._failure_count = 0

        elif self._state == CircuitState.HALF_OPEN:
            # 探测状态，增加成功计数
            self._success_count += 1
            if self._success_count >= self._success_threshold:
                # 探测成功，恢复为正常状态
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0

        elif self._state == CircuitState.OPEN:
            # 异常情况：OPEN 状态下不应有成功记录
            # 但仍处理，重置为 CLOSED
            self._state = CircuitState.CLOSED
            self._failure_count = 0

    def record_failure(self) -> None:
        """记录压缩失败。

        状态转换逻辑：
        - CLOSED: 增加失败计数，达到阈值后转为 OPEN
        - HALF_OPEN: 探测失败，转为 OPEN
        - OPEN: 更新最后失败时间
        """
        self._last_failure_time = time.time()

        if self._state == CircuitState.CLOSED:
            # 正常状态，增加失败计数
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                # 达到阈值，触发熔断
                self._state = CircuitState.OPEN

        elif self._state == CircuitState.HALF_OPEN:
            # 探测失败，继续熔断
            self._state = CircuitState.OPEN
            self._success_count = 0

        elif self._state == CircuitState.OPEN:
            # 已经是熔断状态，仅更新失败时间
            pass

    def reset(self) -> None:
        """手动重置熔断器。

        将所有状态重置为初始值，恢复到 CLOSED 状态。
        用于管理员手动干预或测试场景。
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None

    def __repr__(self) -> str:
        """字符串表示，用于调试。"""
        return (
            f"CircuitBreaker(state={self.state}, "
            f"failures={self._failure_count}/{self._failure_threshold}, "
            f"cooldown={self._cooldown_seconds}s)"
        )
