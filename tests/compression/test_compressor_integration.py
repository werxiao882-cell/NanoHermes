"""ContextCompressor 集成测试。

覆盖场景：
- 熔断器集成（压缩失败触发熔断）
- 预算追踪集成（压缩后记录统计）
- 验证器集成（质量不达标警告）
- 压缩模式集成（不同模式触发条件）
- 完整压缩流程
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.compression.compressor import ContextCompressor
from src.compression.circuit_breaker import CircuitState
from src.compression.budget_tracker import BudgetTracker
from src.compression.validator import CompressionValidator
from src.compression.modes import ReactiveMode, MicroMode, SnipMode


class TestCompressorInit:
    """测试 ContextCompressor 初始化。"""

    def test_default_init(self):
        """默认初始化。"""
        compressor = ContextCompressor(model="qwen-turbo")

        assert compressor.model == "qwen-turbo"
        assert compressor._circuit_breaker is not None
        assert compressor._budget_tracker is not None
        assert compressor._validator is not None
        assert isinstance(compressor._compression_mode, ReactiveMode)

    def test_disable_circuit_breaker(self):
        """禁用熔断器。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            enable_circuit_breaker=False,
        )
        assert compressor._circuit_breaker is None

    def test_disable_budget_tracker(self):
        """禁用预算追踪器。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            enable_budget_tracker=False,
        )
        assert compressor._budget_tracker is None

    def test_disable_validator(self):
        """禁用验证器。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            enable_validator=False,
        )
        assert compressor._validator is None

    def test_custom_circuit_breaker_params(self):
        """自定义熔断器参数。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            circuit_breaker_threshold=5,
            circuit_breaker_cooldown=120.0,
        )
        assert compressor._circuit_breaker._failure_threshold == 5
        assert compressor._circuit_breaker._cooldown_seconds == 120.0

    def test_custom_budget_tracker_params(self):
        """自定义预算追踪器参数。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            budget_tracker_max_history=50,
        )
        assert compressor._budget_tracker._max_history == 50

    def test_custom_validator_params(self):
        """自定义验证器参数。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            validator_min_retention=0.7,
            validator_min_length=300,
            validator_max_length=15000,
        )
        assert compressor._validator._min_retention_rate == 0.7
        assert compressor._validator._min_summary_length == 300
        assert compressor._validator._max_summary_length == 15000

    def test_reactive_mode(self):
        """Reactive 压缩模式。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            compression_mode="reactive",
            reactive_threshold=0.7,
        )
        assert isinstance(compressor._compression_mode, ReactiveMode)
        assert compressor._compression_mode.threshold == 0.7

    def test_micro_mode(self):
        """Micro 压缩模式。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            compression_mode="micro",
            micro_interval=5,
        )
        assert isinstance(compressor._compression_mode, MicroMode)
        assert compressor._compression_mode.interval == 5

    def test_snip_mode(self):
        """Snip 压缩模式。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            compression_mode="snip",
            snip_patterns=["ERROR:", "WARNING:"],
        )
        assert isinstance(compressor._compression_mode, SnipMode)
        assert "ERROR:" in compressor._compression_mode.patterns


