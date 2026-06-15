"""ContextCompressor 上下文压缩引擎单元测试。"""

import pytest
from src.compression.compressor import (
    ContextCompressor,
    SUMMARY_PREFIX,
    MIN_SUMMARY_TOKENS,
    SUMMARY_TOKENS_CEILING,
    SUMMARY_RATIO,
    CHARS_PER_TOKEN,
    PROTECT_FIRST_N,
)


@pytest.fixture
def compressor():
    """创建 ContextCompressor 实例。"""
    return ContextCompressor(model="gpt-4-turbo")


@pytest.fixture
def long_messages():
    """创建长对话消息列表。"""
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for i in range(100):
        messages.append({"role": "user", "content": f"User message {i}" * 10})
        messages.append({"role": "assistant", "content": f"Assistant response {i}" * 10})
    return messages


class TestContextCompressorInit:
    """测试 ContextCompressor 初始化。"""

    def test_default_parameters(self):
        """测试默认参数。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        assert compressor.threshold_percent == 0.50
        assert compressor.protect_first_n == PROTECT_FIRST_N
        assert compressor.protect_last_n == 20
        assert compressor.summary_target_ratio == SUMMARY_RATIO

    def test_custom_parameters(self):
        """测试自定义参数。"""
        compressor = ContextCompressor(
            model="gpt-4-turbo",
            threshold_percent=0.60,
            protect_first_n=5,
            protect_last_n=30,
        )
        assert compressor.threshold_percent == 0.60
        assert compressor.protect_first_n == 5
        assert compressor.protect_last_n == 30


class TestCompress:
    """测试 compress 方法。"""

    def test_compress_long_conversation(self, compressor, long_messages):
        """测试压缩长对话。"""
        # Mock summary generation
        compressor._generate_summary = lambda msgs, budget, model_caller=None: "Test summary"

        result = compressor.compress(long_messages)

        assert "messages" in result
        assert "summary" in result
        assert "head_count" in result
        assert "tail_count" in result
        assert "compressed_count" in result

        compressed = result["messages"]
        # 头部 + 摘要系统消息 + 尾部
        assert len(compressed) == result["head_count"] + 1 + result["tail_count"]

    def test_summary_contains_correct_prefix(self, compressor, long_messages):
        """测试摘要包含正确前缀。"""
        compressor._generate_summary = lambda msgs, budget, model_caller=None: "Test summary"

        result = compressor.compress(long_messages)

        # 查找摘要系统消息（包含 SUMMARY_PREFIX）
        summary_msgs = [m for m in result["messages"] if SUMMARY_PREFIX in m.get("content", "")]
        assert len(summary_msgs) >= 1

    def test_iterative_summary_update(self, compressor, long_messages):
        """测试迭代摘要更新。"""
        compressor._previous_summary = "Previous summary"
        compressor._generate_summary = lambda msgs, budget, model_caller=None: "Updated summary"

        result = compressor.compress(long_messages)

        # 摘要已更新
        assert result["summary"] == "Updated summary"
        # 前次摘要已保存
        assert compressor._previous_summary == "Updated summary"

    def test_first_summary_generation(self, compressor, long_messages):
        """测试首次摘要生成。"""
        assert compressor._previous_summary is None
        compressor._generate_summary = lambda msgs, budget, model_caller=None: "First summary"

        result = compressor.compress(long_messages)

        assert result["summary"] == "First summary"
        assert compressor._previous_summary == "First summary"


class TestCalculateSummaryBudget:
    """测试 calculate_summary_budget 方法。"""

    def test_small_content_budget(self, compressor):
        """测试小内容预算。"""
        # 10000 字符 -> 2500 tokens * 0.20 = 500 -> 最小值 2000
        budget = compressor._calculate_summary_budget(10000)
        assert budget == MIN_SUMMARY_TOKENS

    def test_medium_content_budget(self, compressor):
        """测试中等内容预算。"""
        # 50000 字符 -> 12500 tokens * 0.20 = 2500
        budget = compressor._calculate_summary_budget(50000)
        assert budget == 2500

    def test_large_content_budget_ceiling(self, compressor):
        """测试大内容预算上限。"""
        # 500000 字符 -> 125000 tokens * 0.20 = 25000 -> 最大值 12000
        budget = compressor._calculate_summary_budget(500000)
        assert budget == SUMMARY_TOKENS_CEILING


class TestProtectHead:
    """测试 protect_head 方法。"""

    def test_protect_first_n_messages(self, compressor):
        """测试保护前 N 条消息。"""
        messages = [{"role": "msg", "content": f"Message {i}"} for i in range(10)]
        head = compressor._protect_head(messages)
        assert len(head) == PROTECT_FIRST_N
        assert head[0]["content"] == "Message 0"

    def test_fewer_messages_than_protect(self, compressor):
        """测试消息少于保护数量。"""
        messages = [{"role": "msg", "content": f"Message {i}"} for i in range(2)]
        head = compressor._protect_head(messages)
        assert len(head) == 2


class TestProtectTail:
    """测试 protect_tail 方法。"""

    def test_protect_tail_messages(self, compressor):
        """测试保护尾部消息。"""
        messages = [{"role": "msg", "content": f"Message {i}" * 10} for i in range(20)]
        tail = compressor._protect_tail(messages)
        assert len(tail) > 0
        # 尾部消息应该在 token 预算内


class TestPreflightCheck:
    """测试预飞行压缩检查。"""

    def test_preflight_needs_compression(self, compressor):
        """测试预飞行需要压缩。"""
        # 创建大量消息
        messages = [{"role": "user", "content": "A" * 1000} for _ in range(5000)]
        assert compressor.check_preflight(messages) is True

    def test_preflight_no_compression_needed(self, compressor):
        """测试预飞行不需要压缩。"""
        messages = [{"role": "user", "content": "Short message"} for _ in range(5)]
        assert compressor.check_preflight(messages) is False


class TestPostResponseCheck:
    """测试响应后压缩检查。"""

    def test_context_length_exceeded(self, compressor):
        """测试 context_length_exceeded 错误触发压缩。"""
        response = {
            "error": {"type": "context_length_exceeded"}
        }
        assert compressor.check_post_response(response) is True

    def test_prompt_tokens_exceeded(self, compressor):
        """测试 prompt_tokens 超阈值触发压缩。"""
        response = {
            "usage": {"prompt_tokens": compressor.threshold_tokens + 1000}
        }
        assert compressor.check_post_response(response) is True

    def test_no_compression_needed(self, compressor):
        """测试不需要压缩。"""
        response = {
            "usage": {"prompt_tokens": compressor.threshold_tokens - 1000}
        }
        assert compressor.check_post_response(response) is False
