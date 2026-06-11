"""会话管理命令端到端集成测试。

测试 /sessions 和 /resume 命令的完整工作流程。
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from src.session.session_db import SessionDB
from src.cli.tui import TUIApp


@pytest.fixture
def temp_db():
    """创建临时 SessionDB 实例。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_sessions.db"
        db = SessionDB(db_path)
        yield db
        db.close()


@pytest.fixture
def populated_db(temp_db):
    """填充测试数据的 SessionDB。"""
    db = temp_db
    # 创建 3 个测试会话
    sid1 = db.create_session(title="测试会话 1", model="qwen3.6-plus")
    db.insert_message(sid1, "user", "你好")
    db.insert_message(sid1, "assistant", "你好！有什么可以帮助你的？")

    sid2 = db.create_session(title="代码分析任务", model="qwen3.6-plus")
    db.insert_message(sid2, "user", "分析这段代码")
    db.insert_message(sid2, "assistant", "好的，让我来分析...")

    sid3 = db.create_session(title="Python 调试", model="qwen3.6-plus")
    db.insert_message(sid3, "user", "帮我调试这个 bug")

    return db


class TestSessionsCommand:
    """测试 /sessions 命令。"""

    @pytest.mark.asyncio
    async def test_sessions_list_populated(self, populated_db, capsys):
        """测试列出有数据的会话列表。"""
        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=populated_db)
            await app._cmd_sessions()

        captured = capsys.readouterr()
        assert "历史会话" in captured.out
        assert "测试会话 1" in captured.out
        assert "代码分析任务" in captured.out
        assert "Python 调试" in captured.out

    @pytest.mark.asyncio
    async def test_sessions_list_empty(self, temp_db, capsys):
        """测试列出空会话列表。"""
        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=temp_db)
            await app._cmd_sessions()

        captured = capsys.readouterr()
        assert "暂无历史会话" in captured.out

    @pytest.mark.asyncio
    async def test_sessions_no_db(self, capsys):
        """测试无数据库时的提示。"""
        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=None)
            await app._cmd_sessions()

        captured = capsys.readouterr()
        assert "会话数据库不可用" in captured.out


class TestResumeCommand:
    """测试 /resume 命令。"""

    @pytest.mark.asyncio
    async def test_resume_by_id(self, populated_db, capsys):
        """测试通过会话 ID 恢复。"""
        sessions = populated_db.list_sessions()
        # 找到有消息的会话
        target_session = None
        for s in sessions:
            msgs = populated_db.get_messages(s["id"])
            if len(msgs) >= 2:
                target_session = s
                break

        assert target_session is not None, "No session with 2+ messages found"
        target_id = target_session["id"]

        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=populated_db)
            await app._cmd_resume(target_id)

        captured = capsys.readouterr()
        assert "已恢复会话" in captured.out
        assert app.session_id == target_id
        assert len(app.messages) >= 2

    @pytest.mark.asyncio
    async def test_resume_by_title_exact(self, populated_db, capsys):
        """测试通过精确标题恢复。"""
        # 先找到该会话的 ID
        matches = populated_db.search_sessions_by_title("代码分析任务", limit=1)
        assert len(matches) == 1, f"Expected 1 match, got {len(matches)}"
        target_id = matches[0]["id"]

        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=populated_db)
            await app._cmd_resume(target_id)

        captured = capsys.readouterr()
        assert "已恢复会话" in captured.out
        assert len(app.messages) >= 2

    @pytest.mark.asyncio
    async def test_resume_by_title_partial(self, populated_db, capsys):
        """测试通过标题关键词恢复。"""
        # 先找到该会话的 ID
        matches = populated_db.search_sessions_by_title("调试", limit=1)
        assert len(matches) >= 1, f"Expected at least 1 match, got {len(matches)}"
        target_id = matches[0]["id"]

        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=populated_db)
            await app._cmd_resume(target_id)

        captured = capsys.readouterr()
        assert "已恢复会话" in captured.out

    @pytest.mark.asyncio
    async def test_resume_not_found(self, populated_db, capsys):
        """测试恢复不存在的会话。"""
        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=populated_db)
            await app._cmd_resume("不存在的会话")

        captured = capsys.readouterr()
        assert "未找到匹配的会话" in captured.out

    @pytest.mark.asyncio
    async def test_resume_no_identifier(self, populated_db, capsys):
        """测试无参数时的提示。"""
        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=populated_db)
            await app._cmd_resume(None)

        captured = capsys.readouterr()
        assert "用法: /resume" in captured.out

    @pytest.mark.asyncio
    async def test_resume_no_db(self, capsys):
        """测试无数据库时的提示。"""
        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=None)
            await app._cmd_resume("test")

        captured = capsys.readouterr()
        assert "会话数据库不可用" in captured.out

    @pytest.mark.asyncio
    async def test_resume_multiple_matches(self, populated_db, capsys):
        """测试多个匹配时显示选择列表。"""
        # 创建多个相似标题的会话
        populated_db.create_session(title="测试会话 A")
        populated_db.create_session(title="测试会话 B")

        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=populated_db)
            await app._cmd_resume("测试会话")

        captured = capsys.readouterr()
        assert "找到多个匹配" in captured.out
        assert "测试会话 A" in captured.out or "测试会话 B" in captured.out


class TestHandleCommandIntegration:
    """测试 _handle_command 集成。"""

    @pytest.mark.asyncio
    async def test_handle_sessions_command(self, populated_db):
        """测试 _handle_command 处理 /sessions。"""
        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=populated_db)
            result = await app._handle_command("/sessions")
            assert result is True

    @pytest.mark.asyncio
    async def test_handle_resume_command(self, populated_db):
        """测试 _handle_command 处理 /resume。"""
        sessions = populated_db.list_sessions()
        target_id = sessions[0]["id"]

        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=populated_db)
            result = await app._handle_command(f"/resume {target_id}")
            assert result is True

    @pytest.mark.asyncio
    async def test_process_message_with_sessions(self, populated_db):
        """测试 process_message 处理 /sessions。"""
        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            with patch.object(TUIApp, "_print_status_bar"):
                app = TUIApp(session_db=populated_db)
                # process_message 会调用 _handle_command
                await app.process_message("/sessions")
                # 不应抛出异常
