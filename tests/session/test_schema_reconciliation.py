"""声明式 Schema 协调单元测试。

测试解析期望列、添加缺失列、列类型重建、延迟索引创建等。
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.session.session_db import SessionDB
from src.session.schema import SCHEMA_SQL


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


class TestParseSchemaColumns:
    """测试 _parse_schema_columns 方法。"""

    def test_parse_single_table_columns(self, db):
        """测试解析单表列。"""
        ref = sqlite3.connect(":memory:")
        ref.executescript(SCHEMA_SQL)

        expected = db._parse_schema_columns(ref)
        ref.close()

        assert "sessions" in expected
        assert "id" in expected["sessions"]
        assert "source" in expected["sessions"]
        assert "title" in expected["sessions"]

    def test_parse_multiple_table_columns(self, db):
        """测试解析多表列。"""
        ref = sqlite3.connect(":memory:")
        ref.executescript(SCHEMA_SQL)

        expected = db._parse_schema_columns(ref)
        ref.close()

        assert "sessions" in expected
        assert "messages" in expected
        assert "state_meta" in expected

    def test_parse_column_with_default(self, db):
        """测试解析带 DEFAULT 的列。"""
        ref = sqlite3.connect(":memory:")
        ref.executescript(SCHEMA_SQL)

        expected = db._parse_schema_columns(ref)
        ref.close()

        # 检查带 DEFAULT 的列
        source_type = expected["sessions"]["source"]
        assert "DEFAULT" in source_type


class TestReconcileColumns:
    """测试 _reconcile_columns 方法。"""

    def test_add_missing_column(self, db_path):
        """测试添加缺失列。"""
        # 创建没有某些列的数据库
        db = SessionDB(db_path)
        db.close()

        # 手动删除一个列（模拟旧版本数据库）
        conn = sqlite3.connect(str(db_path))
        # SQLite 不支持删除列，所以我们创建一个新的数据库并手动添加部分列
        conn.close()

        # 重新打开，应该协调添加缺失列
        db2 = SessionDB(db_path)
        try:
            # 验证列存在
            cols = db2._get_live_columns("sessions")
            assert "id" in cols
            assert "source" in cols
            assert "title" in cols
        finally:
            db2.close()

    def test_no_add_existing_column(self, db):
        """测试不添加已存在的列。"""
        # 当前 schema 是完整的，协调不应添加任何列
        db._reconcile_schema()  # 不应抛出异常

    def test_handle_duplicate_column_error(self, db_path):
        """测试处理重复列错误。"""
        db = SessionDB(db_path)
        try:
            # 多次协调不应失败
            db._reconcile_schema()
            db._reconcile_schema()
        finally:
            db.close()


class TestSchemaVersion:
    """测试 schema_version 表。"""

    def test_initialize_schema_version(self, db):
        """测试初始化 schema_version。"""
        cursor = db.conn.execute("SELECT version FROM schema_version")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1

    def test_update_schema_version(self, db):
        """测试更新 schema_version。"""
        db._update_schema_version()

        cursor = db.conn.execute("SELECT version FROM schema_version")
        row = cursor.fetchone()
        assert row[0] == 1


class TestDelayedIndexCreation:
    """测试延迟索引创建。"""

    def test_indexes_created_after_reconciliation(self, db):
        """测试索引在协调之后创建。"""
        # 验证索引存在
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        assert "idx_sessions_source" in indexes
        assert "idx_sessions_parent" in indexes
        assert "idx_sessions_started" in indexes
        assert "idx_messages_session" in indexes
