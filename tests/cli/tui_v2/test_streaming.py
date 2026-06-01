"""TUI 流式输出系统单元测试。"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from src.cli.streaming import (
    TypewriterEffect,
    StreamingMarkdown,
    StreamingOutputBuffer,
    StreamingStatusIndicator,
)


class TestTypewriterEffect:
    """打字机效果测试。"""
    
    @pytest.mark.asyncio
    async def test_print_basic(self, capsys):
        """测试基本打印。"""
        effect = TypewriterEffect(speed_ms=1)  # 快速测试
        await effect.print("Hello")
        
        captured = capsys.readouterr()
        assert "Hello" in captured.out
    
    @pytest.mark.asyncio
    async def test_print_with_end(self, capsys):
        """测试带结束符。"""
        effect = TypewriterEffect(speed_ms=1)
        await effect.print("Hello", end="---")
        
        captured = capsys.readouterr()
        assert "Hello---" in captured.out
    
    def test_skip(self):
        """测试跳过。"""
        effect = TypewriterEffect()
        effect.skip()
        
        assert effect._skipped is True


class TestStreamingMarkdown:
    """流式 Markdown 测试。"""
    
    def test_update(self):
        """测试更新内容。"""
        md = StreamingMarkdown()
        md.update("# Hello")
        
        assert md.content == "# Hello"
    
    def test_update_multiple(self):
        """测试多次更新。"""
        md = StreamingMarkdown()
        md.update("# Hello")
        md.update("\n\nWorld")
        
        assert md.content == "# Hello\n\nWorld"
    
    def test_clear(self):
        """测试清空。"""
        md = StreamingMarkdown()
        md.update("# Hello")
        md.clear()
        
        assert md.content == ""
    
    def test_render_empty(self, capsys):
        """测试渲染空内容。"""
        md = StreamingMarkdown()
        md.render()
        
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_render_basic(self, capsys):
        """测试基本渲染。"""
        md = StreamingMarkdown()
        md.update("# Hello World")
        md.render()
        
        captured = capsys.readouterr()
        # rich 会渲染 Markdown，至少包含文本
        assert "Hello World" in captured.out or "Hello World" in str(captured)


class TestStreamingOutputBuffer:
    """流式输出缓冲区测试。"""
    
    def test_write(self):
        """测试写入。"""
        buf = StreamingOutputBuffer(flush_interval_ms=1000)  # 长间隔
        buf.write("Hello")
        
        assert buf._buffer == "Hello"
    
    def test_flush(self, capsys):
        """测试刷新。"""
        buf = StreamingOutputBuffer(flush_interval_ms=1)
        buf.write("Hello")
        buf.flush()
        
        captured = capsys.readouterr()
        assert "Hello" in captured.out
        assert buf._buffer == ""
    
    def test_clear(self):
        """测试清空。"""
        buf = StreamingOutputBuffer()
        buf.write("Hello")
        buf.clear()
        
        assert buf._buffer == ""
    
    def test_should_flush(self):
        """测试刷新判断。"""
        buf = StreamingOutputBuffer(flush_interval_ms=1)
        buf.write("Hello")
        
        # 等待刷新间隔
        import time
        time.sleep(0.01)
        
        assert buf._should_flush() is True


class TestStreamingStatusIndicator:
    """流式状态指示器测试。"""
    
    def test_start(self, capsys):
        """测试开始。"""
        indicator = StreamingStatusIndicator()
        indicator.start()
        
        captured = capsys.readouterr()
        assert "思考中" in captured.out
        assert indicator._is_streaming is True
    
    def test_complete(self, capsys):
        """测试完成。"""
        indicator = StreamingStatusIndicator()
        indicator.start()
        indicator.complete()
        
        captured = capsys.readouterr()
        assert "完成" in captured.out or "✅" in captured.out
        assert indicator._is_streaming is False
    
    def test_update(self, capsys):
        """测试更新。"""
        indicator = StreamingStatusIndicator()
        indicator.start()
        indicator.update()
        
        captured = capsys.readouterr()
        assert "思考中" in captured.out
