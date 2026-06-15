"""Session Splitting 和 on_pre_compress 钩子单元测试。"""

import pytest
from unittest.mock import MagicMock, patch
from src.compression.compressor import ContextCompressor, SUMMARY_PREFIX


@pytest.fixture
def compressor():
    """创建 ContextCompressor 实例。"""
    return ContextCompressor(model="gpt-4-turbo")


@pytest.fixture
def messages_with_tail():
    """创建包含头部和尾部的消息列表。"""
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for i in range(10):
        messages.append({"role": "user", "content": f"User message {i}" * 10})
        messages.append({"role": "assistant", "content": f"Assistant response {i}" * 10})
    return messages


class TestSessionSplitting:
    """测试 Session Splitting 功能。"""

    def test_split_session_creates_new_session(self, compressor, messages_with_tail):
        """测试新 session 创建。"""
        compressor._generate_summary = lambda msgs, budget, model_caller=None: "Test summary"
        result = compressor.compress(messages_with_tail)

        # Mock session_db
        mock_session_db = MagicMock()
        mock_session_db.get_session.return_value = {
            "id": "old-session",
            "title": "Test Session",
            "model": "gpt-4",
            "source": "local",
            "system_prompt": "You are helpful.",
        }

        new_session_id = compressor.split_session(
            "old-session",
            result["summary"],
            result["tail_messages"],
            session_db=mock_session_db,
        )

        # 验证新 session ID 生成
        assert new_session_id is not None
        assert new_session_id != "old-session"

        # 验证旧 session 标记为 compression 结束
        mock_session_db.end_session.assert_called_once_with("old-session", end_reason="compression")

        # 验证新 session 创建
        mock_session_db.create_session.assert_called_once()
        call_kwargs = mock_session_db.create_session.call_args[1]
        assert call_kwargs["session_id"] == new_session_id
        assert call_kwargs["parent_session_id"] == "old-session"
        assert call_kwargs["title"] == "Test Session"

    def test_parent_session_id_lineage(self, compressor, messages_with_tail):
        """测试 parent_session_id 血缘链。"""
        compressor._generate_summary = lambda msgs, budget, model_caller=None: "Test summary"
        result = compressor.compress(messages_with_tail)

        mock_session_db = MagicMock()
        mock_session_db.get_session.return_value = {"id": "old-session"}

        new_session_id = compressor.split_session(
            "old-session",
            result["summary"],
            result["tail_messages"],
            session_db=mock_session_db,
        )

        # 验证 parent_session_id 指向旧 session
        call_kwargs = mock_session_db.create_session.call_args[1]
        assert call_kwargs["parent_session_id"] == "old-session"

    def test_summary_as_first_message(self, compressor, messages_with_tail):
        """测试摘要作为第一条消息。"""
        compressor._generate_summary = lambda msgs, budget, model_caller=None: "Test summary"
        result = compressor.compress(messages_with_tail)

        mock_session_db = MagicMock()
        mock_session_db.get_session.return_value = {"id": "old-session"}

        compressor.split_session(
            "old-session",
            result["summary"],
            result["tail_messages"],
            session_db=mock_session_db,
        )

        # 验证摘要作为第一条消息插入
        insert_calls = mock_session_db.insert_message.call_args_list
        assert len(insert_calls) >= 1
        first_call = insert_calls[0]
        assert first_call[1]["role"] == "system"
        assert SUMMARY_PREFIX in first_call[1]["content"]
        assert "Test summary" in first_call[1]["content"]

    def test_tail_messages_migrated(self, compressor, messages_with_tail):
        """测试尾部消息迁移。"""
        compressor._generate_summary = lambda msgs, budget, model_caller=None: "Test summary"
        result = compressor.compress(messages_with_tail)
        tail_count = result["tail_count"]

        mock_session_db = MagicMock()
        mock_session_db.get_session.return_value = {"id": "old-session"}

        compressor.split_session(
            "old-session",
            result["summary"],
            result["tail_messages"],
            session_db=mock_session_db,
        )

        # 验证尾部消息被插入到新 session
        insert_calls = mock_session_db.insert_message.call_args_list
        # 第一条是摘要，后面是尾部消息
        assert len(insert_calls) == 1 + tail_count


class TestOnPreCompressHook:
    """测试 on_pre_compress 钩子。"""

    def test_hook_called_before_compression(self, compressor, messages_with_tail):
        """测试钩子在压缩前调用。"""
        call_order = []

        def mock_pre_compress(messages):
            call_order.append("pre_compress")
            return "Extracted user preference: likes Python"

        def mock_generate_summary(messages, budget, model_caller=None):
            call_order.append("generate_summary")
            return "Test summary"

        compressor.set_pre_compress_callback(mock_pre_compress)
        compressor._generate_summary = mock_generate_summary

        result = compressor.compress(messages_with_tail)

        # 验证调用顺序
        assert call_order == ["pre_compress", "generate_summary"]
        # 验证 pre_compress 信息被合并到摘要
        assert "Extracted user preference: likes Python" in result["summary"]

    def test_provider_extracts_information(self, compressor, messages_with_tail):
        """测试 Provider 提取信息。"""
        def mock_pre_compress(messages):
            # 模拟 Honcho 从消息中提取用户偏好
            user_messages = [m for m in messages if m.get("role") == "user"]
            return f"Extracted from {len(user_messages)} user messages"

        compressor.set_pre_compress_callback(mock_pre_compress)
        compressor._generate_summary = lambda msgs, budget, model_caller=None: "Base summary"

        result = compressor.compress(messages_with_tail)

        assert "Extracted from" in result["summary"]

    def test_hook_failure_does_not_stop_compression(self, compressor, messages_with_tail):
        """测试钩子失败不影响压缩。"""
        def failing_pre_compress(messages):
            raise RuntimeError("Provider failed to extract information")

        compressor.set_pre_compress_callback(failing_pre_compress)
        compressor._generate_summary = lambda msgs, budget, model_caller=None: "Test summary"

        # 不应抛出异常
        result = compressor.compress(messages_with_tail)

        # 压缩仍应成功
        assert result["summary"] == "Test summary"
