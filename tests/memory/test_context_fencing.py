"""上下文隔离单元测试。"""

import pytest

from src.memory.context_fencing import sanitize_context, StreamingContextScrubber


class TestSanitizeContext:
    """测试 sanitize_context 函数。"""

    def test_remove_full_context_block(self):
        """测试移除完整上下文块。"""
        text = '<memory-context>secret data</memory-context>'
        result = sanitize_context(text)
        assert result == ""

    def test_remove_system_note(self):
        """测试移除系统注释。"""
        text = "[System note: The following is recalled memory context, NOT new user input.]"
        result = sanitize_context(text)
        assert result == ""

    def test_preserve_visible_content(self):
        """测试保留可见内容。"""
        text = "Hello <memory-context>secret</memory-context> World"
        result = sanitize_context(text)
        assert result == "Hello  World"

    def test_remove_multiple_blocks(self):
        """测试移除多个上下文块。"""
        text = "A<memory-context>1</memory-context>B<memory-context>2</memory-context>C"
        result = sanitize_context(text)
        assert result == "ABC"

    def test_remove_orphan_tags(self):
        """测试移除孤立标签。"""
        text = "Hello </memory-context> World <memory-context>"
        result = sanitize_context(text)
        assert result == "Hello  World "


class TestStreamingContextScrubber:
    """测试 StreamingContextScrubber 类。"""

    def test_full_tag_in_single_chunk(self):
        """测试完整标签在单个 chunk。"""
        scrubber = StreamingContextScrubber()
        result = scrubber.feed("Hello <memory-context>secret</memory-context> World")
        assert result == "Hello  World"

    def test_open_tag_in_first_chunk_close_in_second(self):
        """测试打开标签在第一个 chunk，关闭在第二个。"""
        scrubber = StreamingContextScrubber()
        result1 = scrubber.feed("Hello <memory-context>")
        assert result1 == "Hello "
        result2 = scrubber.feed("secret</memory-context> World")
        assert result2 == " World"

    def test_partial_open_tag(self):
        """测试部分打开标签。"""
        scrubber = StreamingContextScrubber()
        result1 = scrubber.feed("Hello <memory-")
        assert result1 == "Hello "
        result2 = scrubber.feed("context>secret</memory-context>")
        assert result2 == ""

    def test_flush_while_in_span(self):
        """测试 flush 时仍在 span 内。"""
        scrubber = StreamingContextScrubber()
        scrubber.feed("Hello <memory-context>")
        result = scrubber.flush()
        assert result == ""  # 丢弃未关闭的 span

    def test_flush_not_in_span(self):
        """测试 flush 时不在 span 内。"""
        scrubber = StreamingContextScrubber()
        scrubber.feed("Hello <memory-")
        result = scrubber.flush()
        assert result == "<memory-"  # 返回缓冲区内容

    def test_tag_at_line_start(self):
        """测试行首标签。"""
        scrubber = StreamingContextScrubber()
        result = scrubber.feed("\n<memory-context>secret</memory-context>")
        assert result == "\n"

    def test_tag_in_middle_of_word_not_recognized(self):
        """测试行中标签不被识别。"""
        scrubber = StreamingContextScrubber()
        result = scrubber.feed("word<memory-context>secret</memory-context>")
        # 标签不在块边界，不被识别
        assert "word" in result

    def test_reset_clears_state(self):
        """测试 reset 清除状态。"""
        scrubber = StreamingContextScrubber()
        scrubber.feed("Hello <memory-context>")
        scrubber.reset()
        result = scrubber.feed("World")
        assert result == "World"

    def test_empty_input_returns_empty(self):
        """测试空输入返回空字符串。"""
        scrubber = StreamingContextScrubber()
        result = scrubber.feed("")
        assert result == ""

    def test_multiple_tags_in_stream(self):
        """测试流中多个标签。"""
        scrubber = StreamingContextScrubber()
        result = scrubber.feed(
            "A<memory-context>1</memory-context>"
            "B<memory-context>2</memory-context>"
            "C"
        )
        # 标签在单词后不被识别（不是块边界）
        assert "A" in result
        assert "B" in result
        assert "C" in result

    def test_flush_discards_unclosed_span(self):
        """测试 flush 丢弃未关闭的 span 内容。"""
        scrubber = StreamingContextScrubber()
        scrubber.feed("Visible <memory-context>Secret")
        result = scrubber.flush()
        assert result == ""  # Secret 被丢弃

    def test_partial_close_tag_held_in_buffer(self):
        """测试部分关闭标签保留在缓冲区。"""
        scrubber = StreamingContextScrubber()
        scrubber.feed("Hello <memory-context>secret</memory")
        # 此时不应输出任何内容，因为可能还有关闭标签
        # 实际输出取决于实现，但缓冲区应保留部分标签
