"""工具重试管理器。

设计参考: Claude Code withRetry.ts 中的重试循环 + 退避逻辑。
核心流程:
  1. 检查工具是否在可重试白名单中
  2. 使用 classifier 分类错误
  3. 执行恢复动作（reconnect/refresh_credentials/backoff）
  4. 指数退避等待
  5. 重新执行工具

设计理由:
- 使用 async/await 因为重试需要异步等待（退避延迟）
- 通过 executor 回调封装工具执行逻辑，解耦重试与执行
- 默认白名单基于工具副作用分类（只读工具可重试，写操作不可重试）
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Callable

from src.tools.retry_classifier import (
    ToolErrorClassifier,
    RecoveryAction,
    ErrorClassification,
)

logger = logging.getLogger(__name__)


# ─── 重试配置 ─────────────────────────────────────────────────


@dataclass
class RetryConfig:
    """单个工具的重试配置。

    参考 Claude Code: 不同工具/场景有不同的重试策略。
    """
    tool_name: str
    max_retries: int = 3           # 最大重试次数
    is_retryable: bool = False     # 是否可重试
    recover_fn: Callable | None = None  # 自定义恢复函数（如刷新凭证）


# ─── 默认白名单 ───────────────────────────────────────────────
# 设计理由:
# - 只读工具天然可重试（无副作用）
# - 写操作工具不可重试（可能造成重复写入）
# - terminal 不可重试（命令已执行，重试可能重复执行）

DEFAULT_RETRYABLE_TOOLS = {
    "read_file",
    "search_files",
    "skill_view",
    "skills_list",
    "memory",
    "session_search",
}

DEFAULT_NON_RETRYABLE_TOOLS = {
    "write_file",
    "patch",
    "terminal",
    "execute_code",
    "process",
}


# ─── 重试管理器 ───────────────────────────────────────────────


class ToolRetryManager:
    """工具重试管理器。

    使用方式:
        manager = ToolRetryManager()
        result = await manager.execute_with_retry(
            tool_name="read_file",
            executor=lambda: dispatch("read_file", {"path": "..."}),
        )

    设计参考: Claude Code withRetry() AsyncGenerator 的重试循环，
    改为异步版本以适配 NanoHermes 的 dispatch() 架构。
    """

    def __init__(
        self,
        classifier: ToolErrorClassifier | None = None,
        retryable_tools: set[str] | None = None,
        tool_configs: dict[str, RetryConfig] | None = None,
    ):
        self.classifier = classifier or ToolErrorClassifier()
        self.retryable_tools = retryable_tools or set(DEFAULT_RETRYABLE_TOOLS)
        self.tool_configs: dict[str, RetryConfig] = tool_configs or {}

        # 注册自定义工具配置
        for name, config in (tool_configs or {}).items():
            if config.is_retryable:
                self.retryable_tools.add(name)

    async def execute_with_retry(
        self,
        tool_name: str,
        executor: Callable[[], str],
        max_retries: int | None = None,
        recover_fn: Callable | None = None,
    ) -> str:
        """执行工具调用，失败时自动重试。

        参考 Claude Code withRetry() 的核心循环:
          for attempt in 1..max_retries:
              try: return operation()
              catch error:
                  classify error
                  if not retryable: raise
                  apply recovery action
                  sleep(delay)

        Args:
            tool_name: 工具名称。
            executor: 工具执行函数（无参，返回结果字符串）。
            max_retries: 覆盖默认最大重试次数。
            recover_fn: 自定义恢复函数（覆盖 classifier 的默认动作）。

        Returns:
            工具执行结果。
        """
        max_retries = max_retries or self._get_max_retries(tool_name)
        last_error = None

        for attempt in range(1, max_retries + 2):  # +1 为首次执行
            try:
                result = executor()

                # 检查是否为错误响应
                try:
                    data = json.loads(result)
                    if "error" in data:
                        # 模拟异常以便分类器处理
                        raise RuntimeError(data["error"])
                except json.JSONDecodeError:
                    pass  # 非 JSON 结果，视为成功

                return result

            except Exception as error:
                last_error = error

                # 检查是否应该重试
                if not self.classifier.should_retry(
                    error, attempt, tool_name, self.retryable_tools
                ):
                    # 不可重试，直接返回错误
                    logger.warning(
                        f"工具 '{tool_name}' 失败且不可重试: {error}"
                    )
                    return json.dumps({
                        "error": f"工具执行失败: {type(error).__name__}: {error}"
                    })

                # 获取重试信息
                retry_info = self.classifier.get_retry_info(error, attempt)
                if retry_info is None:
                    return json.dumps({
                        "error": f"工具执行失败: {type(error).__name__}: {error}"
                    })

                # 执行恢复动作
                action = recover_fn or retry_info.action
                await self._apply_recovery(action, tool_name, error)

                # 记录重试日志
                logger.info(
                    f"工具 '{tool_name}' 第 {attempt}/{max_retries} 次重试 "
                    f"({retry_info.reason}, 等待 {retry_info.delay_ms}ms)"
                )

                # 指数退避等待
                await asyncio.sleep(retry_info.delay_ms / 1000)

        # 超过最大重试次数
        logger.error(
            f"工具 '{tool_name}' 超过最大重试次数 {max_retries}: {last_error}"
        )
        return json.dumps({
            "error": f"工具执行失败（已重试 {max_retries} 次）: "
                     f"{type(last_error).__name__}: {last_error}",
            "retries_exhausted": True,
        })

    # ─── 内部方法 ─────────────────────────────────────────────

    def _get_max_retries(self, tool_name: str) -> int:
        """获取工具的最大重试次数。"""
        if tool_name in self.tool_configs:
            return self.tool_configs[tool_name].max_retries
        return self.classifier.max_retries

    async def _apply_recovery(
        self,
        action: RecoveryAction | Callable,
        tool_name: str,
        error: Exception,
    ):
        """执行恢复动作。

        参考 Claude Code:
        - reconnect:  → disableKeepAlive() + 重新创建客户端
        - refresh_credentials → handleOAuth401Error() + getClient()
        - backoff:    → sleep(delay)
        """
        if callable(action):
            result = action()
            if asyncio.iscoroutine(result):
                await result
            return

        if action == RecoveryAction.RECONNECT:
            logger.debug(f"工具 '{tool_name}': 执行重连恢复动作")

        elif action == RecoveryAction.REFRESH_CREDENTIALS:
            logger.debug(f"工具 '{tool_name}': 执行凭证刷新恢复动作")
            # 触发凭证刷新事件
            # 具体的 OAuth/token 刷新由 provider 模块处理
            from src.conversation.events import EventBus, EventType
            EventBus.emit(EventType.CREDENTIAL_EXPIRED, {
                "tool": tool_name,
                "error": str(error),
            })

        elif action == RecoveryAction.BACKOFF:
            logger.debug(f"工具 '{tool_name}': 执行退避恢复动作")
