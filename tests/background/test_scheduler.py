"""BackgroundTaskScheduler 单元测试。"""

import threading
import time
import pytest
from src.background.scheduler import BackgroundTaskScheduler


@pytest.fixture
def scheduler():
    """创建调度器实例。"""
    s = BackgroundTaskScheduler(max_concurrent=2, task_timeout_seconds=5.0)
    yield s
    s.shutdown(timeout=2.0)


class TestSchedulerInit:
    """测试调度器初始化。"""

    def test_default_params(self):
        s = BackgroundTaskScheduler()
        assert s.max_concurrent == 2
        assert s.enabled is True

    def test_custom_params(self):
        s = BackgroundTaskScheduler(max_concurrent=3, enabled=False)
        assert s.max_concurrent == 3
        assert s.enabled is False

    def test_min_concurrent(self):
        s = BackgroundTaskScheduler(max_concurrent=0)
        assert s.max_concurrent == 1


class TestTaskRegistration:
    """测试任务注册。"""

    def test_register_task(self, scheduler):
        scheduler.register_task("test", lambda e: None, lambda e: True)
        tasks = scheduler.get_registered_tasks()
        assert len(tasks) == 1
        assert tasks[0]["name"] == "test"
        assert tasks[0]["enabled"] is True

    def test_register_disabled_task(self, scheduler):
        scheduler.register_task("test", lambda e: None, lambda e: True, enabled=False)
        tasks = scheduler.get_registered_tasks()
        assert tasks[0]["enabled"] is False

    def test_unregister_task(self, scheduler):
        scheduler.register_task("test", lambda e: None, lambda e: True)
        assert scheduler.unregister_task("test") is True
        assert len(scheduler.get_registered_tasks()) == 0

    def test_unregister_nonexistent(self, scheduler):
        assert scheduler.unregister_task("nonexistent") is False

    def test_set_task_enabled(self, scheduler):
        scheduler.register_task("test", lambda e: None, lambda e: True)
        scheduler.set_task_enabled("test", False)
        tasks = scheduler.get_registered_tasks()
        assert tasks[0]["enabled"] is False


class TestTaskTriggering:
    """测试任务触发。"""

    def test_trigger_on_loop_end(self, scheduler):
        results = []

        def handler(event_data):
            results.append(event_data["iteration"])

        def trigger(event_data):
            return event_data["iteration"] >= 5

        scheduler.register_task("test", handler, trigger)
        triggered = scheduler.on_loop_end([], iteration=5)

        assert "test" in triggered
        time.sleep(0.5)
        assert 5 in results

    def test_no_trigger_when_condition_false(self, scheduler):
        called = []

        def handler(event_data):
            called.append(True)

        def trigger(event_data):
            return False

        scheduler.register_task("test", handler, trigger)
        triggered = scheduler.on_loop_end([], iteration=1)

        assert len(triggered) == 0
        time.sleep(0.2)
        assert len(called) == 0

    def test_no_trigger_when_disabled(self, scheduler):
        scheduler.enabled = False
        called = []

        def handler(event_data):
            called.append(True)

        scheduler.register_task("test", handler, lambda e: True)
        triggered = scheduler.on_loop_end([], iteration=1)

        assert len(triggered) == 0
        time.sleep(0.2)
        assert len(called) == 0

    def test_no_trigger_when_task_disabled(self, scheduler):
        called = []

        def handler(event_data):
            called.append(True)

        scheduler.register_task("test", handler, lambda e: True, enabled=False)
        triggered = scheduler.on_loop_end([], iteration=1)

        assert len(triggered) == 0
        time.sleep(0.2)
        assert len(called) == 0


