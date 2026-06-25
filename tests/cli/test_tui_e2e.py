"""TUI 端到端集成测试。

模拟完整的 TUI 启动流程和用户交互场景。
"""

import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from src.cli.tui import TUIApp
from src.cli.state import TUIState, ToolCallRecord
from src.cli.event_handler import TUIEventHandler
from src.cli.completers import CommandCompleter, FilePathCompleter, ContextAwareCompleter
from src.cli.history import TUIHistory
from src.cli.streaming import TypewriterEffect, StreamingMarkdown, StreamingOutputBuffer, StreamingStatusIndicator
from src.cli.layout import LayoutManager, LayoutConfig, DynamicPanelManager
from src.cli.widgets import Panel, Spinner, ProgressBar, ToolCallDisplay, ToolCallHistoryPanel


class TestTUIAppE2E:
    """TUIApp 端到端测试。"""
    
    @patch("src.cli.tui.PromptSession")
    def test_app_initialization(self, mock_session):
        """测试应用初始化。"""
        mock_session.return_value = MagicMock()
        app = TUIApp()
        
        assert app.state is not None
        assert app.event_handler is not None
        assert app.layout_manager is not None
        assert app.completer is not None
        assert app.history is not None
    
    @patch("src.cli.tui.PromptSession")
    def test_app_with_custom_config(self, mock_session):
        """测试自定义配置初始化。"""
        mock_session.return_value = MagicMock()
        config = {
            "typing_speed": 5,
            "show_tool_panel": False,
            "tool_panel_position": "bottom",
        }
        app = TUIApp(config=config)
        
        assert app.config["typing_speed"] == 5
        assert app.layout_manager.config.show_tool_panel is False
        assert app.layout_manager.config.tool_panel_position == "bottom"
    
    @pytest.mark.asyncio
    async def test_app_shutdown(self):
        """测试应用优雅关闭。"""
        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp()
            app.state.running = True
            app.state.welcomed = True
            
            await app.shutdown()
            
            assert app.state.running is False


class TestEventHandlerE2E:
    """事件处理器端到端测试。"""
    
    @pytest.fixture
    def handler(self):
        """创建事件处理器。"""
        state = TUIState()
        return TUIEventHandler(state)
    
    @pytest.mark.asyncio
    async def test_handle_help_command(self, handler, capsys):
        """测试处理 /help 命令。"""
        await handler.handle_user_input("/help")
        captured = capsys.readouterr()
        assert "可用命令" in captured.out
    
    @pytest.mark.asyncio
    async def test_handle_status_command(self, handler, capsys):
        """测试处理 /status 命令。"""
        handler.state.session_id = "test-session-123"
        await handler.handle_user_input("/status")
        captured = capsys.readouterr()
        assert "test-session-123" in captured.out
    
    @pytest.mark.asyncio
    async def test_handle_tools_command(self, handler, capsys):
        """测试处理 /tools 命令。"""
        handler.state.add_tool_call("read_file", {"path": "test.txt"})
        handler.state.update_tool_call(0, "success", "文件内容")
        
        await handler.handle_user_input("/tools")
        captured = capsys.readouterr()
        assert "工具调用历史" in captured.out
    
    @pytest.mark.asyncio
    async def test_handle_clear_command(self, handler, capsys):
        """测试处理 /clear 命令。"""
        await handler.handle_user_input("/clear")
        captured = capsys.readouterr()
        # ANSI 清屏码
        assert "\033[2J" in captured.out
    
    @pytest.mark.asyncio
    async def test_handle_quit_command(self, handler):
        """测试处理 /quit 命令。"""
        handler.state.running = True
        await handler.handle_user_input("/quit")
        
        assert handler.state.running is False
    
    @pytest.mark.asyncio
    async def test_handle_unknown_command(self, handler, capsys):
        """测试处理未知命令。"""
        await handler.handle_user_input("/unknown")
        captured = capsys.readouterr()
        assert "未知命令" in captured.out
    
    def test_tool_call_lifecycle(self, handler):
        """测试工具调用完整生命周期。"""
        # 开始
        index = handler.handle_tool_call_start("read_file", {"path": "test.txt"})
        assert index == 0
        assert handler.state.tool_calls[0].status == "start"
        
        # 完成
        handler.handle_tool_call_complete(index, True, "文件内容")
        assert handler.state.tool_calls[0].status == "success"
        assert handler.state.tool_calls[0].result == "文件内容"
    
    def test_multiple_tool_calls(self, handler):
        """测试多个工具调用。"""
        idx1 = handler.handle_tool_call_start("read_file", {})
        idx2 = handler.handle_tool_call_start("terminal", {})
        idx3 = handler.handle_tool_call_start("search_files", {})
        
        handler.handle_tool_call_complete(idx1, True, "文件内容")
        handler.handle_tool_call_complete(idx2, False, "命令失败")
        handler.handle_tool_call_complete(idx3, True, "找到 5 个文件")
        
        assert len(handler.state.tool_calls) == 3
        assert handler.state.tool_calls[0].status == "success"
        assert handler.state.tool_calls[1].status == "error"
        assert handler.state.tool_calls[2].status == "success"