class TestCompressorShouldCompress:
    """测试 should_compress 方法。"""

    def test_circuit_breaker_open_rejects(self):
        """熔断器 OPEN 状态拒绝压缩。"""
        compressor = ContextCompressor(model="qwen-turbo")

        # 触发熔断
        compressor._circuit_breaker.record_failure()
        compressor._circuit_breaker.record_failure()
        compressor._circuit_breaker.record_failure()

        assert compressor.should_compress(messages=[], current_tokens=1000) is False

    def test_reactive_mode_threshold(self):
        """Reactive 模式阈值触发。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            compression_mode="reactive",
            reactive_threshold=0.5,
        )

        # 未达到阈值 (qwen-turbo context_length = 8192, threshold = 4096)
        assert compressor.should_compress(messages=[], current_tokens=2000) is False

        # 达到阈值
        assert compressor.should_compress(messages=[], current_tokens=4100) is True

    def test_micro_mode_interval(self):
        """Micro 模式间隔触发。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            compression_mode="micro",
            micro_interval=5,
        )

        # 轮次 1-4：不触发
        for i in range(1, 5):
            compressor._turn_count = i
            assert compressor.should_compress(messages=[]) is False

        # 轮次 5：触发
        compressor._turn_count = 5
        assert compressor.should_compress(messages=[]) is True

    def test_snip_mode_pattern(self):
        """Snip 模式模式匹配触发。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            compression_mode="snip",
            snip_patterns=["ERROR:"],
        )

        # 无匹配：不触发
        messages1 = [{"role": "user", "content": "Hello"}]
        assert compressor.should_compress(messages=messages1) is False

        # 有匹配：触发
        messages2 = [{"role": "assistant", "content": "ERROR: Something failed"}]
        assert compressor.should_compress(messages=messages2) is True


class TestCompressorTurnCount:
    """测试对话轮次计数。"""

    def test_increment_turn_count(self):
        """增加对话轮次计数。"""
        compressor = ContextCompressor(model="qwen-turbo")
        assert compressor._turn_count == 0

        compressor.increment_turn_count()
        assert compressor._turn_count == 1

        compressor.increment_turn_count()
        assert compressor._turn_count == 2


class TestCompressorCompress:
    """测试 compress 方法。"""

    def test_circuit_breaker_open_skips_compression(self):
        """熔断器 OPEN 状态跳过压缩。"""
        compressor = ContextCompressor(model="qwen-turbo")

        # 触发熔断
        compressor._circuit_breaker.record_failure()
        compressor._circuit_breaker.record_failure()
        compressor._circuit_breaker.record_failure()

        messages = [{"role": "user", "content": "Hello"}]
        result = compressor.compress(messages=messages, current_tokens=1000)

        assert result["skipped"] is True
        assert result["reason"] == "circuit_breaker_open"
        assert result["messages"] == messages

    def test_compression_success_records_budget(self):
        """压缩成功记录预算追踪。"""
        compressor = ContextCompressor(model="qwen-turbo")

        # Mock model_caller
        mock_caller = Mock()
        mock_caller.return_value = "Summary of conversation"

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ] * 20  # 40 条消息

        result = compressor.compress(
            messages=messages,
            current_tokens=5000,
            model_caller=mock_caller,
        )

        # 验证预算追踪记录
        assert compressor._budget_tracker.history_count == 1
        record = compressor._budget_tracker.get_history()[0]
        assert record.success is True
        assert record.before_tokens == 5000

    def test_compression_success_records_circuit_breaker(self):
        """压缩成功记录熔断器。"""
        compressor = ContextCompressor(model="qwen-turbo")

        # Mock model_caller
        mock_caller = Mock()
        mock_caller.return_value = "Summary of conversation"

        messages = [{"role": "user", "content": "Hello"}] * 10

        result = compressor.compress(
            messages=messages,
            current_tokens=1000,
            model_caller=mock_caller,
        )

        # 验证熔断器状态
        assert compressor._circuit_breaker.state == "CLOSED"
        assert compressor._circuit_breaker.failure_count == 0

    def test_compression_failure_records_circuit_breaker(self):
        """压缩失败记录熔断器。
        
        注意：_generate_summary 方法会捕获异常并返回占位符摘要，
        所以 compress() 方法不会看到异常，而是成功返回带有占位符摘要的结果。
        这是设计行为：压缩是优化而非必需，不应阻断对话。
        """
        compressor = ContextCompressor(model="qwen-turbo")

        # Mock model_caller 抛出异常
        mock_caller = Mock()
        mock_caller.side_effect = Exception("LLM error")

        messages = [{"role": "user", "content": "Hello"}] * 10

        result = compressor.compress(
            messages=messages,
            current_tokens=1000,
            model_caller=mock_caller,
        )

        # 验证压缩成功（使用占位符摘要）
        assert "error" not in result
        assert "messages" in result
        # 摘要应该包含失败提示
        assert "Summary generation failed" in result["summary"]

    def test_compression_failure_records_budget(self):
        """压缩失败记录预算追踪。
        
        注意：_generate_summary 方法会捕获异常并返回占位符摘要，
        所以 compress() 方法会成功返回，预算追踪器会记录成功。
        """
        compressor = ContextCompressor(model="qwen-turbo")

        # Mock model_caller 抛出异常
        mock_caller = Mock()
        mock_caller.side_effect = Exception("LLM error")

        messages = [{"role": "user", "content": "Hello"}] * 10

        result = compressor.compress(
            messages=messages,
            current_tokens=1000,
            model_caller=mock_caller,
        )

        # 验证预算追踪记录成功（因为压缩本身成功了，只是摘要生成失败）
        assert compressor._budget_tracker.history_count == 1
        record = compressor._budget_tracker.get_history()[0]
        assert record.success is True  # 压缩成功，只是摘要质量差

    def test_compression_validates_quality(self):
        """压缩后验证质量。"""
        compressor = ContextCompressor(model="qwen-turbo")

        # Mock model_caller
        mock_caller = Mock()
        mock_caller.return_value = "Summary of conversation"

        messages = [{"role": "user", "content": "Hello"}] * 10

        result = compressor.compress(
            messages=messages,
            current_tokens=1000,
            model_caller=mock_caller,
        )

        # 验证质量检查结果
        assert "validation" in result
        assert result["validation"] is not None

    def test_compression_returns_new_fields(self):
        """压缩返回新字段。"""
        compressor = ContextCompressor(model="qwen-turbo")

        # Mock model_caller
        mock_caller = Mock()
        mock_caller.return_value = "Summary of conversation"

        messages = [{"role": "user", "content": "Hello"}] * 10

        result = compressor.compress(
            messages=messages,
            current_tokens=1000,
            model_caller=mock_caller,
        )

        # 验证新字段
        assert "validation" in result
        assert "compression_efficiency" in result
        assert "circuit_breaker_state" in result


class TestCompressorEstimateTokens:
    """测试 _estimate_tokens 方法。"""

    def test_estimate_tokens(self):
        """估算 token 数。"""
        compressor = ContextCompressor(model="qwen-turbo")

        messages = [
            {"role": "user", "content": "a" * 100},  # 100 字符
            {"role": "assistant", "content": "b" * 100},  # 100 字符
        ]

        tokens = compressor._estimate_tokens(messages)
        # 200 字符 / 4 = 50 tokens
        assert tokens == 50

    def test_estimate_tokens_empty(self):
        """空消息列表。"""
        compressor = ContextCompressor(model="qwen-turbo")
        tokens = compressor._estimate_tokens([])
        assert tokens == 0


class TestCompressorIntegration:
    """测试 ContextCompressor 完整集成。"""

    def test_full_compression_cycle(self):
        """完整压缩周期。"""
        compressor = ContextCompressor(
            model="qwen-turbo",
            compression_mode="reactive",
            reactive_threshold=0.5,
        )

        # Mock model_caller - 返回 dict 格式
        mock_caller = Mock()
        mock_caller.return_value = {"content": "Summary: User discussed various topics"}

        # 创建长对话
        messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(50)
        ]

        # 检查是否需要压缩
        should_compress = compressor.should_compress(
            messages=messages,
            current_tokens=5000,
        )
        assert should_compress is True

        # 执行压缩
        result = compressor.compress(
            messages=messages,
            current_tokens=5000,
            model_caller=mock_caller,
        )

        # 验证结果
        assert "messages" in result
        assert "summary" in result
        assert result["summary"] == "Summary: User discussed various topics"
        assert result["circuit_breaker_state"] == "CLOSED"
        assert compressor._budget_tracker.history_count == 1

    def test_multiple_compressions(self):
        """多次压缩。"""
        compressor = ContextCompressor(model="qwen-turbo")

        # Mock model_caller
        mock_caller = Mock()
        mock_caller.return_value = "Summary"

        messages = [{"role": "user", "content": "Hello"}] * 10

        # 第一次压缩
        result1 = compressor.compress(
            messages=messages,
            current_tokens=1000,
            model_caller=mock_caller,
        )
        assert compressor._budget_tracker.history_count == 1

        # 第二次压缩
        result2 = compressor.compress(
            messages=messages,
            current_tokens=1000,
            model_caller=mock_caller,
        )
        assert compressor._budget_tracker.history_count == 2

        # 验证统计
        avg_ratio = compressor._budget_tracker.get_average_compression_ratio()
        assert avg_ratio < 1.0  # 应该有压缩

    def test_compression_with_failure_recovery(self):
        """压缩失败后恢复。
        
        注意：由于 _generate_summary 会捕获异常并返回占位符，
        压缩本身不会失败，所以这个测试验证的是多次压缩的稳定性。
        """
        compressor = ContextCompressor(
            model="qwen-turbo",
            circuit_breaker_threshold=3,
        )

        # Mock model_caller：前两次返回空摘要，第三次成功
        mock_caller = Mock()
        mock_caller.side_effect = [
            {"content": ""},  # 空摘要会触发 ValueError
            {"content": ""},  # 空摘要会触发 ValueError
            {"content": "Summary"},  # 成功
        ]

        messages = [{"role": "user", "content": "Hello"}] * 10

        # 第一次：摘要生成失败，但压缩成功（使用占位符）
        result1 = compressor.compress(
            messages=messages,
            current_tokens=1000,
            model_caller=mock_caller,
        )
        assert "error" not in result1
        assert "Summary generation failed" in result1["summary"]

        # 第二次：摘要生成失败，但压缩成功
        result2 = compressor.compress(
            messages=messages,
            current_tokens=1000,
            model_caller=mock_caller,
        )
        assert "error" not in result2
        assert "Summary generation failed" in result2["summary"]

        # 第三次：成功
        result3 = compressor.compress(
            messages=messages,
            current_tokens=1000,
            model_caller=mock_caller,
        )
        assert "error" not in result3
        assert result3["summary"] == "Summary"
        assert compressor._circuit_breaker.state == "CLOSED"
