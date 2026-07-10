"""循环管理器。

管理循环的完整生命周期：创建、执行、停止、恢复。

核心流程：
1. create_loop(): 创建循环配置和状态
2. start_loop(): 启动后台循环执行器
3. 等待间隔 → 执行对话 → 显示结果 → 解析下一次间隔 → 重复
4. stop_loop(): 停止循环

设计理由：
- 循环执行复用 TUI 的 _run_conversation_loop() 方法，不重复实现
- 使用 asyncio 任务而非线程，与 TUI 事件循环兼容
- 循环元数据通过回调通知 TUI 进行持久化
- 单次失败不停止循环，记录错误继续执行
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from src.loop import (
    DEFAULT_DYNAMIC_INTERVAL,
    LoopConfig,
    LoopMode,
    LoopState,
    LoopStatus,
)
from src.loop.interval_parser import IntervalParseError, format_interval, parse_interval
from src.loop.prompt import get_maintenance_prompt

logger = logging.getLogger(__name__)

# 从 AI 响应中提取动态间隔的正则
NEXT_INTERVAL_PATTERN = re.compile(r"__next_interval:\s*(\d+\s*[smhd])\s*__", re.IGNORECASE)


class LoopManager:
    """循环生命周期管理器。

    职责：
    - 创建和管理单个循环
    - 调度循环执行（固定间隔或动态间隔）
    - 从 AI 响应中提取动态间隔
    - 停止和恢复循环

    注意：同一时间只允许一个活跃循环。
    """

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        on_loop_event: Optional[Callable[[str, dict], Any]] = None,
    ):
        """初始化循环管理器。

        Args:
            working_dir: 当前工作目录（用于查找 loop.md）。
            on_loop_event: 循环事件回调，用于通知 TUI 更新状态。
                          签名: (event_type: str, data: dict) -> None
                          event_type: "created" | "stopped" | "executing" | "waiting" | "error" | "expired"
        """
        self._working_dir = working_dir
        self._on_loop_event = on_loop_event
        self._state: Optional[LoopState] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    @property
    def active_loop(self) -> Optional[LoopState]:
        """获取当前活跃循环状态。"""
        if self._state and self._state.is_active:
            return self._state
        return None

    @property
    def is_running(self) -> bool:
        """是否有循环正在运行。"""
        return self._task is not None and not self._task.done()

    def create_loop(
        self,
        interval: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> LoopState:
        """创建新循环。

        如果已有活跃循环，先停止它。

        Args:
            interval: 间隔表达式（如 "5m", "every 2 hours"）。None 表示动态模式。
            prompt: 用户提示。None 表示使用维护提示。

        Returns:
            新创建的循环状态。
        """
        # 停止已有循环
        if self._state and self._state.is_active:
            self.stop_loop()

        # 解析间隔
        interval_seconds = None
        mode = LoopMode.DYNAMIC

        if interval:
            try:
                interval_seconds = parse_interval(interval)
                mode = LoopMode.FIXED
            except IntervalParseError as e:
                raise ValueError(str(e))

        # 获取提示（如果未提供则使用维护提示）
        effective_prompt = prompt
        if prompt is None:
            effective_prompt = get_maintenance_prompt(self._working_dir)

        # 创建配置和状态
        config = LoopConfig(
            interval_seconds=interval_seconds,
            prompt=effective_prompt,
            mode=mode,
        )

        self._state = LoopState(config=config, status=LoopStatus.ACTIVE)

        # 通知事件
        self._emit_event("created", {
            "loop_id": config.loop_id,
            "interval": format_interval(interval_seconds) if interval_seconds else "dynamic",
            "prompt": effective_prompt[:100] if effective_prompt else "",
            "mode": mode.value,
        })

        return self._state

    async def start_loop(
        self,
        run_conversation: Callable[[str], Any],
    ) -> None:
        """启动循环执行器。

        Args:
            run_conversation: 执行对话循环的函数，签名: (prompt: str) -> dict
                            应返回包含 "final_response" 和可选 "reasoning" 的字典。
        """
        if not self._state or not self._state.is_active:
            raise RuntimeError("没有活跃的循环可启动")

        if self.is_running:
            raise RuntimeError("循环已在运行中")

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(run_conversation))

    def stop_loop(self) -> Optional[LoopState]:
        """停止当前循环。

        Returns:
            停止的循环状态，如果没有活跃循环则返回 None。
        """
        if not self._state or not self._state.is_active:
            return None

        self._state.status = LoopStatus.STOPPED
        self._stop_event.set()

        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

        self._emit_event("stopped", {
            "loop_id": self._state.loop_id,
            "execution_count": self._state.execution_count,
        })

        state = self._state
        self._state = None
        return state

    def restore_loop(self, config: LoopConfig) -> LoopState:
        """从配置恢复循环。

        用于 --resume 时从会话元数据重建循环状态。

        Args:
            config: 循环配置（从 JSONL 元数据恢复）。

        Returns:
            恢复后的循环状态。

        Raises:
            ValueError: 如果循环已过期。
        """
        if config.is_expired:
            raise ValueError(f"循环 {config.loop_id} 已过期（{config.expires_at}）")

        # 停止已有循环
        if self._state and self._state.is_active:
            self.stop_loop()

        self._state = LoopState(
            config=config,
            status=LoopStatus.ACTIVE,
        )

        self._emit_event("created", {
            "loop_id": config.loop_id,
            "interval": format_interval(config.interval_seconds) if config.interval_seconds else "dynamic",
            "prompt": config.prompt[:100] if config.prompt else "",
            "mode": config.mode.value,
            "restored": True,
        })

        return self._state

    async def _run_loop(self, run_conversation: Callable[[str], Any]) -> None:
        """循环执行主逻辑。

        流程：
        1. 检查循环状态
        2. 获取提示（固定模式使用配置提示，动态模式重新加载维护提示）
        3. 执行对话
        4. 解析响应获取动态间隔（如果是动态模式）
        5. 等待间隔
        6. 重复
        """
        while self._state and self._state.is_active:
            # 检查过期
            if self._state.config.is_expired:
                self._state.status = LoopStatus.EXPIRED
                self._emit_event("expired", {"loop_id": self._state.loop_id})
                break

            # 检查停止信号
            if self._stop_event.is_set():
                break

            try:
                # 获取提示
                prompt = self._get_prompt()

                # 执行对话
                self._state.status = LoopStatus.EXECUTING
                self._emit_event("executing", {
                    "loop_id": self._state.loop_id,
                    "execution_count": self._state.execution_count + 1,
                })

                result = await run_conversation(prompt)

                self._state.last_executed_at = datetime.now(timezone.utc)
                self._state.execution_count += 1
                self._state.last_error = None

                # 动态模式：解析下一次间隔
                if self._state.config.is_dynamic:
                    response = result.get("final_response", "") if result else ""
                    next_interval = self._extract_next_interval(response)
                    wait_seconds = next_interval
                else:
                    wait_seconds = self._state.config.interval_seconds

                # 等待下一次间隔
                self._state.status = LoopStatus.WAITING
                self._emit_event("waiting", {
                    "loop_id": self._state.loop_id,
                    "next_interval": format_interval(wait_seconds),
                })

                # 可中断的等待
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=wait_seconds,
                    )
                    # 如果 stop_event 被设置，退出循环
                    break
                except asyncio.TimeoutError:
                    # 超时意味着间隔到期，继续下一次迭代
                    pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"循环执行出错: {e}", exc_info=True)
                self._state.last_error = str(e)
                self._state.status = LoopStatus.ERROR
                self._emit_event("error", {
                    "loop_id": self._state.loop_id,
                    "error": str(e),
                })

                # 出错后等待一段时间再继续
                wait_seconds = self._state.config.interval_seconds or DEFAULT_DYNAMIC_INTERVAL
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=wait_seconds,
                    )
                    break
                except asyncio.TimeoutError:
                    pass

        # 清理
        if self._state and self._state.status not in (LoopStatus.STOPPED, LoopStatus.EXPIRED):
            self._state.status = LoopStatus.STOPPED

    def _get_prompt(self) -> str:
        """获取当前迭代的提示文本。

        动态模式下每次重新加载维护提示（支持 loop.md 运行时修改）。
        固定模式下使用创建时配置的提示。
        """
        if self._state.config.prompt:
            return self._state.config.prompt

        # 维护提示：每次都重新加载
        return get_maintenance_prompt(self._working_dir)

    def _extract_next_interval(self, response: str) -> int:
        """从 AI 响应中提取动态间隔。

        期望格式：__next_interval: 5m__

        Args:
            response: AI 的响应文本。

        Returns:
            间隔秒数，如果未找到标记则返回默认值。
        """
        match = NEXT_INTERVAL_PATTERN.search(response)
        if not match:
            return DEFAULT_DYNAMIC_INTERVAL

        interval_str = match.group(1).strip()
        try:
            return parse_interval(interval_str)
        except IntervalParseError:
            logger.warning(f"无法解析动态间隔 '{interval_str}'，使用默认值")
            return DEFAULT_DYNAMIC_INTERVAL

    def _emit_event(self, event_type: str, data: dict) -> None:
        """发出循环事件。"""
        if self._on_loop_event:
            try:
                self._on_loop_event(event_type, data)
            except Exception as e:
                logger.error(f"循环事件回调出错: {e}", exc_info=True)
