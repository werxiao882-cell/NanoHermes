"""TUI 核心架构单元测试。"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from src.cli.tui import TUIApp
from src.cli.state import TUIState, ToolCallRecord
from src.cli.event_handler import TUIEventHandler


class TestTUIState:
    """TUIState 测试。"""
    
    def test_initial_state(self):
        """测试初始状态。"""
        state = TUIState()
        assert not state.running
        assert not state.welcomed
        assert state.session_id == ""
        assert not state.loading
        assert len(state.tool_calls) == 0
        assert len(state.input_history) == 0
    
    def test_add_tool_call(self):
        """测试添加工具调用记录。"""
        state = TUIState()
        record = state.add_tool_call("read_file", {"path": "test.txt"})
        
        assert record.tool_name == "read_file"
        assert record.status == "start"
        assert record.args == {"path": "test.txt"}
        assert len(state.tool_calls) == 1
    
    def test_update_tool_call(self):
        """测试更新工具调用状态。"""
        state = TUIState()
        state.add_tool_call("read_file")
        state.update_tool_call(0, "success", "文件内容")
        
        assert state.tool_calls[0].status == "success"
        assert state.tool_calls[0].result == "文件内容"
        assert state.tool_calls[0].completed_at > 0
    
    def test_save_and_load_state(self, tmp_path):
        """测试状态保存和加载。"""
        with patch("src.cli.state.STATE_DIR", tmp_path), \
             patch("src.cli.state.STATE_FILE", tmp_path / "state.json"):
            
            state = TUIState()
            state.session_id = "test-123"
            state.add_tool_call("read_file")
            state.input_history.append("hello")
            
            state.save()
            
            # 加载到新状态
            state2 = TUIState()
            state2.load()
            
            assert state2.session_id == "test-123"
            assert len(state2.tool_calls) == 1
            assert state2.input_history == ["hello"]


class TestTUIEventHandler:
    """TUIEventHandler 测试。"""
    
    @pytest.fixture
    def handler(self):
        """创建事件处理器。"""
        state = TUIState()
        return TUIEventHandler(state)
    
    @pytest.mark.asyncio
    async def test_handle_command_help(self, handler, capsys):
        """测试 /help 命令。"""
        await handler._cmd_help([])
        captured = capsys.readouterr()
        assert "可用命令" in captured.out
    
    @pytest.mark.asyncio
    async def test_handle_command_status(self, handler, capsys):
        """测试 /status 命令。"""
        handler.state.session_id = "test-123"
        await handler._cmd_status([])
        captured = capsys.readouterr()
        assert "test-123" in captured.out
    
    @pytest.mark.asyncio
    async def test_handle_command_tools(self, handler, capsys):
        """测试 /tools 命令。"""
        handler.state.add_tool_call("read_file")
        await handler._cmd_tools([])
        captured = capsys.readouterr()
        assert "工具调用历史" in captured.out
    
    def test_handle_tool_call_start(self, handler):
        """测试工具调用开始事件。"""
        index = handler.handle_tool_call_start("read_file", {"path": "test.txt"})
        
        assert index == 0
        assert len(handler.state.tool_calls) == 1
        assert handler.state.tool_calls[0].tool_name == "read_file"
    
    def test_handle_tool_call_complete(self, handler):
        """测试工具调用完成事件。"""
        index = handler.handle_tool_call_start("read_file", {})
        handler.handle_tool_call_complete(index, True, "文件内容")
        
        assert handler.state.tool_calls[0].status == "success"
        assert handler.state.tool_calls[0].result == "文件内容"
    
    def test_handle_interrupt(self, handler):
        """测试中断事件。"""
        handler.state.loading = True
        handler.handle_interrupt()
        
        assert not handler.state.loading
    
    def test_cleanup(self, handler):
        """测试清理。"""
        handler.pending_clarification = {"id": "123"}
        handler.cleanup()
        
        assert handler.pending_clarification is None


class TestTUIApp:
    """TUIApp 测试。"""
    
    @patch("src.cli.tui.PromptSession")
    def test_init(self, mock_session):
        """测试初始化。"""
        mock_session.return_value = AsyncMock()
        app = TUIApp()
        
        assert app.state is not None
        assert app.event_handler is not None
        assert app.key_bindings is not None
        assert app.style is not None
    
    @patch("src.cli.tui.PromptSession")
    def test_init_with_config(self, mock_session):
        """测试带配置初始化。"""
        mock_session.return_value = AsyncMock()
        config = {"typing_speed": 5}
        app = TUIApp(config=config)
        
        assert app.config == config
