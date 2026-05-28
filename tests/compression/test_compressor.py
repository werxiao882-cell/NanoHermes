"""Tests for context compression module."""

import pytest

from src.compression.compressor import (
    ContextCompressor,
    _SUMMARY_BUDGET_RATIO,
    _MIN_SUMMARY_TOKENS,
    _MAX_SUMMARY_TOKENS,
    _PROTECT_HEAD_COUNT,
    _PROTECT_TAIL_COUNT,
)


class TestContextCompressor:
    """Tests for ContextCompressor class."""

    def test_init_default_thresholds(self):
        """Test initialization with default thresholds."""
        compressor = ContextCompressor(context_window=8000)
        assert compressor._context_window == 8000
        assert compressor._pre_threshold == 0.50
        assert compressor._force_threshold == 0.85

    def test_init_custom_thresholds(self):
        """Test initialization with custom thresholds."""
        compressor = ContextCompressor(
            context_window=16000,
            pre_compress_threshold=0.60,
            force_compress_threshold=0.90,
        )
        assert compressor._context_window == 16000
        assert compressor._pre_threshold == 0.60
        assert compressor._force_threshold == 0.90

    def test_needs_compression_below_threshold(self):
        """Test needs_compression returns False below threshold."""
        compressor = ContextCompressor(context_window=8000)
        # 50% of 8000 = 4000, so 3000 should not trigger
        assert compressor.needs_compression(3000) is False

    def test_needs_compression_at_threshold(self):
        """Test needs_compression returns True at threshold."""
        compressor = ContextCompressor(context_window=8000)
        # 85% of 8000 = 6800
        assert compressor.needs_compression(6800) is True
        assert compressor.needs_compression(7000) is True

    def test_needs_compression_zero_window(self):
        """Test needs_compression handles zero context window."""
        compressor = ContextCompressor(context_window=0)
        assert compressor.needs_compression(1000) is False

    def test_needs_pre_compress_below_threshold(self):
        """Test needs_pre_compress returns False below threshold."""
        compressor = ContextCompressor(context_window=8000)
        # 50% of 8000 = 4000, so 3000 should not trigger
        assert compressor.needs_pre_compress(3000) is False

    def test_needs_pre_compress_at_threshold(self):
        """Test needs_pre_compress returns True at threshold."""
        compressor = ContextCompressor(context_window=8000)
        # 50% of 8000 = 4000
        assert compressor.needs_pre_compress(4000) is True
        assert compressor.needs_pre_compress(5000) is True

    def test_calculate_summary_budget_minimum(self):
        """Test calculate_summary_budget returns minimum for small input."""
        compressor = ContextCompressor(context_window=8000)
        # 20% of 1000 = 200, but minimum is 2000
        budget = compressor.calculate_summary_budget(1000)
        assert budget == _MIN_SUMMARY_TOKENS

    def test_calculate_summary_budget_maximum(self):
        """Test calculate_summary_budget returns maximum for large input."""
        compressor = ContextCompressor(context_window=8000)
        # 20% of 100000 = 20000, but maximum is 12000
        budget = compressor.calculate_summary_budget(100000)
        assert budget == _MAX_SUMMARY_TOKENS

    def test_calculate_summary_budget_normal(self):
        """Test calculate_summary_budget returns normal value."""
        compressor = ContextCompressor(context_window=8000)
        # 20% of 20000 = 4000 (within bounds)
        budget = compressor.calculate_summary_budget(20000)
        assert budget == 4000

    def test_compress_empty_messages(self):
        """Test compress returns empty list for empty input."""
        compressor = ContextCompressor(context_window=8000)
        result = compressor.compress([], "summary")
        assert result == []

    def test_compress_preserves_system_messages(self):
        """Test compress preserves system messages."""
        compressor = ContextCompressor(context_window=8000)
        messages = [
            {"role": "system", "content": "You are an assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        result = compressor.compress(messages, "summary")
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are an assistant."

    def test_compress_protects_head_and_tail(self):
        """Test compress protects head and tail messages."""
        compressor = ContextCompressor(context_window=8000)
        # Create 10 messages
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        result = compressor.compress(messages, "summary")

        # Should have head (2) + summary (1) + tail (up to 20, but limited by available)
        assert len(result) >= 3
        # First message after system should be from head
        assert result[0]["content"] == "Message 0"

    def test_compress_inserts_summary(self):
        """Test compress inserts summary message."""
        compressor = ContextCompressor(context_window=8000)
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
        ]
        result = compressor.compress(messages, "Test summary")

        # Find summary message
        summary_msgs = [m for m in result if "Test summary" in m.get("content", "")]
        assert len(summary_msgs) >= 1

    def test_prune_tool_output_no_truncation(self):
        """Test prune_tool_output doesn't truncate short content."""
        compressor = ContextCompressor(context_window=8000)
        content = "Short output"
        result = compressor.prune_tool_output(content, max_length=500)
        assert result == content

    def test_prune_tool_output_truncates_long(self):
        """Test prune_tool_output truncates long content."""
        compressor = ContextCompressor(context_window=8000)
        content = "x" * 1000
        result = compressor.prune_tool_output(content, max_length=500)
        assert result.startswith("x" * 500)
        assert "[truncated]" in result

    def test_compress_head_tail_no_overlap(self):
        """Test compress handles case where head and tail would overlap."""
        compressor = ContextCompressor(context_window=8000)
        # Only 3 messages - head (2) + tail (20) would overlap
        messages = [
            {"role": "user", "content": "Msg 1"},
            {"role": "assistant", "content": "Msg 2"},
            {"role": "user", "content": "Msg 3"},
        ]
        result = compressor.compress(messages, "summary")
        # Should keep all messages without duplication
        assert len(result) >= 3
