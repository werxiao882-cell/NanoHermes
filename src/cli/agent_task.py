"""Agent 任务状态模型。

每个子 Agent 对应一个 AgentTask，包含状态、进度、消息记录。
AgentTaskRegistry 管理所有任务的生命周期，线程安全。

设计理由：
- 子 Agent 在后台线程运行，主线程通过 Registry 查询状态
- messages 列表记录子 Agent 的完整 transcript，供 /agent <id> 命令查看
- last_printed_index 支持增量打印（只显示新消息）
- abort_event 支持从主线程请求中止子 Agent
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentTaskStatus(Enum):
    """Agent 任务状态。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AgentTaskProgress:
    """Agent 任务进度信息。

    由 ConversationEventHandler 在监听到子 Agent 事件时更新。
    """
    token_count: int = 0
    tool_calls: int = 0
    last_activity: str = ""
    last_activity_time: float = 0.0


@dataclass
class AgentTask:
    """单个子 Agent 的任务状态。

    生命周期：
    1. register() → status=RUNNING
    2. 后台线程运行，通过 update_progress/append_message 更新
    3. update_status(COMPLETED/FAILED/TIMEOUT) → 结束

    Attributes:
        id: 任务唯一 ID（task_id）。
        name: 任务名称（用于显示，如 "auth-refactor"）。
        description: 任务描述（goal 的前 80 字符）。
        status: 当前状态。
        start_time: 开始时间戳。
        end_time: 结束时间戳（None 表示未结束）。
        progress: 进度信息。
        messages: 完整 transcript（role/content/metadata）。
        last_printed_index: 上次打印位置（增量打印用）。
        abort_event: 中止信号（线程安全）。
    """
    id: str
    name: str
    description: str
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    progress: AgentTaskProgress = field(default_factory=AgentTaskProgress)
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_printed_index: int = 0
    abort_event: threading.Event = field(default_factory=threading.Event)

    @property
    def is_running(self) -> bool:
        return self.status == AgentTaskStatus.RUNNING

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            AgentTaskStatus.COMPLETED,
            AgentTaskStatus.FAILED,
            AgentTaskStatus.TIMEOUT,
        )

    def format_duration(self) -> str:
        """格式化耗时。"""
        end = self.end_time or time.time()
        seconds = int(max(0, end - self.start_time))
        if seconds < 60:
            return f"{seconds}s"
        return f"{seconds // 60}m{seconds % 60}s"

    def request_abort(self) -> None:
        """请求中止任务（线程安全）。"""
        self.abort_event.set()


class AgentTaskRegistry:
    """线程安全的 Agent 任务注册表。

    设计理由：
    - 子 Agent 线程写入（update_status/update_progress/append_message）
    - 主线程读取（get_all/print_agent_list/print_transcript）
    - 使用 Lock 保护所有读写操作
    """

    def __init__(self) -> None:
        self._tasks: dict[str, AgentTask] = {}
        self._lock = threading.Lock()

    def register(self, task_id: str, name: str, description: str) -> AgentTask:
        """注册新任务，初始状态为 RUNNING。"""
        task = AgentTask(
            id=task_id,
            name=name,
            description=description[:80],
            status=AgentTaskStatus.RUNNING,
        )
        with self._lock:
            self._tasks[task_id] = task
        return task

    def get(self, task_id: str) -> AgentTask | None:
        """按 ID 获取任务。"""
        with self._lock:
            return self._tasks.get(task_id)

    def get_by_name(self, name: str) -> AgentTask | None:
        """按名称查找任务（支持前缀匹配）。"""
        with self._lock:
            for task in self._tasks.values():
                if task.name == name or task.id.startswith(name):
                    return task
        return None

    def get_all(self) -> list[AgentTask]:
        """获取所有任务（按注册顺序）。"""
        with self._lock:
            return list(self._tasks.values())

    def get_all_running(self) -> list[AgentTask]:
        """获取所有运行中的任务。"""
        with self._lock:
            return [t for t in self._tasks.values() if t.is_running]

    def update_status(self, task_id: str, status: AgentTaskStatus) -> None:
        """更新任务状态。终态时自动记录 end_time。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = status
                if status in (AgentTaskStatus.COMPLETED,
                              AgentTaskStatus.FAILED,
                              AgentTaskStatus.TIMEOUT):
                    task.end_time = time.time()

    def update_progress(self, task_id: str, **kwargs: Any) -> None:
        """更新任务进度字段。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                for key, value in kwargs.items():
                    if hasattr(task.progress, key):
                        setattr(task.progress, key, value)
                task.progress.last_activity_time = time.time()

    def append_message(self, task_id: str, message: dict[str, Any]) -> None:
        """追加消息到任务的 transcript。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.messages.append(message)

    def get_new_messages(self, task_id: str) -> tuple[list[dict[str, Any]], int]:
        """获取自上次打印以来的新消息（增量打印）。

        Returns:
            (new_messages, new_count) 元组。
            调用后自动更新 last_printed_index。
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return [], 0
            new_msgs = task.messages[task.last_printed_index:]
            task.last_printed_index = len(task.messages)
            return new_msgs, len(new_msgs)

    @property
    def has_running_tasks(self) -> bool:
        """是否有运行中的任务。"""
        with self._lock:
            return any(t.is_running for t in self._tasks.values())

    def clear(self) -> None:
        """清除所有任务（仅测试用）。"""
        with self._lock:
            self._tasks.clear()
