"""Tests for JSONL session history storage and session resume."""

import json
import tempfile
import time
from pathlib import Path

import pytest


@pytest.fixture
def jsonl_store(tmp_path):
    """Create a JsonlSessionStore with a temp directory."""
    from src.session.jsonl_store import JsonlSessionStore
    return JsonlSessionStore(tmp_path)


class TestJsonlSessionStore:
    """Tests for JsonlSessionStore."""

    def test_append_and_load_single_message(self, jsonl_store):
        """Test appending and loading a single message."""
        jsonl_store.append_message("sess1", "user", "Hello")
        messages = jsonl_store.load_messages("sess1")

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert "timestamp" in messages[0]

    def test_append_multiple_messages(self, jsonl_store):
        """Test appending multiple messages in order."""
        jsonl_store.append_message("sess1", "user", "Hi")
        jsonl_store.append_message("sess1", "assistant", "Hello!")
        jsonl_store.append_message("sess1", "user", "How are you?")

        messages = jsonl_store.load_messages("sess1")
        assert len(messages) == 3
        assert messages[0]["content"] == "Hi"
        assert messages[1]["content"] == "Hello!"
        assert messages[2]["content"] == "How are you?"

    def test_append_message_with_tool_calls(self, jsonl_store):
        """Test appending a message with tool calls."""
        tool_calls = [{
            "id": "call_1",
            "type": "function",
            "function": {"name": "terminal", "arguments": '{"command": "ls"}'},
        }]
        jsonl_store.append_message("sess1", "assistant", "Running command", tool_calls=tool_calls)

        messages = jsonl_store.load_messages("sess1")
        assert len(messages) == 1
        assert messages[0]["tool_calls"] == tool_calls

    def test_append_message_with_reasoning(self, jsonl_store):
        """Test appending a message with reasoning content."""
        jsonl_store.append_message(
            "sess1", "assistant", "The answer is 42",
            reasoning="Let me think... 6*7=42"
        )

        messages = jsonl_store.load_messages("sess1")
        assert messages[0]["reasoning"] == "Let me think... 6*7=42"

    def test_append_message_with_metadata(self, jsonl_store):
        """Test appending a message with metadata."""
        jsonl_store.append_message(
            "sess1", "user", "Test",
            metadata={"source": "cli", "version": "1.0"}
        )

        messages = jsonl_store.load_messages("sess1")
        assert messages[0]["metadata"] == {"source": "cli", "version": "1.0"}

    def test_load_messages_nonexistent_session(self, jsonl_store):
        """Test loading messages from a non-existent session returns empty list."""
        messages = jsonl_store.load_messages("nonexistent")
        assert messages == []

    def test_load_messages_corrupted_lines(self, jsonl_store):
        """Test loading messages with corrupted JSON lines."""
        file_path = jsonl_store._get_file_path("sess1")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('{"role": "user", "content": "good"}\n')
            f.write('this is not json\n')
            f.write('{"role": "assistant", "content": "also good"}\n')

        messages = jsonl_store.load_messages("sess1")
        assert len(messages) == 2
        assert messages[0]["content"] == "good"
        assert messages[1]["content"] == "also good"

    def test_session_exists(self, jsonl_store):
        """Test session_exists returns correct boolean."""
        assert jsonl_store.session_exists("nonexistent") is False

        jsonl_store.append_message("sess1", "user", "Hi")
        assert jsonl_store.session_exists("sess1") is True

    def test_list_sessions(self, jsonl_store):
        """Test listing all sessions."""
        jsonl_store.append_message("sess1", "user", "Hi")
        jsonl_store.append_message("sess2", "user", "Hello")
        jsonl_store.append_message("sess3", "user", "Hey")

        sessions = jsonl_store.list_sessions()
        assert set(sessions) == {"sess1", "sess2", "sess3"}

    def test_list_sessions_empty(self, jsonl_store):
        """Test listing sessions when none exist."""
        assert jsonl_store.list_sessions() == []

    def test_delete_session(self, jsonl_store):
        """Test deleting a session."""
        jsonl_store.append_message("sess1", "user", "Hi")
        assert jsonl_store.session_exists("sess1") is True

        result = jsonl_store.delete_session("sess1")
        assert result is True
        assert jsonl_store.session_exists("sess1") is False

    def test_delete_nonexistent_session(self, jsonl_store):
        """Test deleting a non-existent session returns False."""
        result = jsonl_store.delete_session("nonexistent")
        assert result is False

    def test_get_message_count(self, jsonl_store):
        """Test getting message count."""
        assert jsonl_store.get_message_count("sess1") == 0

        jsonl_store.append_message("sess1", "user", "Hi")
        jsonl_store.append_message("sess1", "assistant", "Hello")
        jsonl_store.append_message("sess1", "user", "Bye")

        assert jsonl_store.get_message_count("sess1") == 3

    def test_utf8_content(self, jsonl_store):
        """Test storing UTF-8 content including CJK characters."""
        jsonl_store.append_message("sess1", "user", "你好世界 🌍")
        jsonl_store.append_message("sess1", "assistant", "こんにちは")

        messages = jsonl_store.load_messages("sess1")
        assert messages[0]["content"] == "你好世界 🌍"
        assert messages[1]["content"] == "こんにちは"

    def test_timestamps_are_chronological(self, jsonl_store):
        """Test that timestamps are in chronological order."""
        jsonl_store.append_message("sess1", "user", "First")
        time.sleep(0.01)
        jsonl_store.append_message("sess1", "assistant", "Second")

        messages = jsonl_store.load_messages("sess1")
        assert messages[0]["timestamp"] < messages[1]["timestamp"]


