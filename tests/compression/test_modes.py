"""压缩模式单元测试。

覆盖场景：
- Reactive 模式触发条件
- Micro 模式触发条件
- Snip 模式触发条件
- 模式工厂函数
- 边界条件
"""

import pytest

from src.compression.modes import (
    CompressionMode,
    ReactiveMode,
    MicroMode,
    SnipMode,
    create_mode,
)


class TestCompressionModeEnum:
    """测试压缩模式枚举。"""

    def test_reactive_mode_value(self):
        """Reactive 模式值。"""
        assert CompressionMode.REACTIVE.value == "reactive"

    def test_micro_mode_value(self):
        """Micro 模式值。"""
        assert CompressionMode.MICRO.value == "micro"

    def test_snip_mode_value(self):
        """Snip 模式值。"""
        assert CompressionMode.SNIP.value == "snip"


class TestReactiveMode:
    """测试 Reactive 压缩模式。"""

    def test_default_threshold(self):
        """默认阈值为 0.5。"""
        mode = ReactiveMode()
        assert mode.threshold == 0.5

    def test_custom_threshold(self):
        """自定义阈值。"""
        mode = ReactiveMode(threshold=0.8)
        assert mode.threshold == 0.8

    def test_invalid_threshold_too_low(self):
        """阈值过低抛出异常。"""
        with pytest.raises(ValueError, match="threshold must be between"):
            ReactiveMode(threshold=-0.1)

    def test_invalid_threshold_too_high(self):
        """阈值过高抛出异常。"""
        with pytest.raises(ValueError, match="threshold must be between"):
            ReactiveMode(threshold=1.5)

    def test_should_compress_below_threshold(self):
        """未达到阈值不触发。"""
        mode = ReactiveMode(threshold=0.5)
        result = mode.should_compress(
            messages=[],
            current_tokens=400,
            max_tokens=1000,
        )
        assert result is False

    def test_should_compress_at_threshold(self):
        """达到阈值触发。"""
        mode = ReactiveMode(threshold=0.5)
        result = mode.should_compress(
            messages=[],
            current_tokens=500,
            max_tokens=1000,
        )
        assert result is True

    def test_should_compress_above_threshold(self):
        """超过阈值触发。"""
        mode = ReactiveMode(threshold=0.5)
        result = mode.should_compress(
            messages=[],
            current_tokens=600,
            max_tokens=1000,
        )
        assert result is True

    def test_should_compress_no_tokens(self):
        """缺少 token 信息不触发。"""
        mode = ReactiveMode(threshold=0.5)
        result = mode.should_compress(messages=[])
        assert result is False

    def test_should_compress_zero_max_tokens(self):
        """最大 token 数为 0 不触发。"""
        mode = ReactiveMode(threshold=0.5)
        result = mode.should_compress(
            messages=[],
            current_tokens=500,
            max_tokens=0,
        )
        assert result is False

    def test_mode_name(self):
        """模式名称。"""
        mode = ReactiveMode()
        assert mode.mode_name == "reactive"


class TestMicroMode:
    """测试 Micro 压缩模式。"""

    def test_default_interval(self):
        """默认间隔为 10。"""
        mode = MicroMode()
        assert mode.interval == 10

    def test_custom_interval(self):
        """自定义间隔。"""
        mode = MicroMode(interval=5)
        assert mode.interval == 5

    def test_invalid_interval_zero(self):
        """间隔为 0 抛出异常。"""
        with pytest.raises(ValueError, match="interval must be positive"):
            MicroMode(interval=0)

    def test_invalid_interval_negative(self):
        """间隔为负数抛出异常。"""
        with pytest.raises(ValueError, match="interval must be positive"):
            MicroMode(interval=-5)

    def test_should_compress_at_interval(self):
        """达到间隔触发。"""
        mode = MicroMode(interval=10)
        result = mode.should_compress(messages=[], turn_count=10)
        assert result is True

    def test_should_compress_multiple_of_interval(self):
        """间隔的倍数触发。"""
        mode = MicroMode(interval=5)
        assert mode.should_compress(messages=[], turn_count=5) is True
        assert mode.should_compress(messages=[], turn_count=10) is True
        assert mode.should_compress(messages=[], turn_count=15) is True

    def test_should_compress_not_at_interval(self):
        """未达到间隔不触发。"""
        mode = MicroMode(interval=10)
        assert mode.should_compress(messages=[], turn_count=1) is False
        assert mode.should_compress(messages=[], turn_count=5) is False
        assert mode.should_compress(messages=[], turn_count=9) is False
        assert mode.should_compress(messages=[], turn_count=11) is False

    def test_should_compress_no_turn_count(self):
        """缺少轮次信息不触发。"""
        mode = MicroMode(interval=10)
        result = mode.should_compress(messages=[])
        assert result is False

    def test_should_compress_zero_turn_count(self):
        """轮次为 0 不触发。"""
        mode = MicroMode(interval=10)
        result = mode.should_compress(messages=[], turn_count=0)
        assert result is False

    def test_mode_name(self):
        """模式名称。"""
        mode = MicroMode()
        assert mode.mode_name == "micro"


