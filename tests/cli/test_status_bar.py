"""TUI 状态栏组件测试。"""

import pytest
from rich.text import Text

from src.cli.widgets import StatusBar


class TestStatusBar:
    """状态栏组件测试。"""
    
    def test_initial_state(self):
        """测试初始状态。"""
        bar = StatusBar(model="qwen3.6-plus")
        
        assert bar.model == "qwen3.6-plus"
        assert bar.input_tokens == 0
        assert bar.output_tokens == 0
        assert bar.elapsed_time == 0.0
    
    def test_update_tokens(self):
        """测试更新 Token 计数。"""
        bar = StatusBar()
        bar.update_tokens(1000, 500)
        
        assert bar.input_tokens == 1000
        assert bar.output_tokens == 500
    
    def test_update_time(self):
        """测试更新耗时。"""
        bar = StatusBar()
        bar.update_time(5.5)
        
        assert bar.elapsed_time == 5.5
        assert bar.last_response_time == 5.5
    
    def test_render_basic(self):
        """测试基本渲染。"""
        bar = StatusBar(model="qwen3.6-plus")
        bar.update_tokens(50000, 30000)
        bar.update_time(120)
        
        result = bar.render()
        
        assert isinstance(result, Text)
        assert "qwen3.6-plus" in result.plain
        assert "80.0K" in result.plain or "80" in result.plain
    
    def test_render_high_usage(self):
        """测试高使用率渲染。"""
        bar = StatusBar(model="test", context_window=100000)
        bar.update_tokens(95000, 0)
        
        result = bar.render()
        # 应该包含红色样式（使用率 > 90%）
        assert "95" in result.plain
    
    def test_render_time_formatting(self):
        """测试时间格式化。"""
        bar = StatusBar()
        
        # 秒级
        bar.update_time(30)
        result = bar.render()
        assert "30s" in result.plain
        
        # 分钟级
        bar2 = StatusBar()
        bar2.update_time(120)
        result2 = bar2.render()
        assert "2m" in result2.plain
    
    def test_render_progress_bar(self):
        """测试进度条渲染。"""
        bar = StatusBar(context_window=1000)
        bar.update_tokens(500, 0)
        
        result = bar.render()
        # 应该包含进度条字符
        assert "█" in result.plain or "░" in result.plain