class TestSessionResumeIntegration:
    """Integration tests for session resume functionality."""

    def test_resume_loads_jsonl_history(self, tmp_path):
        """Test that resume loads JSONL history into messages."""
        from src.session.jsonl_store import JsonlSessionStore

        store = JsonlSessionStore(tmp_path)
        store.append_message("sess1", "user", "Hello")
        store.append_message("sess1", "assistant", "Hi there!")
        store.append_message("sess1", "user", "How are you?")

        messages = store.load_messages("sess1")
        assert len(messages) == 3

        # Verify messages can be converted to OpenAI format
        openai_messages = []
        for msg in messages:
            role = msg.get("role")
            if role == "system":
                continue
            openai_msg = {"role": role}
            if "content" in msg:
                openai_msg["content"] = msg["content"]
            if "tool_calls" in msg:
                openai_msg["tool_calls"] = msg["tool_calls"]
            openai_messages.append(openai_msg)

        assert len(openai_messages) == 3
        assert openai_messages[0]["role"] == "user"
        assert openai_messages[0]["content"] == "Hello"
        assert openai_messages[1]["role"] == "assistant"
        assert openai_messages[1]["content"] == "Hi there!"

    def test_resume_with_tool_calls_history(self, tmp_path):
        """Test resume loads history with tool calls."""
        from src.session.jsonl_store import JsonlSessionStore

        store = JsonlSessionStore(tmp_path)
        store.append_message("sess1", "user", "List files")
        store.append_message(
            "sess1", "assistant", "Running ls",
            tool_calls=[{
                "id": "call_1",
                "type": "function",
                "function": {"name": "terminal", "arguments": '{"command": "ls"}'},
            }],
        )
        store.append_message(
            "sess1", "tool", "file1.txt\nfile2.txt",
            tool_call_id="call_1",
        )
        store.append_message("sess1", "assistant", "Found 2 files")

        messages = store.load_messages("sess1")
        assert len(messages) == 4
        assert messages[1]["tool_calls"][0]["function"]["name"] == "terminal"
        assert messages[2]["tool_call_id"] == "call_1"