class TestSnipMode:
    """测试 Snip 压缩模式。"""

    def test_default_patterns(self):
        """默认触发模式。"""
        mode = SnipMode()
        assert len(mode.patterns) > 0
        assert "```" in mode.patterns

    def test_custom_patterns(self):
        """自定义触发模式。"""
        mode = SnipMode(patterns=["ERROR:", "WARNING:"])
        assert len(mode.patterns) == 2
        assert "ERROR:" in mode.patterns
        assert "WARNING:" in mode.patterns

    def test_should_compress_code_block(self):
        """检测到代码块触发。"""
        mode = SnipMode()
        messages = [
            {"role": "user", "content": "Here is the code:\n```python\nprint('hello')\n```"},
        ]
        result = mode.should_compress(messages=messages)
        assert result is True

    def test_should_compress_logs(self):
        """检测到日志触发。"""
        mode = SnipMode()
        messages = [
            {"role": "assistant", "content": "Here are the logs:\n2024-01-01 ERROR: ..."},
        ]
        result = mode.should_compress(messages=messages)
        assert result is True

    def test_should_compress_no_match(self):
        """未检测到特征不触发。"""
        mode = SnipMode()
        messages = [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thanks!"},
        ]
        result = mode.should_compress(messages=messages)
        assert result is False

    def test_should_compress_empty_messages(self):
        """空消息列表不触发。"""
        mode = SnipMode()
        result = mode.should_compress(messages=[])
        assert result is False

    def test_should_compress_recent_messages_only(self):
        """只检查最近 5 条消息。"""
        mode = SnipMode(patterns=["TRIGGER"])
        messages = [
            {"role": "user", "content": "TRIGGER"},  # 第 1 条（不在最近 5 条）
            {"role": "assistant", "content": "OK"},
            {"role": "user", "content": "OK"},
            {"role": "assistant", "content": "OK"},
            {"role": "user", "content": "OK"},
            {"role": "assistant", "content": "OK"},  # 第 6 条（最近 5 条的开始）
        ]
        result = mode.should_compress(messages=messages)
        assert result is False

    def test_should_compress_non_string_content(self):
        """非字符串内容跳过。"""
        mode = SnipMode()
        messages = [
            {"role": "user", "content": 123},  # 非字符串
            {"role": "assistant", "content": "Hello"},
        ]
        result = mode.should_compress(messages=messages)
        assert result is False

    def test_mode_name(self):
        """模式名称。"""
        mode = SnipMode()
        assert mode.mode_name == "snip"


class TestCreateMode:
    """测试模式工厂函数。"""

    def test_create_reactive_mode(self):
        """创建 Reactive 模式。"""
        mode = create_mode("reactive", reactive_threshold=0.7)
        assert isinstance(mode, ReactiveMode)
        assert mode.threshold == 0.7

    def test_create_micro_mode(self):
        """创建 Micro 模式。"""
        mode = create_mode("micro", micro_interval=5)
        assert isinstance(mode, MicroMode)
        assert mode.interval == 5

    def test_create_snip_mode(self):
        """创建 Snip 模式。"""
        mode = create_mode("snip", snip_patterns=["ERROR:"])
        assert isinstance(mode, SnipMode)
        assert "ERROR:" in mode.patterns

    def test_create_mode_case_insensitive(self):
        """模式名称大小写不敏感。"""
        mode1 = create_mode("REACTIVE")
        mode2 = create_mode("Reactive")
        mode3 = create_mode("reactive")

        assert isinstance(mode1, ReactiveMode)
        assert isinstance(mode2, ReactiveMode)
        assert isinstance(mode3, ReactiveMode)

    def test_create_invalid_mode(self):
        """无效模式名称抛出异常。"""
        with pytest.raises(ValueError, match="Invalid compression mode"):
            create_mode("invalid_mode")

    def test_create_mode_with_all_params(self):
        """创建模式时传递所有参数。"""
        mode = create_mode(
            "reactive",
            reactive_threshold=0.8,
            micro_interval=10,
            snip_patterns=["ERROR:"],
        )
        assert isinstance(mode, ReactiveMode)
        assert mode.threshold == 0.8


class TestCompressionModeIntegration:
    """测试压缩模式集成场景。"""

    def test_reactive_mode_full_cycle(self):
        """Reactive 模式完整生命周期。"""
        mode = ReactiveMode(threshold=0.5)

        # 初始状态：token 使用率低
        assert mode.should_compress(messages=[], current_tokens=200, max_tokens=1000) is False

        # 达到阈值
        assert mode.should_compress(messages=[], current_tokens=500, max_tokens=1000) is True

        # 超过阈值
        assert mode.should_compress(messages=[], current_tokens=800, max_tokens=1000) is True

    def test_micro_mode_full_cycle(self):
        """Micro 模式完整生命周期。"""
        mode = MicroMode(interval=3)

        # 轮次 1-2：不触发
        assert mode.should_compress(messages=[], turn_count=1) is False
        assert mode.should_compress(messages=[], turn_count=2) is False

        # 轮次 3：触发
        assert mode.should_compress(messages=[], turn_count=3) is True

        # 轮次 4-5：不触发
        assert mode.should_compress(messages=[], turn_count=4) is False
        assert mode.should_compress(messages=[], turn_count=5) is False

        # 轮次 6：触发
        assert mode.should_compress(messages=[], turn_count=6) is True

    def test_snip_mode_full_cycle(self):
        """Snip 模式完整生命周期。"""
        mode = SnipMode(patterns=["ERROR:", "WARNING:"])

        # 无特征：不触发
        messages1 = [{"role": "user", "content": "Hello"}]
        assert mode.should_compress(messages=messages1) is False

        # 检测到 ERROR：触发
        messages2 = [{"role": "assistant", "content": "ERROR: Something went wrong"}]
        assert mode.should_compress(messages=messages2) is True

        # 检测到 WARNING：触发
        messages3 = [{"role": "assistant", "content": "WARNING: Deprecated API"}]
        assert mode.should_compress(messages=messages3) is True
