"""工具错误分类器。

设计参考: Claude Code withRetry.ts 中的错误分类体系:
  - isTransientCapacityError() → 429/529 → 重试
  - isStaleConnectionError()   → ECONNRESET/EPIPE → 重连
  - isOAuthTokenRevokedError() → 403 → 刷新 token
  - handleFastModeCooldown()   → 限流 → 降级
"""

from __future__ import annotations

import re
import random
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class RecoveryAction(str, Enum):
    """错误恢复动作枚举。"""
    RECONNECT = "reconnect"
    BACKOFF = "backoff"
    REFRESH_CREDENTIALS = "refresh_credentials"
    FAIL = "fail"


@dataclass
class ErrorClassification:
    """错误分类结果。"""
    is_retryable: bool
    action: RecoveryAction
    delay_ms: int
    reason: str
    extra: dict | None = None


# 1. 连接错误 → reconnect
CONNECTION_PATTERNS = [
    re.compile(r"ECONNRESET", re.IGNORECASE),
    re.compile(r"EPIPE", re.IGNORECASE),
    re.compile(r"Connection (?:refused|reset|timed?out)", re.IGNORECASE),
    re.compile(r"Broken pipe", re.IGNORECASE),
    re.compile(r"Network is unreachable", re.IGNORECASE),
]

# 2. 认证错误 → refresh_credentials
AUTH_PATTERNS = [
    re.compile(r"401", re.IGNORECASE),
    re.compile(r"Unauthorized", re.IGNORECASE),
    re.compile(r"token (?:expired|invalid|revoked)", re.IGNORECASE),
    re.compile(r"Authentication failed", re.IGNORECASE),
    re.compile(r"Invalid API key", re.IGNORECASE),
]

# 3. 限流错误 → backoff
RATE_LIMIT_PATTERNS = [
    re.compile(r"429", re.IGNORECASE),
    re.compile(r"529", re.IGNORECASE),
    re.compile(r"rate ?limit", re.IGNORECASE),
    re.compile(r"too many requests", re.IGNORECASE),
    re.compile(r"overloaded", re.IGNORECASE),
    re.compile(r"capacity exceeded", re.IGNORECASE),
    re.compile(r"Retry-After:\s*(\d+)", re.IGNORECASE),
]

# 4. 不可重试错误 → fail
NON_RETRYABLE_TYPES = {
    ValueError, TypeError, AssertionError,
    FileNotFoundError, PermissionError, IsADirectoryError,
    KeyError, AttributeError, SyntaxError,
}

BASE_DELAY_MS = 500
MAX_DELAY_MS = 60_000
MAX_RETRIES_DEFAULT = 3
JITTER_RATIO = 0.5


class ToolErrorClassifier:
    """工具执行错误分类器。"""

    def __init__(
        self,
        base_delay_ms: int = BASE_DELAY_MS,
        max_delay_ms: int = MAX_DELAY_MS,
        max_retries: int = MAX_RETRIES_DEFAULT,
    ):
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.max_retries = max_retries

    def classify(
        self,
        error: Exception,
        attempt: int = 1,
        response_headers: dict | None = None,
    ) -> ErrorClassification:
        """将错误分类为可重试或不可重试。"""
        error_str = str(error)
        error_type = type(error)

        # 步骤 1: 不可重试的工具逻辑错误
        if isinstance(error, tuple(NON_RETRYABLE_TYPES)):
            return ErrorClassification(
                is_retryable=False,
                action=RecoveryAction.FAIL,
                delay_ms=0,
                reason=f"不可重试的工具逻辑错误: {error_type.__name__}",
            )

        # 步骤 2: 连接错误 → reconnect
        for pattern in CONNECTION_PATTERNS:
            if pattern.search(error_str):
                delay = self._calculate_delay(attempt, multiplier=1.0)
                return ErrorClassification(
                    is_retryable=True,
                    action=RecoveryAction.RECONNECT,
                    delay_ms=delay,
                    reason=f"连接错误，建议重连",
                )

        # 步骤 3: 认证错误 → refresh_credentials
        for pattern in AUTH_PATTERNS:
            if pattern.search(error_str):
                return ErrorClassification(
                    is_retryable=True,
                    action=RecoveryAction.REFRESH_CREDENTIALS,
                    delay_ms=self.base_delay_ms,
                    reason="认证错误，建议刷新凭证",
                )

        # 步骤 4: 限流错误 → backoff
        for pattern in RATE_LIMIT_PATTERNS:
            match = pattern.search(error_str)
            if match:
                retry_after = self._extract_retry_after(response_headers, match)
                delay = retry_after or self._calculate_delay(attempt, multiplier=2.0)
                return ErrorClassification(
                    is_retryable=True,
                    action=RecoveryAction.BACKOFF,
                    delay_ms=delay,
                    reason="限流错误，建议退避",
                    extra={"retry_after": retry_after} if retry_after else None,
                )

        # 步骤 5: 未知错误 → 保守视为不可重试
        return ErrorClassification(
            is_retryable=False,
            action=RecoveryAction.FAIL,
            delay_ms=0,
            reason=f"未知错误类型: {error_type.__name__}: {error_str}",
        )

    def should_retry(
        self,
        error: Exception,
        attempt: int,
        tool_name: str,
        retryable_tools: set[str] | None = None,
    ) -> bool:
        """判断是否应该重试。"""
        if retryable_tools and tool_name not in retryable_tools:
            return False
        if attempt > self.max_retries:
            return False
        classification = self.classify(error, attempt)
        return classification.is_retryable

    def get_retry_info(
        self, error: Exception, attempt: int
    ) -> ErrorClassification | None:
        """获取重试信息。"""
        classification = self.classify(error, attempt)
        if not classification.is_retryable:
            return None
        return classification

    def _calculate_delay(
        self, attempt: int, multiplier: float = 1.0
    ) -> int:
        """计算指数退避延迟 + 随机抖动。"""
        base = self.base_delay_ms * (2 ** attempt) * multiplier
        jitter = base * JITTER_RATIO * (random.random() - 0.5) * 2
        delay = int(base + jitter)
        return min(delay, self.max_delay_ms)

    def _extract_retry_after(
        self, headers: dict | None, pattern_match: re.Match | None
    ) -> int | None:
        """提取 Retry-After 值。"""
        if headers:
            retry_after = headers.get("Retry-After")
            if retry_after:
                try:
                    return int(retry_after) * 1000
                except ValueError:
                    pass
        if pattern_match and pattern_match.lastindex:
            try:
                return int(pattern_match.group(1)) * 1000
            except (ValueError, IndexError):
                pass
        return None
