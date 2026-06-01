"""会话标题管理单元测试。

测试设置标题、标题唯一性、标题解析、lineage 标题生成、标题清理等。
"""

import tempfile
from pathlib import Path

import pytest

from src.session.session_db import SessionDB, sanitize_title


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


class TestSetSessionTitle:
    """测试 set_session_title 方法。"""

    def test_set_new_title(self, db):
        """测试设置新标题。"""
        sid = db.create_session(title="old")
        db.set_session_title(sid, "New Title")

        title = db.get_session_title(sid)
        assert title == "New Title"

    def test_update_own_title(self, db):
        """测试更新自己的标题。"""
        sid = db.create_session(title="original")
        db.set_session_title(sid, "updated")

        title = db.get_session_title(sid)
        assert title == "updated"


class TestSanitizeTitle:
    """测试 sanitize_title 函数。"""

    def test_strip_control_characters(self):
        """测试剥离控制字符。"""
        # 零宽字符
        result = sanitize_title("Hello\u200bWorld")
        assert result == "HelloWorld"

    def test_collapse_whitespace(self):
        """测试折叠空白。"""
        result = sanitize_title("  Hello   World  ")
        assert result == "Hello World"

    def test_title_too_long(self):
        """测试标题过长。"""
        with pytest.raises(ValueError, match="Title too long"):
            sanitize_title("A" * 101)

    def test_empty_title(self):
        """测试空标题。"""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            sanitize_title("   ")


class TestResolveSessionByTitle:
    """测试 resolve_session_by_title 方法。"""

    def test_exact_title_match(self, db):
        """测试精确标题匹配。"""
        sid = db.create_session(title="My Session")

        result = db.resolve_session_by_title("My Session")
        assert result == sid

    def test_numbered_variant_match(self, db):
        """测试编号变体匹配。"""
        sid1 = db.create_session(title="My Session #2")
        sid2 = db.create_session(title="My Session #3")

        # 搜索 "My Session" 应该返回最新的编号变体
        result = db.resolve_session_by_title("My Session")
        assert result is not None

    def test_title_not_found(self, db):
        """测试标题不存在。"""
        db.create_session(title="Existing")

        result = db.resolve_session_by_title("Non-existent")
        assert result is None


class TestGetNextTitleInLineage:
    """测试 get_next_title_in_lineage 方法。"""

    def test_generate_first_numbered_title(self, db):
        """测试生成第一个编号标题。"""
        db.create_session(title="My Session")

        result = db.get_next_title_in_lineage("My Session")
        assert result == "My Session #2"

    def test_generate_subsequent_numbered_title(self, db):
        """测试生成后续编号标题。"""
        db.create_session(title="My Session")
        db.create_session(title="My Session #2")

        result = db.get_next_title_in_lineage("My Session")
        assert result == "My Session #3"

    def test_strip_existing_numbered_suffix(self, db):
        """测试剥离现有编号后缀。"""
        db.create_session(title="My Session #2")

        result = db.get_next_title_in_lineage("My Session #2")
        assert result == "My Session #3"

    def test_no_existing_sessions(self, db):
        """测试无现有会话时返回基础标题。"""
        result = db.get_next_title_in_lineage("New Session")
        assert result == "New Session"
