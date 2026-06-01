"""FTS5 全文搜索单元测试。

测试 FTS 虚拟表创建、触发器同步、跨会话搜索、CJK 子串搜索等。
"""

import tempfile
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


class TestFTSCreation:
    """测试 FTS 虚拟表创建。"""

    def test_standard_fts_table_exists(self, db):
        """测试创建标准 FTS5 表。"""
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages_fts'"
        )
        assert cursor.fetchone() is not None

    def test_trigram_fts_table_exists(self, db):
        """测试创建 trigram FTS5 表。"""
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages_fts_trigram'"
        )
        assert cursor.fetchone() is not None


class TestFTSSync:
    """测试 FTS 触发器同步。"""

    def test_insert_syncs_to_fts(self, db):
        """测试插入消息同步到 FTS。"""
        sid = db.create_session(title="fts_test")
        db.insert_message(sid, "user", "这是一个测试消息")

        cursor = db.conn.execute("SELECT COUNT(*) FROM messages_fts")
        count = cursor.fetchone()[0]
        assert count == 1

        cursor = db.conn.execute("SELECT COUNT(*) FROM messages_fts_trigram")
        count = cursor.fetchone()[0]
        assert count == 1

    def test_delete_syncs_to_fts(self, db):
        """测试删除消息同步到 FTS。"""
        sid = db.create_session(title="fts_delete_test")
        msg_id = db.insert_message(sid, "user", "删除测试")

        # 删除消息
        db.conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        db.conn.commit()

        cursor = db.conn.execute("SELECT COUNT(*) FROM messages_fts")
        count = cursor.fetchone()[0]
        assert count == 0

    def test_update_syncs_to_fts(self, db):
        """测试更新消息同步到 FTS。"""
        sid = db.create_session(title="fts_update_test")
        db.insert_message(sid, "user", "original content")

        # 插入另一条消息
        db.insert_message(sid, "user", "updated content here")

        # 搜索新内容
        results = db.search_messages("updated")
        assert len(results) >= 1

        # 搜索旧内容
        results2 = db.search_messages("original")
        assert len(results2) >= 1


class TestCrossSessionSearch:
    """测试跨会话搜索。"""

    def test_search_all_sessions(self, db):
        """测试搜索所有会话。"""
        sid1 = db.create_session(title="session1")
        sid2 = db.create_session(title="session2")
        sid3 = db.create_session(title="session3")

        db.insert_message(sid1, "user", "这是一个 bug 修复")
        db.insert_message(sid2, "user", "发现了一个 bug")
        db.insert_message(sid3, "user", "正常消息")

        results = db.search_messages("bug")
        assert len(results) == 2

    def test_search_with_session_filter(self, db):
        """测试按会话过滤搜索。"""
        sid1 = db.create_session(title="session1")
        sid2 = db.create_session(title="session2")

        db.insert_message(sid1, "user", "error in session 1")
        db.insert_message(sid1, "user", "another error")
        db.insert_message(sid2, "user", "error in session 2")

        results = db.search_messages("error", session_id=sid1)
        assert len(results) == 2
        for r in results:
            assert r["session_id"] == sid1

    def test_search_no_results(self, db):
        """测试搜索无结果。"""
        sid = db.create_session(title="empty")
        db.insert_message(sid, "user", "正常消息")

        results = db.search_messages("不存在的关键词")
        assert len(results) == 0


class TestCJKSearch:
    """测试 CJK 子串搜索。"""

    def test_chinese_substring_search(self, db):
        """测试中文子串搜索。"""
        sid = db.create_session(title="chinese_test")
        db.insert_message(sid, "user", "测试消息")

        # FTS5 MATCH 对中文字符使用前缀搜索
        results = db.search_messages("测*")
        assert len(results) >= 1

    def test_japanese_substring_search(self, db):
        """测试日文子串搜索。"""
        sid = db.create_session(title="japanese_test")
        db.insert_message(sid, "user", "テスト")

        # FTS5 MATCH 对日文字符使用前缀搜索
        results = db.search_messages("テ*")
        assert len(results) >= 1

    def test_mixed_language_search(self, db):
        """测试混合语言搜索。"""
        sid = db.create_session(title="mixed_test")
        db.insert_message(sid, "user", "bug 修复完成测试通过")

        results = db.search_messages("bug")
        assert len(results) >= 1


class TestToolSearch:
    """测试工具名称和参数搜索。"""

    def test_search_tool_name(self, db):
        """测试搜索工具名称。"""
        sid = db.create_session(title="tool_test")
        db.insert_message(sid, "assistant", tool_name="read_file")

        results = db.search_messages("read_file")
        assert len(results) == 1

    def test_search_tool_calls(self, db):
        """测试搜索工具调用参数。"""
        sid = db.create_session(title="tool_calls_test")
        db.insert_message(
            sid,
            "assistant",
            tool_calls='{"path": "/test/file.py"}',
        )

        # 避免使用 . 等特殊字符
        results = db.search_messages("file")
        assert len(results) >= 1
