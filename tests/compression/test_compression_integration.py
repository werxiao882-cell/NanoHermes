"""上下文压缩集成测试。

测试压缩功能与 TUI 对话循环、会话管理的集成。
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from src.session.session_db import SessionDB
from src.compression.compressor import ContextCompressor, SUMMARY_PREFIX


@pytest.fixture
def temp_db():
    """创建临时 SessionDB 实例。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_sessions.db"
        db = SessionDB(db_path)
        yield db
        db.close()


@pytest.fixture
def long_messages():
    """创建长对话消息列表。"""
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for i in range(200):
        messages.append({"role": "user", "content": f"User message {i}" * 50})
        messages.append({"role": "assistant", "content": f"Assistant response {i}" * 50})
    return messages


class TestCompressionWithSessionDB:
    """测试压缩与会话数据库的集成。"""

    def test_compress_and_save_to_session(self, temp_db, long_messages):
        """测试压缩后保存到会话。"""
        # 创建会话
        session_id = temp_db.create_session(title="压缩测试", model="gpt-4-turbo")

        # 保存原始消息
        for msg in long_messages[:10]:
            temp_db.insert_message(session_id, msg["role"], msg["content"])

        # 执行压缩
        compressor = ContextCompressor(model="gpt-4-turbo")
        compressor._generate_summary = lambda msgs, budget: "集成测试摘要"

        result = compressor.compress(long_messages)

        # 验证压缩结果
        assert "messages" in result
        assert len(result["messages"]) < len(long_messages)
        assert "summary" in result
        assert "集成测试摘要" in result["summary"]

    def test_session_split_integration(self, temp_db, long_messages):
        """测试会话分裂与数据库的集成。"""
        # 创建旧会话
        old_session_id = temp_db.create_session(
            title="旧会话", model="gpt-4-turbo", source="local"
        )

        # 保存消息
        for msg in long_messages[:20]:
            temp_db.insert_message(old_session_id, msg["role"], msg["content"])

        # 执行压缩
        compressor = ContextCompressor(model="gpt-4-turbo")
        compressor._generate_summary = lambda msgs, budget: "分裂测试摘要"
        result = compressor.compress(long_messages)

        # 执行会话分裂
        new_session_id = compressor.split_session(
            old_session_id,
            result["summary"],
            result["tail_messages"],
            session_db=temp_db,
        )

        # 验证旧会话已标记结束
        old_session = temp_db.get_session(old_session_id)
        assert old_session.get("end_reason") == "compression"

        # 验证新会话存在
        new_session = temp_db.get_session(new_session_id)
        assert new_session is not None
        assert new_session.get("parent_session_id") == old_session_id

        # 验证新会话有消息
        new_messages = temp_db.get_messages(new_session_id)
        assert len(new_messages) >= 1  # 至少包含摘要消息


class TestAutoCompressTrigger:
    """测试自动压缩触发逻辑。"""

    def test_check_post_response_context_exceeded(self):
        """测试 context_length_exceeded 触发压缩。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        response = {"error": {"type": "context_length_exceeded"}}
        assert compressor.check_post_response(response) is True

    def test_check_post_response_token_threshold(self):
        """测试 token 超阈值触发压缩。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        response = {"usage": {"prompt_tokens": compressor.threshold_tokens + 1000}}
        assert compressor.check_post_response(response) is True

    def test_check_preflight_large_context(self):
        """测试预飞行检查大上下文。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        messages = [{"role": "user", "content": "A" * 5000} for _ in range(200)]
        assert compressor.check_preflight(messages) is True

    def test_check_preflight_small_context(self):
        """测试预飞行检查小上下文。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        messages = [{"role": "user", "content": "Short"} for _ in range(5)]
        assert compressor.check_preflight(messages) is False

    def test_no_false_positive_normal_response(self):
        """测试正常响应不应触发压缩。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        response = {
            "content": "Hello!",
            "usage": {"prompt_tokens": 100, "completion_tokens": 10},
        }
        assert compressor.check_post_response(response) is False


class TestCompressionEdgeCases:
    """测试压缩边界情况。"""

    def test_compress_empty_messages(self):
        """测试压缩空消息列表。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        compressor._generate_summary = lambda msgs, budget: "Empty summary"
        result = compressor.compress([])
        # 即使空消息也应返回有效结果
        assert "messages" in result

    def test_compress_single_message(self):
        """测试压缩单条消息。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        compressor._generate_summary = lambda msgs, budget: "Single summary"
        messages = [{"role": "user", "content": "Hello"}]
        result = compressor.compress(messages)
        assert "messages" in result
        assert len(result["messages"]) >= 1

    def test_compress_preserves_system_message(self, long_messages):
        """测试压缩保留 system 消息。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        compressor._generate_summary = lambda msgs, budget: "Test summary"
        result = compressor.compress(long_messages)

        # 头部保护应包含 system 消息
        head = result["messages"][:compressor.protect_first_n]
        assert any(m.get("role") == "system" for m in head)

    def test_compression_reduces_message_count(self, long_messages):
        """测试压缩确实减少消息数。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        compressor._generate_summary = lambda msgs, budget: "Test summary"
        original_count = len(long_messages)

        result = compressor.compress(long_messages)
        compressed_count = len(result["messages"])

        assert compressed_count < original_count

    def test_summary_prefix_in_compressed_messages(self, long_messages):
        """测试压缩消息包含 SUMMARY_PREFIX。"""
        compressor = ContextCompressor(model="gpt-4-turbo")
        compressor._generate_summary = lambda msgs, budget: "Test summary"
        result = compressor.compress(long_messages)

        summary_msgs = [
            m for m in result["messages"]
            if SUMMARY_PREFIX in m.get("content", "")
        ]
        assert len(summary_msgs) == 1
