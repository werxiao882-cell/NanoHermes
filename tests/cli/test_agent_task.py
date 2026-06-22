"""AgentTask 和 AgentTaskRegistry 单元测试。

测试覆盖：
- AgentTask 属性（is_running, is_terminal, format_duration）
- AgentTaskRegistry 注册、获取、更新、增量消息
- 线程安全并发写入
"""

import threading
import time

import pytest

from src.cli.agent_task import (
    AgentTask,
    AgentTaskProgress,
    AgentTaskRegistry,
    AgentTaskStatus,
)


# ============================================================================
# AgentTask 属性测试
# ============================================================================

class TestAgentTask:
    def test_is_running(self):
        task = AgentTask(id="t1", name="test", description="test desc")
        task.status = AgentTaskStatus.RUNNING
        assert task.is_running is True
        task.status = AgentTaskStatus.COMPLETED
        assert task.is_running is False

    def test_is_terminal(self):
        task = AgentTask(id="t1", name="test", description="test desc")
        for status in (AgentTaskStatus.COMPLETED, AgentTaskStatus.FAILED, AgentTaskStatus.TIMEOUT):
            task.status = status
            assert task.is_terminal is True
        for status in (AgentTaskStatus.PENDING, AgentTaskStatus.RUNNING):
            task.status = status
            assert task.is_terminal is False

    def test_format_duration_seconds(self):
        task = AgentTask(id="t1", name="test", description="test desc")
        task.start_time = time.time() - 45
        assert task.format_duration() == "45s"

    def test_format_duration_minutes(self):
        task = AgentTask(id="t1", name="test", description="test desc")
        task.start_time = time.time() - 150
        assert task.format_duration() == "2m30s"

    def test_format_duration_with_end_time(self):
        task = AgentTask(id="t1", name="test", description="test desc")
        task.start_time = 1000.0
        task.end_time = 1060.0
        assert task.format_duration() == "1m0s"

    def test_request_abort(self):
        task = AgentTask(id="t1", name="test", description="test desc")
        assert task.abort_event.is_set() is False
        task.request_abort()
        assert task.abort_event.is_set() is True


# ============================================================================
# AgentTaskRegistry 测试
# ============================================================================

class TestAgentTaskRegistry:
    def test_register_and_get(self):
        registry = AgentTaskRegistry()
        task = registry.register("a1b2", "auth-refactor", "Refactor auth module")
        assert task.id == "a1b2"
        assert task.name == "auth-refactor"
        assert task.status == AgentTaskStatus.RUNNING
        assert registry.get("a1b2") is task

    def test_get_nonexistent(self):
        registry = AgentTaskRegistry()
        assert registry.get("nonexistent") is None

    def test_get_by_name_exact(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "desc")
        assert registry.get_by_name("auth-refactor") is not None

    def test_get_by_name_prefix(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "desc")
        assert registry.get_by_name("a1b2") is not None

    def test_get_by_name_no_match(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "desc")
        assert registry.get_by_name("nonexistent") is None

    def test_get_all(self):
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")
        registry.register("t2", "task-2", "desc2")
        tasks = registry.get_all()
        assert len(tasks) == 2
        assert tasks[0].id == "t1"
        assert tasks[1].id == "t2"

    def test_get_all_running(self):
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")
        registry.register("t2", "task-2", "desc2")
        registry.update_status("t2", AgentTaskStatus.COMPLETED)
        running = registry.get_all_running()
        assert len(running) == 1
        assert running[0].id == "t1"

    def test_update_status_completed(self):
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")
        registry.update_status("t1", AgentTaskStatus.COMPLETED)
        task = registry.get("t1")
        assert task.status == AgentTaskStatus.COMPLETED
        assert task.end_time is not None

    def test_update_status_failed(self):
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")
        registry.update_status("t1", AgentTaskStatus.FAILED)
        task = registry.get("t1")
        assert task.status == AgentTaskStatus.FAILED
        assert task.end_time is not None

    def test_update_progress(self):
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")
        registry.update_progress("t1", last_activity="patching auth.py", token_count=5200)
        task = registry.get("t1")
        assert task.progress.last_activity == "patching auth.py"
        assert task.progress.token_count == 5200
        assert task.progress.last_activity_time > 0

    def test_append_message(self):
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")
        registry.append_message("t1", {"role": "user", "content": "hello"})
        registry.append_message("t1", {"role": "assistant", "content": "hi"})
        task = registry.get("t1")
        assert len(task.messages) == 2
        assert task.messages[0]["role"] == "user"
        assert task.messages[1]["role"] == "assistant"

    def test_get_new_messages_first_time(self):
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")
        registry.append_message("t1", {"role": "user", "content": "msg1"})
        registry.append_message("t1", {"role": "assistant", "content": "msg2"})
        registry.append_message("t1", {"role": "tool", "content": "msg3"})

        new_msgs, count = registry.get_new_messages("t1")
        assert count == 3
        assert len(new_msgs) == 3

    def test_get_new_messages_incremental(self):
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")
        registry.append_message("t1", {"role": "user", "content": "msg1"})
        registry.append_message("t1", {"role": "assistant", "content": "msg2"})

        # 首次获取
        new_msgs, count = registry.get_new_messages("t1")
        assert count == 2

        # 追加新消息
        registry.append_message("t1", {"role": "tool", "content": "msg3"})
        registry.append_message("t1", {"role": "assistant", "content": "msg4"})

        # 再次获取（增量）
        new_msgs2, count2 = registry.get_new_messages("t1")
        assert count2 == 2
        assert new_msgs2[0]["content"] == "msg3"
        assert new_msgs2[1]["content"] == "msg4"

    def test_get_new_messages_no_new(self):
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")
        registry.append_message("t1", {"role": "user", "content": "msg1"})

        registry.get_new_messages("t1")
        new_msgs, count = registry.get_new_messages("t1")
        assert count == 0
        assert len(new_msgs) == 0

    def test_get_new_messages_nonexistent(self):
        registry = AgentTaskRegistry()
        new_msgs, count = registry.get_new_messages("nonexistent")
        assert count == 0
        assert len(new_msgs) == 0

    def test_has_running_tasks(self):
        registry = AgentTaskRegistry()
        assert registry.has_running_tasks is False

        registry.register("t1", "task-1", "desc1")
        assert registry.has_running_tasks is True

        registry.update_status("t1", AgentTaskStatus.COMPLETED)
        assert registry.has_running_tasks is False

    def test_clear(self):
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")
        registry.register("t2", "task-2", "desc2")
        registry.clear()
        assert len(registry.get_all()) == 0


# ============================================================================
# 线程安全测试
# ============================================================================

class TestAgentTaskRegistryConcurrency:
    def test_concurrent_writes(self):
        """测试多线程并发写入不崩溃。"""
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")

        errors = []

        def writer(thread_id: int):
            try:
                for i in range(100):
                    registry.append_message("t1", {
                        "role": "tool",
                        "content": f"thread-{thread_id}-msg-{i}",
                    })
                    registry.update_progress("t1", last_activity=f"thread-{thread_id}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        task = registry.get("t1")
        assert len(task.messages) == 500  # 5 threads * 100 messages

    def test_concurrent_read_write(self):
        """测试读写并发不崩溃。"""
        registry = AgentTaskRegistry()
        registry.register("t1", "task-1", "desc1")

        errors = []

        def writer():
            try:
                for i in range(100):
                    registry.append_message("t1", {"role": "tool", "content": f"msg-{i}"})
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(100):
                    registry.get_new_messages("t1")
                    registry.get_all()
                    registry.get_all_running()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
