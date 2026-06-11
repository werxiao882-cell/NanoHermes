"""会话生命周期管理单元测试。

测试创建、结束、恢复、分支、压缩延续链、token 计数更新等。
"""

import tempfile
import time
from pathlib import Path

import pytest

from src.session.session_db import SessionDB


@pytest.fixture
def db_path():
    """创建临时数据库路径。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir) / "test.db"


@pytest.fixture
def db(db_path):
    """创建 SessionDB 实例。"""
    db = SessionDB(db_path)
    yield db
    db.close()


class TestCreateSession:
    """测试 create_session 方法。"""

    def test_create_new_session(self, db):
        """测试创建新会话。"""
        sid = db.create_session(title="test", model="gpt-4")

        session = db.get_session(sid)
        assert session is not None
        assert session["id"] == sid
        assert session["title"] == "test"
        assert session["model"] == "gpt-4"
        assert session["source"] == "local"
        assert session["started_at"] is not None

    def test_idempotent_create(self, db):
        """测试幂等创建。"""
        sid = db.create_session(session_id="same-id", title="first")
        sid2 = db.create_session(session_id="same-id", title="second")

        # 应该返回相同的 ID
        assert sid == sid2

        # 只有一条记录
        sessions = db.list_sessions()
        assert len(sessions) == 1

    def test_create_with_full_params(self, db):
        """测试创建会话带完整参数。"""
        sid = db.create_session(
            session_id="full-test",
            source="telegram",
            user_id="user-123",
            model="gpt-4",
            parent_session_id=None,
            title="Full Test",
            system_prompt="You are a helpful assistant.",
        )

        session = db.get_session(sid)
        assert session["source"] == "telegram"
        assert session["user_id"] == "user-123"
        assert session["model"] == "gpt-4"
        assert session["system_prompt"] == "You are a helpful assistant."


class TestEndAndReopenSession:
    """测试 end_session 和 reopen_session 方法。"""

    def test_end_session(self, db):
        """测试结束会话。"""
        sid = db.create_session(title="end_test")
        db.end_session(sid, "user_exit")

        session = db.get_session(sid)
        assert session["ended_at"] is not None
        assert session["end_reason"] == "user_exit"

    def test_already_ended_session_not_duplicated(self, db):
        """测试已结束会话不重复结束。"""
        sid = db.create_session(title="end_test")
        db.end_session(sid, "first_reason")

        # 再次结束
        db.end_session(sid, "second_reason")

        session = db.get_session(sid)
        # 第一次的 end_reason 获胜
        assert session["end_reason"] == "first_reason"

    def test_reopen_session(self, db):
        """测试恢复会话。"""
        sid = db.create_session(title="reopen_test")
        db.end_session(sid, "user_exit")

        # 恢复
        db.reopen_session(sid)

        session = db.get_session(sid)
        assert session["ended_at"] is None
        assert session["end_reason"] is None


class TestCompressionLineage:
    """测试压缩延续 lineage。"""

    def test_create_compression_continuation(self, db):
        """测试创建压缩延续会话。"""
        sid1 = db.create_session(title="original")
        db.end_session(sid1, "compression")

        # 创建延续会话
        sid2 = db.branch_session(parent_session_id=sid1, title="continuation")

        session2 = db.get_session(sid2)
        assert session2["parent_session_id"] == sid1

    def test_get_compression_tip(self, db):
        """测试获取压缩延续 tip。"""
        # 创建压缩延续链：session1 → session2 → session3
        sid1 = db.create_session(title="original")
        db.end_session(sid1, "compression")

        sid2 = db.create_session(parent_session_id=sid1, title="continuation1")
        db.end_session(sid2, "compression")

        sid3 = db.create_session(parent_session_id=sid2, title="continuation2")

        # 获取 tip
        tip = db.get_compression_tip(sid1)
        assert tip == sid3

    def test_exclude_delegated_child(self, db):
        """测试排除委托子节点。"""
        # 创建父会话（未结束）
        sid1 = db.create_session(title="parent")

        # 创建子会话（在父会话还活着时创建）
        sid2 = db.create_session(parent_session_id=sid1, title="child")

        # 获取 compression tip 应该返回 sid1（不是 sid2）
        tip = db.get_compression_tip(sid1)
        assert tip == sid1


class TestUpdateTokenCounts:
    """测试 update_token_counts 方法。"""

    def test_incremental_update(self, db):
        """测试增量更新 token 计数。"""
        sid = db.create_session(title="token_test")

        # 初始为 0
        session = db.get_session(sid)
        assert session["input_tokens"] == 0

        # 增量更新
        db.update_token_counts(sid, input_tokens=100, output_tokens=50)

        session = db.get_session(sid)
        assert session["input_tokens"] == 100
        assert session["output_tokens"] == 50

        # 再次增量更新
        db.update_token_counts(sid, input_tokens=50, output_tokens=25)

        session = db.get_session(sid)
        assert session["input_tokens"] == 150
        assert session["output_tokens"] == 75

    def test_absolute_update(self, db):
        """测试绝对更新 token 计数。"""
        sid = db.create_session(title="token_test")
        db.update_token_counts(sid, input_tokens=100, output_tokens=50)

        # 绝对更新
        db.update_token_counts(
            sid,
            input_tokens=500,
            output_tokens=200,
            incremental=False,
        )

        session = db.get_session(sid)
        assert session["input_tokens"] == 500
        assert session["output_tokens"] == 200

    def test_update_model_info(self, db):
        """测试更新模型信息。"""
        sid = db.create_session(title="model_test", model="gpt-3.5")

        session = db.get_session(sid)
        assert session["model"] == "gpt-3.5"


class TestGetSession:
    """测试 get_session 方法。"""

    def test_get_existing_session(self, db):
        """测试获取存在的会话。"""
        sid = db.create_session(title="get_test", model="gpt-4")

        session = db.get_session(sid)
        assert session is not None
        assert session["id"] == sid
        assert session["title"] == "get_test"

    def test_get_nonexistent_session(self, db):
        """测试获取不存在的会话。"""
        session = db.get_session("non-existent")
        assert session is None


class TestUpdateSystemPrompt:
    """测试 update_system_prompt 方法。"""

    def test_update_system_prompt(self, db):
        """测试更新系统提示。"""
        sid = db.create_session(title="prompt_test")
        db.update_system_prompt(sid, "You are a helpful assistant.")

        session = db.get_session(sid)
        assert session["system_prompt"] == "You are a helpful assistant."