class TestCompletersE2E:
    """补全器端到端测试。"""
    
    def test_command_completer_full(self):
        """测试命令补全器完整功能。"""
        completer = CommandCompleter()
        
        # 测试所有命令
        test_cases = [
            ("/h", ["/help"]),
            ("/c", ["/clear"]),
            ("/q", ["/quit"]),
            ("/r", ["/resume"]),
            ("/s", ["/status"]),
            ("/t", ["/tools"]),
        ]
        
        for prefix, expected in test_cases:
            from prompt_toolkit.document import Document
            doc = Document(text=prefix, cursor_position=len(prefix))
            completions = list(completer.get_completions(doc, None))
            completion_texts = [c.text for c in completions]
            
            for exp in expected:
                assert exp in completion_texts, f"命令 {exp} 未补全"
    
    def test_file_path_completer_with_real_files(self, tmp_path):
        """测试文件路径补全器与真实文件。"""
        # 创建测试文件结构
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").touch()
        (tmp_path / "src" / "utils.py").touch()
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").touch()
        (tmp_path / "README.md").touch()
        
        completer = FilePathCompleter()
        
        # 测试补全（不带末尾斜杠）
        from prompt_toolkit.document import Document
        doc = Document(text=str(tmp_path / "src"), cursor_position=len(str(tmp_path / "src")))
        completions = list(completer.get_completions(doc, None))
        completion_texts = [c.text for c in completions]
        
        # 应该找到 src 目录下的文件
        assert len(completion_texts) >= 1
    
    def test_context_aware_completer_delegation(self):
        """测试上下文感知补全器委托。"""
        completer = ContextAwareCompleter()
        
        from prompt_toolkit.document import Document
        
        # 命令补全
        doc = Document(text="/he", cursor_position=3)
        completions = list(completer.get_completions(doc, None))
        assert any(c.text == "/help" for c in completions)


class TestStreamingE2E:
    """流式输出端到端测试。"""
    
    @pytest.mark.asyncio
    async def test_typewriter_effect_full(self, capsys):
        """测试打字机效果完整流程。"""
        effect = TypewriterEffect(speed_ms=1)  # 快速测试
        await effect.print("Hello World", end="\n")
        
        captured = capsys.readouterr()
        assert "Hello World" in captured.out
    
    @pytest.mark.asyncio
    async def test_typewriter_skip(self, capsys):
        """测试打字机跳过功能。"""
        effect = TypewriterEffect(speed_ms=100)  # 慢速
        effect.skip()  # 立即跳过
        await effect.print("Hello World")
        
        captured = capsys.readouterr()
        assert "Hello World" in captured.out
    
    def test_streaming_markdown_incremental(self, capsys):
        """测试增量 Markdown 渲染。"""
        md = StreamingMarkdown()
        
        # 逐步添加内容
        md.update("# 标题")
        md.update("\n\n")
        md.update("- 项目 1")
        md.update("\n")
        md.update("- 项目 2")
        
        assert md.content == "# 标题\n\n- 项目 1\n- 项目 2"
        
        # 渲染
        md.render()
        captured = capsys.readouterr()
        # rich 会渲染 Markdown
        assert "标题" in captured.out or "项目" in captured.out
    
    def test_output_buffer_flush_cycle(self, capsys):
        """测试输出缓冲区刷新循环。"""
        buf = StreamingOutputBuffer(flush_interval_ms=10)
        
        buf.write("Hello")
        buf.write(" ")
        buf.write("World")
        
        # 等待刷新
        import time
        time.sleep(0.05)
        
        buf.flush()
        captured = capsys.readouterr()
        assert "Hello World" in captured.out
    
    def test_status_indicator_lifecycle(self, capsys):
        """测试状态指示器生命周期。"""
        indicator = StreamingStatusIndicator()

        indicator.start()
        captured1 = capsys.readouterr()
        assert "思考中" in captured1.out
        assert indicator._is_streaming is True

        indicator.complete()
        # complete() 只清空状态行，不打印额外内容
        assert indicator._is_streaming is False


