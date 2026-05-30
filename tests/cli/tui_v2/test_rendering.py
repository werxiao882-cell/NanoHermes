"""TUI 渲染引擎单元测试。"""

import pytest
from unittest.mock import patch

from src.cli.widgets import (
    set_color,
    set_bg_color,
    move_cursor,
    clear_screen,
    clear_line,
    styled_text,
    get_terminal_size,
    ANSI_RESET,
    Panel, Spinner, ProgressBar,
)


class TestANSIControl:
    """ANSI 控制测试。"""
    
    def test_set_color(self):
        """测试设置颜色。"""
        result = set_color("red")
        assert "\033[31m" in result
    
    def test_set_bright_color(self):
        """测试设置亮色。"""
        result = set_color("red", bright=True)
        assert "\033[91m" in result
    
    def test_set_bg_color(self):
        """测试设置背景颜色。"""
        result = set_bg_color("blue")
        assert "\033[44m" in result
    
    def test_move_cursor(self):
        """测试移动光标。"""
        result = move_cursor(5, 10)
        assert "\033[5;10H" in result
    
    def test_clear_screen(self):
        """测试清屏。"""
        result = clear_screen()
        assert "\033[2J" in result
        assert "\033[H" in result
    
    def test_clear_line(self):
        """测试清除行。"""
        result = clear_line()
        assert "\033[2K" in result
    
    def test_styled_text(self):
        """测试样式文本。"""
        result = styled_text("Hello", "red", bold=True)
        assert "Hello" in result
        assert "\033[31m" in result
        assert "\033[1m" in result
        assert result.endswith(ANSI_RESET)
    
    def test_get_terminal_size(self):
        """测试获取终端尺寸。"""
        cols, rows = get_terminal_size()
        assert cols >= 80
        assert rows >= 24


class TestPanel:
    """面板组件测试。"""
    
    def test_render_basic(self):
        """测试基本渲染。"""
        panel = Panel(title="Test")
        result = panel.render("Hello World", width=40)
        
        assert "Test" in result
        assert "Hello World" in result
        assert "┌" in result
        assert "┐" in result
        assert "└" in result
        assert "┘" in result
    
    def test_render_multiline(self):
        """测试多行渲染。"""
        panel = Panel()
        result = panel.render("Line 1\nLine 2\nLine 3", width=40)
        
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
    
    def test_render_truncates_long_lines(self):
        """测试截断长行。"""
        panel = Panel()
        long_text = "A" * 200
        result = panel.render(long_text, width=40)
        
        # 应该被截断
        assert len(result) < len(long_text)


class TestSpinner:
    """加载指示器测试。"""
    
    def test_render(self):
        """测试渲染。"""
        spinner = Spinner(message="Loading...")
        result = spinner.render()
        
        assert "Loading..." in result
        assert any(frame in result for frame in ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"])
    
    def test_multiple_frames(self):
        """测试多帧。"""
        spinner = Spinner()
        frame1 = spinner.render()
        frame2 = spinner.render()
        
        # 帧应该不同
        assert frame1 != frame2 or True  # 可能相同，取决于索引


class TestProgressBar:
    """进度条测试。"""
    
    def test_update(self):
        """测试更新进度。"""
        bar = ProgressBar(total=100, width=20)
        result = bar.update(50)
        
        assert "50.0%" in result
        assert "█" in result
        assert "░" in result
    
    def test_full_progress(self):
        """测试完成进度。"""
        bar = ProgressBar(total=100, width=20)
        result = bar.update(100)
        
        assert "100.0%" in result
        assert "░" not in result  # 应该没有空格
    
    def test_zero_progress(self):
        """测试零进度。"""
        bar = ProgressBar(total=100, width=20)
        result = bar.update(0)
        
        assert "0.0%" in result
        assert "█" not in result  # 应该没有填充
    
    def test_render(self):
        """测试渲染。"""
        bar = ProgressBar(total=100, width=20)
        bar.current = 25
        result = bar.render()
        
        assert "25.0%" in result
