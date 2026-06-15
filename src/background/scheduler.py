"""后台任务调度器。

统一管理所有后台任务的触发、执行和状态监控。
使用信号量控制并发，防止资源耗尽。

设计决策：
- 使用 threading.Semaphore 控制并发，比 asyncio 更简单可靠
- 事件驱动触发（LOOP_END），比定时轮询更高效
- 守护线程执行，不阻塞主对话
- 任务失败只记录日志，不影响主对话
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class TaskRecord:
    """任务注册记录。

    Attributes:
        name: 任务名称。
        handler: 任务处理函数。
        trigger: 触发条件函数，接收 event_data 返回 bool。
        enabled: 是否启用。
    """
    name: str
    handler: Callable
    trigger: Callable[[dict[str, Any]], bool]
    enabled: bool = True


@dataclass
class RunningTask:
    """运行中的任务信息。

    Attributes:
        name: 任务名称。
        thread: 执行线程。
        start_time: 启动时间戳。
    """
    name: str
    thread: threading.Thread
    start_time: float


@dataclass
class TaskHistoryEntry:
    """任务历史条目。

    Attributes:
        name: 任务名称。
        start_time: 启动时间戳。
        end_time: 结束时间戳。
        duration: 运行时长（秒）。
        success: 是否成功。
        error: 错误信息（如果失败）。
    """
    name: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error: str = ""


class BackgroundTaskScheduler:
    """后台任务调度器。

    管理所有后台任务的注册、触发、执行和状态监控。

    使用方式：
        scheduler = BackgroundTaskScheduler(max_concurrent=2)
        scheduler.register_task("memory_flush", handler, trigger_fn)
        scheduler.on_loop_end(messages, iteration)
        # ... 应用退出时
        scheduler.shutdown()
    """

    def __init__(
        self,
        max_concurrent: int = 2,
        task_timeout_seconds: float = 300.0,
        enabled: bool = True,
    ):
        """初始化调度器。

        Args:
            max_concurrent: 最大并发任务数。
            task_timeout_seconds: 任务超时时间（秒）。
            enabled: 全局启用开关。
        """
        self._max_concurrent = max(1, max_concurrent)
        self._task_timeout = max(1.0, task_timeout_seconds)
        self._enabled = enabled

        # 信号量控制并发
        self._semaphore = threading.Semaphore(self._max_concurrent)

        # 任务注册表
        self._tasks: dict[str, TaskRecord] = {}

        # 运行中的任务（线程安全）
        self._running_lock = threading.Lock()
        self._running_tasks: dict[str, RunningTask] = {}

        # 任务历史（最近 20 条）
        self._history_lock = threading.Lock()
        self._history: deque[TaskHistoryEntry] = deque(maxlen=20)

        # 关闭标志
        self._shutdown_event = threading.Event()

    @property
    def enabled(self) -> bool:
        """全局启用状态。"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def max_concurrent(self) -> int:
        """最大并发数。"""
        return self._max_concurrent

    def register_task(
        self,
        name: str,
        handler: Callable,
        trigger: Callable[[dict[str, Any]], bool],
        enabled: bool = True,
    ) -> None:
        """注册后台任务。

        Args:
            name: 任务名称（唯一标识）。
            handler: 任务处理函数，接收 event_data 参数。
            trigger: 触发条件函数，接收 event_data 返回 bool。
            enabled: 是否启用。
        """
        self._tasks[name] = TaskRecord(
            name=name,
            handler=handler,
            trigger=trigger,
            enabled=enabled,
        )
        logger.info(f"后台任务已注册: {name} (enabled={enabled})")

    def unregister_task(self, name: str) -> bool:
        """注销后台任务。

        Args:
            name: 任务名称。

        Returns:
            是否成功注销。
        """
        if name in self._tasks:
            del self._tasks[name]
            logger.info(f"后台任务已注销: {name}")
            return True
        return False

    def set_task_enabled(self, name: str, enabled: bool) -> bool:
        """设置任务启用状态。

        Args:
            name: 任务名称。
            enabled: 是否启用。

        Returns:
            是否成功设置。
        """
        if name in self._tasks:
            self._tasks[name].enabled = enabled
            logger.info(f"后台任务 {name} 启用状态: {enabled}")
            return True
        return False

    def on_loop_end(
        self,
        messages: list[dict[str, Any]],
        iteration: int,
        **kwargs: Any,
    ) -> list[str]:
        """对话循环结束时触发后台任务。

        遍历所有注册的任务，评估触发条件，满足条件则启动后台线程执行。

        Args:
            messages: 当前对话消息列表。
            iteration: 当前迭代次数。
            **kwargs: 其他事件数据。

        Returns:
            已触发的任务名称列表。
        """
        if not self._enabled:
            return []

        if self._shutdown_event.is_set():
            return []

        event_data = {
            "messages": messages,
            "iteration": iteration,
            **kwargs,
        }

        triggered = []

        for name, task in self._tasks.items():
            if not task.enabled:
                continue

            # 检查任务是否已在运行
            with self._running_lock:
                if name in self._running_tasks:
                    continue

            # 评估触发条件
            try:
                should_trigger = task.trigger(event_data)
            except Exception as e:
                logger.warning(f"后台任务 {name} 触发条件评估失败: {e}")
                continue

            if should_trigger:
                self._start_task(name, task, event_data)
                triggered.append(name)

                # 任务启动间隔，避免 API 速率限制
                time.sleep(0.1)

        return triggered

    def _start_task(
        self,
        name: str,
        task: TaskRecord,
        event_data: dict[str, Any],
    ) -> None:
        """启动后台任务线程。

        Args:
            name: 任务名称。
            task: 任务记录。
            event_data: 事件数据。
        """
        def _task_wrapper():
            """任务执行包装器，处理信号量和异常。"""
            start_time = time.time()

            # 获取信号量（阻塞等待）
            acquired = self._semaphore.acquire(timeout=self._task_timeout)
            if not acquired:
                logger.warning(f"后台任务 {name} 获取信号量超时")
                return

            try:
                # 记录运行状态
                with self._running_lock:
                    self._running_tasks[name] = RunningTask(
                        name=name,
                        thread=threading.current_thread(),
                        start_time=time.time(),
                    )

                logger.info(f"后台任务启动: {name}")

                # 执行任务
                task.handler(event_data)

                elapsed = time.time() - start_time
                logger.info(f"后台任务完成: {name} (耗时: {elapsed:.1f}s)")

                # 记录成功历史
                self._add_history(name, start_time, True)

            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"后台任务失败: {name} ({elapsed:.1f}s): {e}",
                    exc_info=True,
                )
                # 记录失败历史
                self._add_history(name, start_time, False, str(e))

            finally:
                # 清理运行状态
                with self._running_lock:
                    self._running_tasks.pop(name, None)

                # 释放信号量
                self._semaphore.release()

        thread = threading.Thread(
            target=_task_wrapper,
            name=f"bg-{name}",
            daemon=True,
        )
        thread.start()

    def _add_history(
        self,
        name: str,
        start_time: float,
        success: bool,
        error: str = "",
    ) -> None:
        """添加任务历史记录。

        Args:
            name: 任务名称。
            start_time: 启动时间戳。
            success: 是否成功。
            error: 错误信息。
        """
        end_time = time.time()
        entry = TaskHistoryEntry(
            name=name,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            success=success,
            error=error,
        )
        with self._history_lock:
            self._history.append(entry)

    def get_running_tasks(self) -> list[dict[str, Any]]:
        """获取运行中的任务列表。

        Returns:
            运行中的任务信息列表。
        """
        with self._running_lock:
            result = []
            for name, task in self._running_tasks.items():
                result.append({
                    "name": name,
                    "start_time": task.start_time,
                    "duration": time.time() - task.start_time,
                })
            return result

    def get_task_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取任务历史记录。

        Args:
            limit: 返回的最大条目数。

        Returns:
            任务历史列表（最近的在前）。
        """
        with self._history_lock:
            entries = list(self._history)
            entries.reverse()
            return [
                {
                    "name": e.name,
                    "start_time": e.start_time,
                    "end_time": e.end_time,
                    "duration": e.duration,
                    "success": e.success,
                    "error": e.error,
                }
                for e in entries[:limit]
            ]

    def get_registered_tasks(self) -> list[dict[str, Any]]:
        """获取已注册的任务列表。

        Returns:
            任务信息列表。
        """
        return [
            {
                "name": t.name,
                "enabled": t.enabled,
            }
            for t in self._tasks.values()
        ]

    def shutdown(self, timeout: float = 10.0) -> None:
        """优雅关闭调度器。

        等待运行中的任务完成，超时后强制终止。

        Args:
            timeout: 等待超时时间（秒）。
        """
        self._shutdown_event.set()

        # 等待运行中的任务完成
        with self._running_lock:
            running = list(self._running_tasks.values())

        if running:
            logger.info(f"等待 {len(running)} 个后台任务完成 (超时: {timeout}s)...")
            deadline = time.time() + timeout
            for task in running:
                remaining = max(0.1, deadline - time.time())
                task.thread.join(timeout=remaining)
                if task.thread.is_alive():
                    logger.warning(f"后台任务 {task.name} 超时未完成")

        logger.info("后台任务调度器已关闭")

    def reset(self) -> None:
        """重置调度器状态（用于测试）。"""
        self._tasks.clear()
        with self._running_lock:
            self._running_tasks.clear()
        with self._history_lock:
            self._history.clear()
        self._shutdown_event.clear()
