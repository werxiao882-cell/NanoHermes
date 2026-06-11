"""集成测试：从 src.main 开始的完整流程测试。

测试场景：
1. API 连接测试 (--test-api)
2. 交互模式初始化（模块耦合）
3. 工具调用链（terminal 工具）
4. 会话持久化（SessionDB）
5. 记忆注入（MemoryManager）
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_env():
    """模拟环境变量配置。"""
    os.environ["DASHSCOPE_API_KEY"] = "test-key-123"
    os.environ["DASHSCOPE_BASE_URL"] = "https://test.example.com/v1"
    os.environ["MODEL_NAME"] = "test-model"
    yield
    del os.environ["DASHSCOPE_API_KEY"]
    del os.environ["DASHSCOPE_BASE_URL"]
    del os.environ["MODEL_NAME"]


@pytest.fixture
def temp_home(tmp_path):
    """模拟临时 HOME 目录。"""
    with patch.object(Path, "home", return_value=tmp_path):
        yield tmp_path


class TestMainModule:
    """测试 main.py 模块加载和初始化。"""

    def test_import_main(self):
        """测试 main 模块可正常导入。"""
        from src import main
        assert hasattr(main, "main")
        assert hasattr(main, "main_chat")
        assert hasattr(main, "list_sessions_command")

    def test_main_chat_assembly(self):
        """测试 main_chat 函数的依赖注入结构。"""
        # main_chat 是组合根函数，验证其存在且可调用
        from src.main import main_chat
        assert callable(main_chat)

    def test_list_sessions_command(self):
        """测试 list_sessions_command 函数。"""
        from src.main import list_sessions_command
        assert callable(list_sessions_command)


class TestToolIntegration:
    """测试工具调用链集成。"""

    def test_terminal_tool_registered(self):
        """测试 terminal 工具已注册到注册表。"""
        from src.tools.core.registry import ToolRegistry, register_tool
        from src.tools.impls.terminal import _register_terminal_tool

        ToolRegistry.clear()
        _register_terminal_tool()

        from src.tools.core.registry import get_tool
        tool = get_tool("terminal")
        assert tool is not None
        assert tool.name == "terminal"
        assert tool.toolset == "terminal"

    def test_tool_dispatch_terminal_command(self):
        """测试通过分发器执行终端命令。"""
        from src.tools.core.registry import ToolRegistry
        from src.tools.impls.terminal import _register_terminal_tool
        from src.tools.core.dispatcher import dispatch

        ToolRegistry.clear()
        _register_terminal_tool()

        result = dispatch("terminal", {"command": "echo test123"})
        data = json.loads(result)

        assert "test123" in data["stdout"]
        assert data["exit_code"] == 0

    def test_tool_dispatch_dangerous_command(self):
        """测试危险命令返回审批请求。"""
        from src.tools.core.registry import ToolRegistry
        from src.tools.impls.terminal import _register_terminal_tool
        from src.tools.core.dispatcher import dispatch

        ToolRegistry.clear()
        _register_terminal_tool()

        result = dispatch("terminal", {"command": "rm -rf /tmp/test"})
        data = json.loads(result)

        assert data.get("requires_approval") is True
        assert "reason" in data


class TestSessionIntegration:
    """测试会话存储集成。"""

    def test_session_lifecycle(self, temp_home):
        """测试完整会话生命周期。"""
        from src.session.session_db import SessionDB

        db_path = temp_home / ".nanohermes" / "sessions.db"
        with SessionDB(db_path) as db:
            # 创建会话
            session_id = db.create_session(model="test-model", provider="test")
            assert session_id is not None

            # 获取会话
            session = db.get_session(session_id)
            assert session is not None
            assert session["model"] == "test-model"

            # 插入消息
            msg_id = db.insert_message(session_id, "user", "Hello")
            assert msg_id is not None

            # 获取消息
            messages = db.get_messages(session_id)
            assert len(messages) == 1
            assert messages[0]["content"] == "Hello"

            # 更新 token 计数
            db.update_token_counts(session_id, input_tokens=100, output_tokens=50)
            session = db.get_session(session_id)
            assert session["input_tokens"] == 100
            assert session["output_tokens"] == 50

            # 结束会话
            db.end_session(session_id, end_reason="completed")
            session = db.get_session(session_id)
            assert session["ended_at"] is not None
            assert session["end_reason"] == "completed"

    def test_session_search(self, temp_home):
        """测试 FTS5 全文搜索。"""
        from src.session.session_db import SessionDB

        db_path = temp_home / ".nanohermes" / "sessions.db"
        with SessionDB(db_path) as db:
            session_id = db.create_session()

            db.insert_message(session_id, "user", "Python 是一门很好的编程语言")
            db.insert_message(session_id, "assistant", "是的，Python 非常流行")
            db.insert_message(session_id, "user", "JavaScript 也很流行")

            # 搜索消息
            results = db.search_messages("Python", session_id)
            assert len(results) >= 1


class TestMemoryIntegration:
    """测试记忆系统集成。"""

    def test_file_memory_provider(self, temp_home):
        """测试文件记忆提供者。"""
        from src.memory.file_provider import FileMemoryProvider

        provider = FileMemoryProvider(temp_home)
        provider.initialize({})

        # 验证文件创建 (文件存储在 memory/ 子目录下)
        assert (temp_home / "memory" / "MEMORY.md").exists()
        assert (temp_home / "memory" / "USER.md").exists()

        # 添加记忆
        provider.add_entry("测试", "这是一条测试记忆")
        content = provider.prefetch()
        assert "测试" in content
        assert "这是一条测试记忆" in content

    def test_memory_manager(self, temp_home):
        """测试记忆管理器编排。"""
        from src.memory.managers import MemoryManager
        from src.memory.file_provider import FileMemoryProvider

        manager = MemoryManager()
        provider = FileMemoryProvider(temp_home)
        manager.add_provider(provider)
        manager.initialize_all({})

        # 构建系统提示部分
        section = manager.build_system_prompt_section()
        assert "<memory-context>" in section or section == ""


class TestPromptAssembly:
    """测试系统提示组装。"""

    def test_three_tier_assembly(self):
        """测试三层提示组装。"""
        from src.conversation.assembler import PromptAssembler

        assembler = PromptAssembler()
        assembler.set_stable(["身份：AI 助手", "工具：terminal"])
        assembler.set_context(["上下文：当前目录 /home/user"])
        assembler.set_volatile(["记忆：用户喜欢 Python", "时间：2024-01-01"])

        result = assembler.assemble()
        assert "身份：AI 助手" in result
        assert "上下文：当前目录" in result
        assert "记忆：用户喜欢 Python" in result

    def test_stable_hash_changes(self):
        """测试 stable 层变化时哈希改变。"""
        from src.conversation.assembler import PromptAssembler

        assembler = PromptAssembler()
        assembler.set_stable(["stable text 1"])
        hash1 = assembler.get_stable_hash()

        assembler.set_stable(["stable text 2"])
        hash2 = assembler.get_stable_hash()

        assert hash1 != hash2


class TestConversationLoopIntegration:
    """测试对话循环集成。"""

    def test_loop_with_mock_model(self):
        """测试对话循环与模拟模型。"""
        from src.conversation.loop import ConversationLoop

        call_count = 0

        def mock_call(messages, tools):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 第一次返回工具调用
                return {
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {"name": "echo", "arguments": '{"msg": "hello"}'},
                    }],
                }
            else:
                # 第二次返回文本
                return {"content": "Done!", "tool_calls": None}

        def mock_dispatch(name, args):
            return json.dumps({"result": "ok"})

        loop = ConversationLoop(model_call=mock_call, tool_dispatch=mock_dispatch)
        result = loop.run([{"role": "user", "content": "Test"}])

        assert call_count == 2  # 模型被调用两次
        assert result["final_response"] == "Done!"
        assert result["iterations"] == 2

    def test_loop_max_iterations(self):
        """测试达到最大迭代次数。"""
        from src.conversation.loop import ConversationLoop

        def mock_call(messages, tools):
            return {
                "content": None,
                "tool_calls": [{"id": "call_1", "function": {"name": "x", "arguments": "{}"}}],
            }

        loop = ConversationLoop(max_iterations=3, model_call=mock_call, tool_dispatch=lambda n, a: "ok")
        result = loop.run([{"role": "user", "content": "Test"}])

        assert result["iterations"] == 3
        assert "最大迭代" in result["final_response"]
