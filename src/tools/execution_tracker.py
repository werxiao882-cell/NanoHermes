"""工具执行状态追踪器。

设计参考: Claude Code toolOrchestration.ts 中的状态追踪:
  toolUseContext.setInProgressToolUseIDs(prev => new Set(prev).add(toolUse.id))
  markToolUseAsComplete(toolUseContext, toolUse.id)

NanoHermes 适配:
  - 单例模式，全局共享执行状态
  - 线程安全（支持同步/异步混合调用）
  - 超时自动清理
  - 提供查询接口用于调试和监控

设计理由:
- 使用 threading.Lock 而非 asyncio.Lock 因为 dispatch() 是同步函数
- 单例确保所有模块看到一致的执行状态
- 历史记录限制大小避免内存无限增长
"""

from __future__ import annotations

import time
import json
import logging
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ─── 执行状态枚举 ─────────────────────────────────────────────


class ToolExecutionStatus(str, Enum):
    """工具执行状态。"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# ─── 执行状态数据类 ──────────────────────────────────────────


@dataclass
class ToolExecutionState:
    """单个工具的执行状态。"""
    tool_call_id: str             # 工具调用唯一 ID（来自 LLM）
    tool_name: str                # 工具名称
    status: ToolExecutionStatus   # 当前状态
    started_at: float             # 开始时间（Unix 时间戳）
    completed_at: float | None = None  # 完成时间
    error: str | None = None      # 错误信息（如有）
    args: dict | None = None      # 工具参数（用于调试）
    result_length: int | None = None  # 结果长度（用于监控）

    @property
    def duration_ms(self) -> float | None:
        """执行耗时（毫秒）。"""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at) * 1000


# ─── 配置常量 ─────────────────────────────────────────────────

DEFAULT_EXECUTION_TIMEOUT = 300  # 默认执行超时 300 秒
CLEANUP_INTERVAL = 60            # 清理间隔 60 秒
MAX_HISTORY_SIZE = 100           # 保留最近 100 条历史记录


# ─── 执行追踪器 ───────────────────────────────────────────────


class ToolExecutionTracker:
    """工具执行状态追踪器（单例）。"""

    _instance: ToolExecutionTracker | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> ToolExecutionTracker:
        """单例模式实现。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化（只执行一次）。"""
        if self._initialized:
            return

        # 正在执行的工具: tool_call_id → ToolExecutionState
        self._active: dict[str, ToolExecutionState] = {}

        # 历史记录: 最近 N 条完成/失败的执行记录
        self._history: list[ToolExecutionState] = []

        # 锁: 保护 _active 和 _history 的并发访问
        self._data_lock = threading.Lock()

        # 超时配置
        self.default_timeout = DEFAULT_EXECUTION_TIMEOUT

        self._initialized = True

    def mark_start(
        self,
        tool_call_id: str,
        tool_name: str,
        args: dict | None = None,
    ) -> bool:
        """标记工具开始执行。

        Returns:
            True 如果成功标记，False 如果已在执行中（防重入）。
        """
        with self._data_lock:
            # 防重入检查
            if tool_call_id in self._active:
                existing = self._active[tool_call_id]
                logger.warning(
                    f"工具调用 '{tool_call_id}' ({tool_name}) 已在执行中，"
                    f"拒绝重复执行（状态: {existing.status.value}）"
                )
                return False

            # 创建新的执行状态
            state = ToolExecutionState(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                status=ToolExecutionStatus.IN_PROGRESS,
                started_at=time.time(),
                args=args,
            )
            self._active[tool_call_id] = state

            logger.debug(f"工具开始执行: '{tool_call_id}' ({tool_name})")
            return True

    def mark_complete(
        self,
        tool_call_id: str,
        result_length: int | None = None,
    ) -> ToolExecutionState | None:
        """标记工具执行完成。"""
        with self._data_lock:
            state = self._active.pop(tool_call_id, None)
            if state is None:
                logger.warning(
                    f"工具调用 '{tool_call_id}' 不在活跃列表中，"
                    f"无法标记为完成"
                )
                return None

            state.status = ToolExecutionStatus.COMPLETED
            state.completed_at = time.time()
            state.result_length = result_length

            self._add_to_history(state)

            logger.debug(
                f"工具执行完成: '{tool_call_id}' ({state.tool_name}) "
                f"耗时 {state.duration_ms:.0f}ms"
            )
            return state

    def mark_failed(
        self,
        tool_call_id: str,
        error: str,
    ) -> ToolExecutionState | None:
        """标记工具执行失败。"""
        with self._data_lock:
            state = self._active.pop(tool_call_id, None)
            if state is None:
                logger.warning(
                    f"工具调用 '{tool_call_id}' 不在活跃列表中，"
                    f"无法标记为失败"
                )
                return None

            state.status = ToolExecutionStatus.FAILED
            state.completed_at = time.time()
            state.error = error

            self._add_to_history(state)

            logger.debug(
                f"工具执行失败: '{tool_call_id}' ({state.tool_name}) "
                f"耗时 {state.duration_ms:.0f}ms: {error}"
            )
            return state

    def mark_timeout(
        self,
        tool_call_id: str,
    ) -> ToolExecutionState | None:
        """标记工具执行超时。"""
        with self._data_lock:
            state = self._active.pop(tool_call_id, None)
            if state is None:
                return None

            state.status = ToolExecutionStatus.TIMEOUT
            state.completed_at = time.time()
            state.error = f"执行超时（超过 {self.default_timeout}s）"

            self._add_to_history(state)

            logger.warning(
                f"工具执行超时: '{tool_call_id}' ({state.tool_name}) "
                f"耗时 {state.duration_ms:.0f}ms"
            )
            return state

    # ─── 查询方法 ─────────────────────────────────────────────

    def is_in_progress(self, tool_call_id: str) -> bool:
        """检查工具是否正在执行。"""
        with self._data_lock:
            return tool_call_id in self._active

    def get_state(self, tool_call_id: str) -> ToolExecutionState | None:
        """获取工具的执行状态。"""
        with self._data_lock:
            return self._active.get(tool_call_id)

    def get_active_tools(self) -> list[ToolExecutionState]:
        """获取所有正在执行的工具。"""
        with self._data_lock:
            return list(self._active.values())

    def get_active_count(self) -> int:
        """获取正在执行的工具数量。"""
        with self._data_lock:
            return len(self._active)

    def get_history(
        self,
        limit: int = 20,
        status: ToolExecutionStatus | None = None,
    ) -> list[ToolExecutionState]:
        """获取执行历史记录。"""
        with self._data_lock:
            history = self._history
            if status:
                history = [s for s in history if s.status == status]
            return history[-limit:][::-1]  # 最新的在前

    def get_statistics(self) -> dict:
        """获取执行统计信息。"""
        with self._data_lock:
            completed = [s for s in self._history
                        if s.status == ToolExecutionStatus.COMPLETED]
            failed = [s for s in self._history
                     if s.status == ToolExecutionStatus.FAILED]
            timeout = [s for s in self._history
                      if s.status == ToolExecutionStatus.TIMEOUT]

            durations = [s.duration_ms for s in completed
                        if s.duration_ms is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0

            return {
                "active_count": len(self._active),
                "total_completed": len(completed),
                "total_failed": len(failed),
                "total_timeout": len(timeout),
                "avg_duration_ms": round(avg_duration, 1),
            }

    # ─── 超时清理 ─────────────────────────────────────────────

    def check_timeouts(self) -> list[str]:
        """检查并清理超时的工具执行。"""
        now = time.time()
        timed_out = []

        with self._data_lock:
            for tool_call_id, state in list(self._active.items()):
                elapsed = now - state.started_at
                if elapsed > self.default_timeout:
                    state.status = ToolExecutionStatus.TIMEOUT
                    state.completed_at = now
                    state.error = f"执行超时（超过 {elapsed:.0f}s）"

                    self._add_to_history(state)
                    del self._active[tool_call_id]

                    timed_out.append(tool_call_id)
                    logger.warning(
                        f"工具执行超时被清理: '{tool_call_id}' "
                        f"({state.tool_name}, {elapsed:.0f}s)"
                    )

        return timed_out

    # ─── 内部方法 ─────────────────────────────────────────────

    def _add_to_history(self, state: ToolExecutionState):
        """将执行状态加入历史记录。"""
        self._history.append(state)

        # 限制历史记录大小
        while len(self._history) > MAX_HISTORY_SIZE:
            self._history.pop(0)

    def reset(self):
        """重置所有状态（用于测试）。"""
        with self._data_lock:
            self._active.clear()
            self._history.clear()
