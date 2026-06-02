"""JSONL 会话历史存储单元测试。

测试追加写入、加载消息、列出会话、删除会话等。
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.session.jsonl_store import JsonlSessionStore


@pytest.fixture
def store_dir():
    """创建临时存储目录。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def store(store_dir):
    """创建 JsonlSessionStore 实例。"""
    return JsonlSessionStore(store_dir)


class TestAppendMessage:
    """测试 append_message 方法。"""

    def test_append_single_message(self, store):
        """测试追加单条消息。"""
        store.append_message("session-1", "user", "Hello")

        messages = store.load_messages("session-1")
        assert len(messages) == 1
        assert messages[0]["type"] == "user"
        assert messages[0]["content"] == "Hello"
        assert "timestamp" in messages[0]

    def test_append_multiple_messages(self, store):
        """测试追加多条消息。"""
        store.append_message("session-1", "user", "Hello")
        store.append_message("session-1", "assistant", "Hi there!")

        messages = store.load_messages("session-1")
        assert len(messages) == 2

    def test_append_with_tool_calls(self, store):
        """测试追加带工具调用的消息。"""
        tool_calls = [{"name": "read_file", "arguments": {"path": "/test.py"}}]
        store.append_message("session-1", "assistant", tool_calls=tool_calls)

        messages = store.load_messages("session-1")
        assert messages[0]["tool_calls"] == tool_calls

    def test_append_with_reasoning(self, store):
        """测试追加带推理内容的消息。"""
        store.append_message("session-1", "assistant", "Answer", reasoning="Thinking...")

        messages = store.load_messages("session-1")
        assert messages[0]["reasoning"] == "Thinking..."

    def test_append_with_metadata(self, store):
        """测试追加带元数据的消息。"""
        metadata = {"model": "gpt-4", "tokens": 100}
        store.append_message("session-1", "user", "Hello", metadata=metadata)

        messages = store.load_messages("session-1")
        assert messages[0]["metadata"] == metadata


class TestLoadMessages:
    """测试 load_messages 方法。"""

    def test_load_existing_messages(self, store):
        """测试加载已存在的消息。"""
        store.append_message("session-1", "user", "Hello")
        store.append_message("session-1", "assistant", "Hi")

        messages = store.load_messages("session-1")
        assert len(messages) == 2

    def test_load_nonexistent_session(self, store):
        """测试加载不存在的会话。"""
        messages = store.load_messages("non-existent")
        assert messages == []

    def test_load_skips_corrupted_lines(self, store):
        """测试跳过损坏的行。"""
        file_path = store._get_file_path("session-1")
        with open(file_path, "w") as f:
            f.write('{"role": "user", "content": "valid"}\n')
            f.write("not valid json\n")
            f.write('{"role": "assistant", "content": "also valid"}\n')

        messages = store.load_messages("session-1")
        assert len(messages) == 2


class TestSessionExists:
    """测试 session_exists 方法。"""

    def test_existing_session(self, store):
        """测试存在的会话。"""
        store.append_message("session-1", "user", "Hello")
        assert store.session_exists("session-1") is True

    def test_nonexistent_session(self, store):
        """测试不存在的会话。"""
        assert store.session_exists("non-existent") is False


class TestListSessions:
    """测试 list_sessions 方法。"""

    def test_list_multiple_sessions(self, store):
        """测试列出多个会话。"""
        store.append_message("session-1", "user", "Hello")
        store.append_message("session-2", "user", "Hi")
        store.append_message("session-3", "user", "Hey")

        sessions = store.list_sessions()
        assert len(sessions) == 3
        assert "session-1" in sessions
        assert "session-2" in sessions
        assert "session-3" in sessions

    def test_list_empty_directory(self, store):
        """测试列出空目录。"""
        sessions = store.list_sessions()
        assert sessions == []


class TestDeleteSession:
    """测试 delete_session 方法。"""

    def test_delete_existing_session(self, store):
        """测试删除存在的会话。"""
        store.append_message("session-1", "user", "Hello")
        result = store.delete_session("session-1")

        assert result is True
        assert not store.session_exists("session-1")

    def test_delete_nonexistent_session(self, store):
        """测试删除不存在的会话。"""
        result = store.delete_session("non-existent")
        assert result is False


class TestGetMessageCount:
    """测试 get_message_count 方法。"""

    def test_count_messages(self, store):
        """测试统计消息数量。"""
        store.append_message("session-1", "user", "Hello")
        store.append_message("session-1", "assistant", "Hi")
        store.append_message("session-1", "user", "How are you?")

        count = store.get_message_count("session-1")
        assert count == 3

    def test_count_nonexistent_session(self, store):
        """测试统计不存在的会话。"""
        count = store.get_message_count("non-existent")
        assert count == 0