class TestConcurrencyControl:
    """测试并发控制。"""

    def test_max_concurrent_enforced(self, scheduler):
        running_count = []
        lock = threading.Lock()

        def handler(event_data):
            with lock:
                running_count.append(len(scheduler.get_running_tasks()))
            time.sleep(0.5)

        def trigger(event_data):
            return True

        scheduler.register_task("task_a", handler, trigger)
        scheduler.register_task("task_b", handler, trigger)
        scheduler.register_task("task_c", handler, trigger)

        scheduler.on_loop_end([], iteration=1)
        time.sleep(0.2)

        # 最多 2 个任务同时运行
        assert max(running_count) <= 2

    def test_task_completes_and_releases_slot(self, scheduler):
        completed = []

        def fast_handler(event_data):
            time.sleep(0.1)
            completed.append("fast")

        def slow_handler(event_data):
            time.sleep(0.5)
            completed.append("slow")

        scheduler.register_task("fast", fast_handler, lambda e: True)
        scheduler.register_task("slow", slow_handler, lambda e: True)

        scheduler.on_loop_end([], iteration=1)
        time.sleep(1.0)

        assert "fast" in completed
        assert "slow" in completed


class TestTaskHistory:
    """测试任务历史。"""

    def test_successful_task_recorded(self, scheduler):
        def handler(event_data):
            pass

        scheduler.register_task("test", handler, lambda e: True)
        scheduler.on_loop_end([], iteration=1)
        time.sleep(0.5)

        history = scheduler.get_task_history()
        assert len(history) >= 1
        assert history[0]["name"] == "test"
        assert history[0]["success"] is True

    def test_failed_task_recorded(self, scheduler):
        def handler(event_data):
            raise RuntimeError("test error")

        scheduler.register_task("test", handler, lambda e: True)
        scheduler.on_loop_end([], iteration=1)
        time.sleep(0.5)

        history = scheduler.get_task_history()
        assert len(history) >= 1
        assert history[0]["success"] is False
        assert "test error" in history[0]["error"]

    def test_history_limit(self, scheduler):
        def handler(event_data):
            pass

        for i in range(25):
            name = f"task_{i}"
            scheduler.register_task(name, handler, lambda e: True)
            scheduler.on_loop_end([], iteration=i)
            time.sleep(0.1)

        time.sleep(1.0)
        history = scheduler.get_task_history(limit=10)
        assert len(history) <= 10


class TestRunningTasks:
    """测试运行中任务查询。"""

    def test_running_tasks_empty_initially(self, scheduler):
        assert scheduler.get_running_tasks() == []

    def test_running_tasks_during_execution(self, scheduler):
        barrier = threading.Event()

        def handler(event_data):
            barrier.wait(timeout=2.0)

        scheduler.register_task("test", handler, lambda e: True)
        scheduler.on_loop_end([], iteration=1)
        time.sleep(0.2)

        running = scheduler.get_running_tasks()
        assert len(running) >= 1
        assert running[0]["name"] == "test"
        assert running[0]["duration"] > 0

        barrier.set()
        time.sleep(0.3)

        running = scheduler.get_running_tasks()
        assert len(running) == 0


class TestShutdown:
    """测试优雅关闭。"""

    def test_shutdown_waits_for_tasks(self, scheduler):
        completed = []

        def handler(event_data):
            time.sleep(0.3)
            completed.append(True)

        scheduler.register_task("test", handler, lambda e: True)
        scheduler.on_loop_end([], iteration=1)
        time.sleep(0.1)

        scheduler.shutdown(timeout=2.0)
        assert len(completed) == 1

    def test_shutdown_timeout(self, scheduler):
        def handler(event_data):
            time.sleep(5.0)

        scheduler.register_task("test", handler, lambda e: True)
        scheduler.on_loop_end([], iteration=1)
        time.sleep(0.1)

        start = time.time()
        scheduler.shutdown(timeout=0.5)
        elapsed = time.time() - start

        assert elapsed < 2.0

    def test_no_trigger_after_shutdown(self, scheduler):
        called = []

        def handler(event_data):
            called.append(True)

        scheduler.register_task("test", handler, lambda e: True)
        scheduler.shutdown(timeout=1.0)

        triggered = scheduler.on_loop_end([], iteration=1)
        assert len(triggered) == 0
        time.sleep(0.2)
        assert len(called) == 0


class TestReset:
    """测试重置。"""

    def test_reset_clears_state(self, scheduler):
        scheduler.register_task("test", lambda e: None, lambda e: True)
        scheduler.on_loop_end([], iteration=1)
        time.sleep(0.3)

        scheduler.reset()

        assert len(scheduler.get_registered_tasks()) == 0
        assert len(scheduler.get_running_tasks()) == 0
        assert len(scheduler.get_task_history()) == 0
