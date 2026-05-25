"""ErrorClassifier - API 错误分类器。

将 API 错误分类为：
- auth: 401/403
- billing: 402
- rate_limit: 429
- context_overflow: 上下文溢出
- server_error: 5xx
- network_error: 网络错误
- format_error: 格式错误
- unknown: 未知
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCategory(Enum):
    """错误分类。"""
    AUTH = "auth"
    BILLING = "billing"
    RATE_LIMIT = "rate_limit"
    CONTEXT_OVERFLOW = "context_overflow"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    FORMAT_ERROR = "format_error"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedError:
    """分类后的错误。

    Attributes:
        category: 错误分类。
        message: 错误描述。
        retryable: 是否可重试。
        recovery_hint: 恢复策略提示。
    """
    category: ErrorCategory
    message: str
    retryable: bool = False
    recovery_hint: str = ""


class ErrorClassifier:
    """API 错误分类器。

    根据 HTTP 状态码和错误消息分类 API 错误，
    提供恢复策略建议。
    """

    def classify(self, status_code: int | None, message: str) -> ClassifiedError:
        """分类 API 错误。

        Args:
            status_code: HTTP 状态码。
            message: 错误消息。

        Returns:
            分类后的错误。
        """
        if status_code is None:
            return ClassifiedError(
                category=ErrorCategory.NETWORK_ERROR,
                message=f"网络错误: {message}",
                retryable=True,
                recovery_hint="检查网络连接后重试",
            )

        msg_lower = message.lower()

        if status_code == 401 or status_code == 403:
            return ClassifiedError(
                category=ErrorCategory.AUTH,
                message=f"认证错误 (HTTP {status_code}): {message}",
                retryable=False,
                recovery_hint="检查 API Key 是否有效",
            )

        if status_code == 402:
            return ClassifiedError(
                category=ErrorCategory.BILLING,
                message=f"计费错误 (HTTP {status_code}): {message}",
                retryable=False,
                recovery_hint="检查账户余额或配额",
            )

        if status_code == 429:
            return ClassifiedError(
                category=ErrorCategory.RATE_LIMIT,
                message=f"速率限制 (HTTP {status_code}): {message}",
                retryable=True,
                recovery_hint="等待后重试，或切换备用模型",
            )

        if status_code == 400 and "context" in msg_lower:
            return ClassifiedError(
                category=ErrorCategory.CONTEXT_OVERFLOW,
                message=f"上下文溢出: {message}",
                retryable=False,
                recovery_hint="触发上下文压缩",
            )

        if status_code >= 500:
            return ClassifiedError(
                category=ErrorCategory.SERVER_ERROR,
                message=f"服务器错误 (HTTP {status_code}): {message}",
                retryable=True,
                recovery_hint="等待后重试，或切换备用提供商",
            )

        return ClassifiedError(
            category=ErrorCategory.UNKNOWN,
            message=f"未知错误 (HTTP {status_code}): {message}",
            retryable=False,
        )
