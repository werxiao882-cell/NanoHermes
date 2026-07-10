"""间隔表达式解析器。

支持多种间隔格式：
- 持续时间： "30s", "5m", "2h", "1d"
- 自然语言： "every 5 minutes", "every 2 hours", "every 30 seconds"
- Cron 表达式： "*/5 * * * *"（5 字段，转换为等效秒数）

设计理由：
- 复用 cronjob 工具的 _parse_schedule() 思路，但独立实现以避免工具耦合
- 统一转换为秒数，简化调度逻辑
- 秒单位自动向上取整到分钟（cron 最小粒度限制）
"""

from __future__ import annotations

import re
from typing import Optional

from src.loop import MAX_INTERVAL_SECONDS, MIN_INTERVAL_SECONDS


class IntervalParseError(Exception):
    """间隔解析错误。"""
    pass


def parse_interval(expression: str) -> int:
    """解析间隔表达式为秒数。

    支持格式：
    - 持续时间： "30s", "5m", "2h", "1d"
    - 自然语言： "every 5 minutes", "every 2 hours", "every 30 seconds", "every 1 day"
    - Cron 表达式： "*/5 * * * *"（仅支持 step 格式，如 */N）

    Args:
        expression: 间隔表达式字符串。

    Returns:
        间隔秒数（已验证在 MIN_INTERVAL_SECONDS 和 MAX_INTERVAL_SECONDS 之间）。

    Raises:
        IntervalParseError: 当表达式无法解析或超出有效范围时。
    """
    expression = expression.strip().lower()

    # 尝试各种解析策略
    seconds = _try_duration(expression)
    if seconds is not None:
        return _validate_interval(seconds)

    seconds = _try_natural_language(expression)
    if seconds is not None:
        return _validate_interval(seconds)

    seconds = _try_cron(expression)
    if seconds is not None:
        return _validate_interval(seconds)

    raise IntervalParseError(
        f"无法解析间隔表达式: '{expression}'\n"
        f"支持的格式: '5m', '2h', 'every 30 minutes', '*/5 * * * *'"
    )


def _try_duration(expression: str) -> Optional[int]:
    """尝试解析持续时间格式（如 "5m", "2h"）。"""
    match = re.match(r"^(\d+)\s*([smhd])$", expression)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2)

    unit_seconds = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }

    return value * unit_seconds[unit]


def _try_natural_language(expression: str) -> Optional[int]:
    """尝试解析自然语言格式（如 "every 5 minutes"）。"""
    # 匹配 "every <number> <unit>" 或 "every <unit>"
    patterns = [
        r"^every\s+(\d+)\s+(seconds?|minutes?|hours?|days?)$",
        r"^every\s+(second|minute|hour|day)$",
    ]

    for pattern in patterns:
        match = re.match(pattern, expression)
        if not match:
            continue

        if match.group(2) in ("second", "seconds", "minute", "minutes", "hours", "hour", "days", "day"):
            unit = match.group(2).lower()
            # 单数形式
            if match.group(1).isdigit():
                value = int(match.group(1))
            else:
                value = 1

            # 统一单位
            if unit.startswith("second"):
                return value
            elif unit.startswith("minute"):
                return value * 60
            elif unit.startswith("hour"):
                return value * 3600
            elif unit.startswith("day"):
                return value * 86400

    return None


def _try_cron(expression: str) -> Optional[int]:
    """尝试解析 Cron 表达式（仅支持 step 格式如 */N）。"""
    parts = expression.split()
    if len(parts) != 5:
        return None

    # 只解析分钟字段的 step（*/N）
    minute_field = parts[0]
    step_match = re.match(r"^\*/(\d+)$", minute_field)
    if not step_match:
        return None

    minutes = int(step_match.group(1))
    return minutes * 60


def _validate_interval(seconds: int) -> int:
    """验证间隔在有效范围内。

    设计理由：
    - 最小 60 秒：防止 API 滥用和过快循环
    - 最大 86400 秒（24 小时）：防止忘记停止循环
    - 秒向上取整到 60 的倍数（cron 最小粒度是分钟）
    """
    if seconds <= 0:
        raise IntervalParseError("间隔必须大于 0")

    # 向上取整到分钟
    if seconds < MIN_INTERVAL_SECONDS:
        seconds = MIN_INTERVAL_SECONDS

    if seconds > MAX_INTERVAL_SECONDS:
        raise IntervalParseError(
            f"间隔过长（{seconds} 秒），最大允许 {MAX_INTERVAL_SECONDS} 秒（24 小时）"
        )

    return seconds


def format_interval(seconds: int) -> str:
    """将秒数格式化为人类可读的间隔字符串。

    Args:
        seconds: 间隔秒数。

    Returns:
        格式化的间隔字符串（如 "5m", "2h", "1d"）。
    """
    if seconds >= 86400 and seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    elif seconds >= 3600 and seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    elif seconds >= 60 and seconds % 60 == 0:
        return f"{seconds // 60}m"
    else:
        return f"{seconds}s"
