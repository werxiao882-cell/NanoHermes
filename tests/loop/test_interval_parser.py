"""间隔解析器测试。"""

import pytest

from src.loop.interval_parser import (
    IntervalParseError,
    format_interval,
    parse_interval,
)


class TestParseInterval:
    """测试间隔解析。"""

    def test_duration_seconds(self):
        assert parse_interval("60s") == 60
        assert parse_interval("120s") == 120

    def test_duration_minutes(self):
        assert parse_interval("5m") == 300
        assert parse_interval("30m") == 1800
        assert parse_interval("1m") == 60

    def test_duration_hours(self):
        assert parse_interval("1h") == 3600
        assert parse_interval("2h") == 7200

    def test_duration_days(self):
        assert parse_interval("1d") == 86400

    def test_natural_language_minutes(self):
        assert parse_interval("every 5 minutes") == 300
        assert parse_interval("every 1 minute") == 60
        assert parse_interval("every 30 minutes") == 1800

    def test_natural_language_hours(self):
        assert parse_interval("every 2 hours") == 7200
        assert parse_interval("every 1 hour") == 3600

    def test_natural_language_days(self):
        assert parse_interval("every 1 day") == 86400

    def test_natural_language_seconds(self):
        """秒级间隔会被提升到最小 60 秒。"""
        assert parse_interval("every 30 seconds") == 60  # 提升到最小间隔

    def test_cron_step(self):
        assert parse_interval("*/5 * * * *") == 300
        assert parse_interval("*/10 * * * *") == 600
        assert parse_interval("*/15 * * * *") == 900

    def test_invalid_format(self):
        with pytest.raises(IntervalParseError):
            parse_interval("invalid")

    def test_invalid_cron(self):
        with pytest.raises(IntervalParseError):
            parse_interval("0 9 * * *")  # 非 step 格式的 cron

    def test_zero_interval(self):
        with pytest.raises(IntervalParseError):
            parse_interval("0s")

    def test_negative_interval(self):
        with pytest.raises(IntervalParseError):
            parse_interval("-5m")

    def test_too_long_interval(self):
        with pytest.raises(IntervalParseError):
            parse_interval("48h")  # 超过 24 小时

    def test_minimum_clamped(self):
        """小于 60 秒的间隔应提升到 60 秒。"""
        assert parse_interval("10s") == 60
        assert parse_interval("30s") == 60
        assert parse_interval("every 30 seconds") == 60

    def test_whitespace_tolerance(self):
        assert parse_interval("  5m  ") == 300
        assert parse_interval("  every 2 hours  ") == 7200


class TestFormatInterval:
    """测试间隔格式化。"""

    def test_format_days(self):
        assert format_interval(86400) == "1d"
        assert format_interval(172800) == "2d"

    def test_format_hours(self):
        assert format_interval(3600) == "1h"
        assert format_interval(7200) == "2h"

    def test_format_minutes(self):
        assert format_interval(60) == "1m"
        assert format_interval(300) == "5m"
        assert format_interval(1800) == "30m"

    def test_format_seconds(self):
        assert format_interval(30) == "30s"
        assert format_interval(90) == "90s"
