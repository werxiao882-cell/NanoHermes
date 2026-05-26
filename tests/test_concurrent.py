"""并发测试：SessionDB WAL 模式并发访问。

测试场景：
1. 多读单写（WAL 模式特性）
2. 写锁竞争 + 抖动重试
3. 并发插入消息
4. 并发搜索
"""

import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_home(tmp_path):
    """模拟临时 HOME 目录。"""
    with patch.object(Path, "home", return_value=tmp_path):
        yield tmp_path


class TestConcurrentReads:
    """测试并发读取。"""

    def test_multiple_concurrent_reads(self, temp_home):
        """测试多个线程同时读取会话数据。"""
        from src.session.session_db import SessionDB

        db_path = temp_home / ".nanohermes" / "sessions.db"
        with SessionDB(db_path) as db:
            session_id = db.create_session(model="test", provider="test")
            for i in range(10):
                db.insert_message(session_id, "user", f"Message {i}")

        results = []
        errors = []

        def read_session():
            try:
                with SessionDB(db_path) as db:
                    messages = db.get_messages(session_id)
                    results.append(len(messages))
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=read_session) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(r == 10 for r in results)


class TestConcurrentWrites:
    """测试并发写入（写锁竞争 + 抖动重试）。"""

    def test_concurrent_session_creation(self, temp_home):
        """测试多个线程同时创建会话。"""
        from src.session.session_db import SessionDB

        db_path = temp_home / ".nanohermes" / "sessions.db"
        created_ids = []
        errors = []
        lock = threading.Lock()

        def create_session():
            try:
                with SessionDB(db_path) as db:
                    sid = db.create_session(model="test", provider="test")
                    with lock:
                        created_ids.append(sid)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=create_session) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(created_ids) == 5
        # 所有 ID 应该唯一
        assert len(set(created_ids)) == 5

    def test_concurrent_message_insert(self, temp_home):
        """测试多个线程同时插入消息到同一会话。"""
        from src.session.session_db import SessionDB

        db_path = temp_home / ".nanohermes" / "sessions.db"
        with SessionDB(db_path) as db:
            session_id = db.create_session()

        errors = []
        lock = threading.Lock()

        def insert_messages(start_idx):
            try:
                with SessionDB(db_path) as db:
                    for i in range(5):
                        db.insert_message(session_id, "user", f"Thread {start_idx} msg {i}")
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=insert_messages, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        # 验证所有消息都插入
        with SessionDB(db_path) as db:
            messages = db.get_messages(session_id)
            assert len(messages) == 15  # 3 threads * 5 messages


class TestConcurrentReadWrite:
    """测试并发读写混合。"""

    def test_read_while_writing(self, temp_home):
        """测试写入时读取。"""
        from src.session.session_db import SessionDB

        db_path = temp_home / ".nanohermes" / "sessions.db"
        with SessionDB(db_path) as db:
            session_id = db.create_session()

        write_done = threading.Event()
        read_count = [0]
        errors = []
        lock = threading.Lock()

        def writer():
            try:
                with SessionDB(db_path) as db:
                    for i in range(10):
                        db.insert_message(session_id, "user", f"Msg {i}")
                        time.sleep(0.01)
            except Exception as e:
                with lock:
                    errors.append(f"writer: {e}")
            finally:
                write_done.set()

        def reader():
            try:
                while not write_done.is_set():
                    with SessionDB(db_path) as db:
                        messages = db.get_messages(session_id)
                        read_count[0] += 1
                    time.sleep(0.02)
            except Exception as e:
                with lock:
                    errors.append(f"reader: {e}")

        w = threading.Thread(target=writer)
        r = threading.Thread(target=reader)
        w.start()
        r.start()
        w.join()
        r.join()

        assert len(errors) == 0
        assert read_count[0] > 0  # 至少读取了一次


class TestConcurrentTokenUpdates:
    """测试并发 token 计数更新。"""

    def test_incremental_token_updates(self, temp_home):
        """测试增量 token 计数的并发更新。"""
        from src.session.session_db import SessionDB

        db_path = temp_home / ".nanohermes" / "sessions.db"
        with SessionDB(db_path) as db:
            session_id = db.create_session()

        errors = []
        lock = threading.Lock()

        def update_tokens(count):
            try:
                with SessionDB(db_path) as db:
                    db.update_token_counts(
                        session_id,
                        input_tokens=count,
                        output_tokens=count * 2,
                        incremental=True,
                    )
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=update_tokens, args=(100,)) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        with SessionDB(db_path) as db:
            session = db.get_session(session_id)
            assert session["input_tokens"] == 500  # 5 * 100
            assert session["output_tokens"] == 1000  # 5 * 200


class TestConcurrentSearch:
    """测试并发搜索。"""

    def test_concurrent_fts_search(self, temp_home):
        """测试多个线程同时执行 FTS 搜索。"""
        from src.session.session_db import SessionDB

        db_path = temp_home / ".nanohermes" / "sessions.db"
        with SessionDB(db_path) as db:
            session_id = db.create_session()
            for i in range(20):
                db.insert_message(session_id, "user", f"Python test message {i}")
                db.insert_message(session_id, "assistant", f"Response about Python {i}")

        results = []
        errors = []
        lock = threading.Lock()

        def search():
            try:
                with SessionDB(db_path) as db:
                    matches = db.search_messages("Python", session_id)
                    with lock:
                        results.append(len(matches))
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=search) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(r > 0 for r in results)
