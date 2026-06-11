"""TUI 工具可视化单元测试。"""

import pytest
from unittest.mock import patch

from src.cli.widgets import (
    ToolCallDisplay,
    ToolCallHistoryPanel,
    ToolCallResultSummary,
)
from src.cli.state import ToolCallRecord


class TestToolCallDisplay:
    """工具调用显示测试。"""
    
    def test_render_start(self):
        """测试渲染开始状态。"""
        display = ToolCallDisplay()
        result = display.render_start("read_file", {"path": "test.txt"})
        
        assert "read_file" in result
        assert "⏳" in result
    
    def test_render_start_no_args(self):
        """测试渲染开始状态（无参数）。"""
        display = ToolCallDisplay()
        result = display.render_start("read_file")
        
        assert "read_file" in result
    
    def test_render_running(self):
        """测试渲染运行状态。"""
        display = ToolCallDisplay()
        result = display.render_running("read_file")
        
        assert "read_file" in result
        assert "执行中" in result
        assert "🔄" in result
    
    def test_render_success(self):
        """测试渲染成功状态。"""
        display = ToolCallDisplay()
        result = display.render_success("read_file", result="内容", summary="读取 10 行")
        
        assert "read_file" in result
        assert "读取 10 行" in result
        assert "✅" in result
    
    def test_render_error(self):
        """测试渲染失败状态。"""
        display = ToolCallDisplay()
        result = display.render_error("read_file", error="文件不存在")
        
        assert "read_file" in result
        assert "文件不存在" in result
        assert "❌" in result


class TestToolCallHistoryPanel:
    """工具调用历史面板测试。"""
    
    def test_render_empty(self):
        """测试渲染空历史。"""
        panel = ToolCallHistoryPanel()
        result = panel.render([])
        
        assert "暂无" in result
    
    def test_render_with_history(self):
        """测试渲染有历史。"""
        panel = ToolCallHistoryPanel()
        tool_calls = [
            ToolCallRecord(tool_name="read_file", status="success", result="内容"),
            ToolCallRecord(tool_name="terminal", status="error", result="错误"),
        ]
        result = panel.render(tool_calls)
        
        assert "read_file" in result
        assert "terminal" in result
        assert "工具调用历史" in result
    
    def test_render_limits_display(self):
        """测试显示数量限制。"""
        panel = ToolCallHistoryPanel(max_display=2)
        tool_calls = [
            ToolCallRecord(tool_name=f"tool{i}", status="success")
            for i in range(5)
        ]
        result = panel.render(tool_calls)
        
        # 应该只显示最近 2 个
        assert "tool3" in result or "tool4" in result
    
    def test_generate_summary_read_file(self):
        """测试生成 read_file 摘要。"""
        panel = ToolCallHistoryPanel()
        result = panel._generate_summary("read_file", "line1\nline2\nline3")
        
        assert "行" in result
        assert "字符" in result
    
    def test_generate_summary_terminal(self):
        """测试生成 terminal 摘要。"""
        panel = ToolCallHistoryPanel()
        result = panel._generate_summary("terminal", "exit code: 0")
        
        assert "退出码" in result
    
    def test_generate_summary_empty(self):
        """测试生成空摘要。"""
        panel = ToolCallHistoryPanel()
        result = panel._generate_summary("unknown", "")
        
        assert result == ""


class TestToolCallResultSummary:
    """工具调用结果摘要生成器测试。"""
    
    def test_generate_basic(self):
        """测试基本摘要生成。"""
        result = ToolCallResultSummary.generate("read_file", "文件内容")
        
        assert result == "文件内容"
    
    def test_generate_truncates_long(self):
        """测试截断长结果。"""
        long_text = "A" * 200
        result = ToolCallResultSummary.generate("read_file", long_text, max_length=50)
        
        assert len(result) <= 50
        assert "..." in result
    
    def test_generate_empty(self):
        """测试空结果。"""
        result = ToolCallResultSummary.generate("read_file", "")
        
        assert result == "无结果"
    
    def test_generate_respects_max_length(self):
        """测试尊重最大长度。"""
        result = ToolCallResultSummary.generate("read_file", "短内容", max_length=100)
        
        assert result == "短内容"
