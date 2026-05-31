"""会话存储端到端集成测试。

测试完整的会话生命周期：创建、保存消息、恢复。
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from src.session.session_db import SessionDB
from src.session.jsonl_store import JsonlSessionStore
from src.cli.tui import TUIApp


@pytest.fixture
def temp_storage():
    """创建临时存储环境。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_sessions.db"
        jsonl_dir = Path(tmp_dir) / "sessions"
        jsonl_dir.mkdir()

        db = SessionDB(db_path)
        jsonl_store = JsonlSessionStore(jsonl_dir)
        yield db, jsonl_store
        db.close()


class TestSessionStorageLifecycle:
    """测试完整会话生命周期。"""

    def test_create_and_save_session(self, temp_storage):
        """测试创建会话并保存消息。"""
        db, jsonl_store = temp_storage

        # 创建会话
        session_id = db.create_session(title="测试会话", model="qwen3.6-plus")

        # 保存消息到 SQLite
        db.insert_message(session_id, "user", "你好")
        db.insert_message(session_id, "assistant", "你好！有什么可以帮助你的？")

        # 保存消息到 JSONL
        jsonl_store.append_message(session_id, "user", "你好")
        jsonl_store.append_message(session_id, "assistant", "你好！有什么可以帮助你的？")

        # 验证 SQLite 存储
        messages_db = db.get_messages(session_id)
        assert len(messages_db) == 2
        assert messages_db[0]["role"] == "user"
        assert messages_db[1]["role"] == "assistant"

        # 验证 JSONL 存储
        messages_jsonl = jsonl_store.load_messages(session_id)
        assert len(messages_jsonl) == 2
        assert messages_jsonl[0]["role"] == "user"
        assert messages_jsonl[1]["role"] == "assistant"

    def test_list_sessions_after_save(self, temp_storage):
        """测试保存后可列出会话。"""
        db, jsonl_store = temp_storage

        # 创建 3 个会话
        for i in range(3):
            sid = db.create_session(title=f"测试会话 {i+1}")
            jsonl_store.append_message(sid, "user", f"消息 {i+1}")

        # 验证 JSONL 列表
        session_ids = jsonl_store.list_sessions()
        assert len(session_ids) == 3

        # 验证 SQLite 列表
        sessions = db.list_sessions()
        assert len(sessions) == 3

    def test_resume_session_from_sqlite(self, temp_storage):
        """测试从 SQLite 恢复会话。"""
        db, jsonl_store = temp_storage

        # 创建并保存会话
        session_id = db.create_session(title="恢复测试")
        db.insert_message(session_id, "user", "第一条消息")
        db.insert_message(session_id, "assistant", "第一条回复")
        db.insert_message(session_id, "user", "第二条消息")
        db.insert_message(session_id, "assistant", "第二条回复")

        # 恢复会话
        messages = db.get_messages(session_id)
        assert len(messages) == 4

        # 验证消息顺序
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"

    def test_resume_session_from_jsonl(self, temp_storage):
        """测试从 JSONL 恢复会话。"""
        db, jsonl_store = temp_storage

        # 创建并保存会话
        session_id = db.create_session(title="JSONL 恢复测试")
        jsonl_store.append_message(session_id, "user", "用户消息 1")
        jsonl_store.append_message(session_id, "assistant", "助手回复 1")
        jsonl_store.append_message(session_id, "user", "用户消息 2")

        # 恢复会话
        messages = jsonl_store.load_messages(session_id)
        assert len(messages) == 3
        assert messages[0]["content"] == "用户消息 1"
        assert messages[1]["content"] == "助手回复 1"
        assert messages[2]["content"] == "用户消息 2"

    def test_session_title_search(self, temp_storage):
        """测试会话标题搜索。"""
        db, jsonl_store = temp_storage

        db.create_session(title="Python 代码调试")
        db.create_session(title="JavaScript 问题")
        db.create_session(title="Python 数据分析")

        # 搜索 Python 相关
        matches = db.search_sessions_by_title("Python", limit=10)
        assert len(matches) == 2

        # 搜索 JavaScript
        matches = db.search_sessions_by_title("JavaScript", limit=10)
        assert len(matches) == 1


class TestTUISessionStorage:
    """测试 TUI 中的会话存储。"""

    @pytest.mark.asyncio
    async def test_tui_saves_user_message(self, temp_storage):
        """测试 TUI 保存用户消息。"""
        db, jsonl_store = temp_storage
        session_id = db.create_session(title="TUI 测试")

        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=db, session_id=session_id)
            app.jsonl_store = jsonl_store

            # 模拟添加用户消息并保存
            app.messages.append({"role": "user", "content": "测试消息"})
            app._save_message_to_storage("user", "测试消息")

            # 验证保存
            messages_db = db.get_messages(session_id)
            assert len(messages_db) == 1
            assert messages_db[0]["role"] == "user"

            messages_jsonl = jsonl_store.load_messages(session_id)
            assert len(messages_jsonl) == 1

    @pytest.mark.asyncio
    async def test_tui_saves_assistant_message(self, temp_storage):
        """测试 TUI 保存助手消息。"""
        db, jsonl_store = temp_storage
        session_id = db.create_session(title="TUI 助手测试")

        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=db, session_id=session_id)
            app.jsonl_store = jsonl_store

            # 模拟添加助手消息并保存
            app.messages.append({"role": "assistant", "content": "助手回复"})
            app._save_message_to_storage("assistant", "助手回复")

            # 验证保存
            messages_db = db.get_messages(session_id)
            assert len(messages_db) == 1
            assert messages_db[0]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_tui_resume_loads_messages(self, temp_storage):
        """测试 TUI 恢复会话时加载消息。"""
        db, jsonl_store = temp_storage
        session_id = db.create_session(title="恢复测试")

        # 预先保存消息
        db.insert_message(session_id, "user", "历史消息 1")
        db.insert_message(session_id, "assistant", "历史回复 1")

        with patch("src.cli.tui.PromptSession", return_value=MagicMock()):
            app = TUIApp(session_db=db, session_id="new_session")

            # 恢复会话
            await app._cmd_resume(session_id)

            # 验证消息已加载
            assert app.session_id == session_id
            assert len(app.messages) == 2
            assert app.messages[0]["role"] == "user"
            assert app.messages[1]["role"] == "assistant"