class TestLayoutE2E:
    """布局系统端到端测试。"""
    
    @patch("src.cli.layout.get_terminal_size")
    def test_layout_adaptation(self, mock_size):
        """测试布局自适应。"""
        manager = LayoutManager()
        
        # 测试不同尺寸
        test_sizes = [
            (120, 40),   # 标准
            (80, 24),    # 最小
            (200, 60),   # 大屏
            (150, 50),   # 宽屏
        ]
        
        for width, height in test_sizes:
            mock_size.return_value = (width, height)
            layout = manager.get_layout()
            
            assert layout["width"] == width
            assert layout["height"] == height
            assert "main" in layout
    
    @patch("src.cli.layout.get_terminal_size")
    def test_panel_position_changes(self, mock_size):
        """测试面板位置变化。"""
        mock_size.return_value = (120, 40)
        
        config_right = LayoutConfig(show_tool_panel=True, tool_panel_position="right")
        manager_right = LayoutManager(config_right)
        layout_right = manager_right.get_layout()
        
        config_bottom = LayoutConfig(show_tool_panel=True, tool_panel_position="bottom")
        manager_bottom = LayoutManager(config_bottom)
        layout_bottom = manager_bottom.get_layout()
        
        assert layout_right["type"] == "vertical_split"
        assert layout_bottom["type"] == "horizontal_split"
    
    def test_dynamic_panel_management(self):
        """测试动态面板管理。"""
        manager = LayoutManager()
        panel_mgr = DynamicPanelManager(manager)
        
        # 创建面板
        panel_mgr.create_panel("tools", {"title": "工具"})
        panel_mgr.create_panel("status", {"title": "状态"})
        panel_mgr.create_panel("history", {"title": "历史"})
        
        assert len(panel_mgr.list_panels()) == 3
        
        # 获取面板
        tools_panel = panel_mgr.get_panel("tools")
        assert tools_panel["title"] == "工具"
        
        # 销毁面板
        panel_mgr.destroy_panel("status")
        assert len(panel_mgr.list_panels()) == 2
        assert panel_mgr.get_panel("status") is None
        
        # 重排
        panel_mgr.rearrange_panels()


class TestToolDisplayE2E:
    """工具可视化端到端测试。"""
    
    def test_full_tool_call_display(self):
        """测试完整工具调用显示。"""
        display = ToolCallDisplay()
        
        # 开始
        start_msg = display.render_start("read_file", {"path": "test.txt"})
        assert "read_file" in start_msg
        assert "⏳" in start_msg
        
        # 运行中
        running_msg = display.render_running("read_file")
        assert "执行中" in running_msg
        assert "🔄" in running_msg
        
        # 成功
        success_msg = display.render_success("read_file", result="内容", summary="10 行")
        assert "read_file" in success_msg
        assert "10 行" in success_msg
        assert "✅" in success_msg
        
        # 失败
        error_msg = display.render_error("read_file", error="文件不存在")
        assert "read_file" in error_msg
        assert "文件不存在" in error_msg
        assert "❌" in error_msg
    
    def test_history_panel_with_multiple_calls(self):
        """测试历史面板显示多个工具调用。"""
        panel = ToolCallHistoryPanel(max_display=5)
        
        tool_calls = [
            ToolCallRecord(tool_name="read_file", status="success", result="内容 1"),
            ToolCallRecord(tool_name="terminal", status="success", result="exit code: 0"),
            ToolCallRecord(tool_name="search_files", status="error", result="未找到"),
            ToolCallRecord(tool_name="write_file", status="success", result="已写入"),
            ToolCallRecord(tool_name="patch", status="running"),
        ]
        
        result = panel.render(tool_calls)
        
        assert "工具调用历史" in result
        assert "read_file" in result
        assert "terminal" in result
        assert "search_files" in result


class TestIntegrationWorkflow:
    """集成工作流测试。"""
    
    def test_full_session_lifecycle(self):
        """测试完整会话生命周期。"""
        state = TUIState()
        handler = TUIEventHandler(state)
        
        # 1. 初始化
        assert not state.running
        assert not state.welcomed
        
        # 2. 开始会话
        state.running = True
        state.welcomed = True
        state.session_id = "session-123"
        
        # 3. 用户输入
        state.input_history.append("你好，帮我分析一下这段代码")
        
        # 4. 工具调用
        idx1 = handler.handle_tool_call_start("read_file", {"path": "main.py"})
        handler.handle_tool_call_complete(idx1, True, "代码内容...")
        
        idx2 = handler.handle_tool_call_start("terminal", {"command": "python main.py"})
        handler.handle_tool_call_complete(idx2, True, "输出结果...")
        
        # 5. 保存状态
        state.save()
        
        # 6. 验证状态
        assert len(state.tool_calls) == 2
        assert len(state.input_history) == 1
        assert state.session_id == "session-123"
        
        # 7. 清理
        handler.cleanup()
        state.running = False
    
    def test_concurrent_tool_calls(self):
        """测试并发工具调用模拟。"""
        state = TUIState()
        handler = TUIEventHandler(state)
        
        # 模拟多个工具同时调用
        tools = [
            ("read_file", {"path": "a.py"}),
            ("read_file", {"path": "b.py"}),
            ("search_files", {"query": "test"}),
        ]
        
        indices = []
        for name, args in tools:
            idx = handler.handle_tool_call_start(name, args)
            indices.append(idx)
        
        # 全部标记为运行中
        for idx in indices:
            state.tool_calls[idx].status = "running"
        
        # 按顺序完成
        handler.handle_tool_call_complete(indices[0], True, "文件 A 内容")
        handler.handle_tool_call_complete(indices[1], True, "文件 B 内容")
        handler.handle_tool_call_complete(indices[2], True, "找到 3 个结果")
        
        # 验证所有工具都完成
        for tc in state.tool_calls:
            assert tc.status == "success"
