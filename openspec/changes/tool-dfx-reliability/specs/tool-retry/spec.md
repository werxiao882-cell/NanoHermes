## ADDED Requirements

### Requirement: Tool error classification

系统 SHALL 实现 `ToolErrorClassifier`，将工具执行错误分类为可重试或不可重试，并返回建议的延迟时间和恢复动作。

参考 Claude Code `withRetry.ts` 的错误分类体系：
- `isTransientCapacityError()` → 429/529 → 重试
- `isStaleConnectionError()` → ECONNRESET/EPIPE → 重连
- `isOAuthTokenRevokedError()` → 403 → 刷新 token
- `isBedrockAuthError()` → Bedrock 认证 → 刷新凭证
- Fast mode cooldown → 限流降级

#### Scenario: 连接错误被分类为可重试
- **WHEN** 工具执行失败，错误包含 `ECONNRESET`、`EPIPE`、`Connection refused`、`Timeout`
- **THEN** 分类为 `RetryableError`，建议延迟 = `base_delay * 2^attempt`，动作 = `reconnect`

#### Scenario: 限流错误被分类为可重试
- **WHEN** 错误包含 `429`、`rate limit`、`529`、`overloaded`
- **THEN** 分类为 `RetryableError`，限流退避 = `base_delay * 2^attempt * 2`（加倍），动作 = `backoff`

#### Scenario: 认证错误触发凭证刷新
- **WHEN** 错误包含 `401`、`Unauthorized`、`token expired`
- **THEN** 分类为 `RetryableError`，动作 = `refresh_credentials`

#### Scenario: 工具内部错误不可重试
- **WHEN** 错误为 `ValueError`、`TypeError`、`PermissionError`、`FileNotFoundError`
- **THEN** 分类为 `NonRetryableError`，动作 = `fail`

### Implementation Pseudo-Code

**设计参考**: Claude Code `withRetry.ts` (822 行, 29KB) — 完整的错误分类 + 重试 + 退避体系。

```python
"""src/tools/retry_classifier.py

工具错误分类器。

设计参考: Claude Code withRetry.ts 中的错误分类体系:
  - isTransientCapacityError() → 429/529 → 重试
  - isStaleConnectionError()   → ECONNRESET/EPIPE → 重连
  - isOAuthTokenRevokedError() → 403 → 刷新 token
  - handleFastModeCooldown()   → 限流 → 降级
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ─── 错误恢复动作 ─────────────────────────────────────────────
# 参考 Claude Code: 不同错误类型需要不同的恢复动作
# - reconnect: 关闭旧连接，创建新连接后重试
# - backoff:  退避等待后重试（限流场景）
# - refresh_credentials: 刷新凭证后重试
# - fail:     不可恢复，直接返回错误


class RecoveryAction(str, Enum):
    """错误恢复动作枚举。"""
    RECONNECT = "reconnect"
    BACKOFF = "backoff"
    REFRESH_CREDENTIALS = "refresh_credentials"
    FAIL = "fail"


# ─── 错误分类结果 ─────────────────────────────────────────────


@dataclass
class ErrorClassification:
    """错误分类结果。

    参考 Claude Code RetryContext + CannotRetryError 的设计:
    - is_retryable: 是否可重试
    - action:       恢复动作
    - delay_ms:     建议延迟（毫秒）
    - reason:       分类理由（用于日志和调试）
    - extra:        额外上下文（如 Retry-After header 值）
    """
    is_retryable: bool
    action: RecoveryAction
    delay_ms: int
    reason: str
    extra: dict | None = None


# ─── 错误模式定义 ─────────────────────────────────────────────
# 参考 Claude Code: 每个错误模式对应特定的恢复策略
# 正则表达式按优先级排列（先匹配的优先）

# 1. 连接错误 → reconnect
# Claude Code: isStaleConnectionError() 检测 ECONNRESET/EPIPE
CONNECTION_PATTERNS = [
    re.compile(r"ECONNRESET", re.IGNORECASE),
    re.compile(r"EPIPE", re.IGNORECASE),
    re.compile(r"Connection (?:refused|reset|timed?out)", re.IGNORECASE),
    re.compile(r"Broken pipe", re.IGNORECASE),
    re.compile(r"Network is unreachable", re.IGNORECASE),
]

# 2. 认证错误 → refresh_credentials
# Claude Code: 401 + isOAuthTokenRevokedError()
AUTH_PATTERNS = [
    re.compile(r"401", re.IGNORECASE),
    re.compile(r"Unauthorized", re.IGNORECASE),
    re.compile(r"token (?:expired|invalid|revoked)", re.IGNORECASE),
    re.compile(r"Authentication failed", re.IGNORECASE),
    re.compile(r"Invalid API key", re.IGNORECASE),
]

# 3. 限流错误 → backoff（退避加倍）
# Claude Code: 429/529 + isTransientCapacityError() + triggerFastModeCooldown()
RATE_LIMIT_PATTERNS = [
    re.compile(r"429", re.IGNORECASE),
    re.compile(r"529", re.IGNORECASE),
    re.compile(r"rate ?limit", re.IGNORECASE),
    re.compile(r"too many requests", re.IGNORECASE),
    re.compile(r"overloaded", re.IGNORECASE),
    re.compile(r"capacity exceeded", re.IGNORECASE),
    re.compile(r"Retry-After:\s*(\d+)", re.IGNORECASE),  # 提取 Retry-After 值
]

# 4. 不可重试错误 → fail
# 这些是工具逻辑错误，重试无意义
NON_RETRYABLE_TYPES = {
    ValueError, TypeError, AssertionError,
    FileNotFoundError, PermissionError, IsADirectoryError,
    KeyError, AttributeError, SyntaxError,
}


# ─── 配置常量 ─────────────────────────────────────────────────
# 参考 Claude Code:
#   BASE_DELAY_MS = 500        # 基础退避延迟
#   MAX_529_RETRIES = 3        # 529 错误最多 3 次
#   DEFAULT_MAX_RETRIES = 10   # 最大重试次数
#   PERSISTENT_MAX_BACKOFF_MS = 5 * 60 * 1000  # 最大退避 5 分钟

BASE_DELAY_MS = 500
MAX_DELAY_MS = 60_000       # 最大延迟 60 秒
MAX_RETRIES_DEFAULT = 3     # 默认最大重试次数
JITTER_RATIO = 0.5          # 抖动比例（±50%）


# ─── 核心分类器 ───────────────────────────────────────────────


class ToolErrorClassifier:
    """工具执行错误分类器。

    设计参考: Claude Code withRetry.ts 中的错误分类逻辑。

    分类优先级:
      1. 连接错误  → reconnect（最优先，网络层问题）
      2. 认证错误  → refresh_credentials（凭证过期）
      3. 限流错误  → backoff（服务端容量问题）
      4. 不可重试  → fail（工具逻辑错误）

    使用方式:
        classifier = ToolErrorClassifier()
        result = classifier.classify(error, attempt=2)
        if result.is_retryable:
            await asyncio.sleep(result.delay_ms / 1000)
            # 执行恢复动作后重试
    """

    def __init__(
        self,
        base_delay_ms: int = BASE_DELAY_MS,
        max_delay_ms: int = MAX_DELAY_MS,
        max_retries: int = MAX_RETRIES_DEFAULT,
    ):
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.max_retries = max_retries

    def classify(
        self,
        error: Exception,
        attempt: int = 1,
        response_headers: dict | None = None,
    ) -> ErrorClassification:
        """将错误分类为可重试或不可重试。

        Args:
            error: 捕获到的异常。
            attempt: 当前重试次数（1-based）。
            response_headers: HTTP 响应头（用于提取 Retry-After）。

        Returns:
            ErrorClassification 分类结果。
        """
        error_str = str(error)
        error_type = type(error)

        # ── 步骤 1: 检查是否为不可重试的工具逻辑错误 ──
        # 优先检查：逻辑错误无需网络诊断，直接返回
        if isinstance(error, tuple(NON_RETRYABLE_TYPES)):
            return ErrorClassification(
                is_retryable=False,
                action=RecoveryAction.FAIL,
                delay_ms=0,
                reason=f"不可重试的工具逻辑错误: {error_type.__name__}",
            )

        # ── 步骤 2: 检查连接错误 → reconnect ──
        # 参考: Claude Code isStaleConnectionError()
        for pattern in CONNECTION_PATTERNS:
            if pattern.search(error_str):
                delay = self._calculate_delay(attempt, multiplier=1.0)
                return ErrorClassification(
                    is_retryable=True,
                    action=RecoveryAction.RECONNECT,
                    delay_ms=delay,
                    reason=f"连接错误（匹配 {pattern.pattern}），建议重连",
                )

        # ── 步骤 3: 检查认证错误 → refresh_credentials ──
        # 参考: Claude Code isOAuthTokenRevokedError()
        for pattern in AUTH_PATTERNS:
            if pattern.search(error_str):
                return ErrorClassification(
                    is_retryable=True,
                    action=RecoveryAction.REFRESH_CREDENTIALS,
                    delay_ms=self.base_delay_ms,  # 认证刷新不需要退避
                    reason="认证错误，建议刷新凭证",
                )

        # ── 步骤 4: 检查限流错误 → backoff ──
        # 参考: Claude Code isTransientCapacityError() + triggerFastModeCooldown()
        for pattern in RATE_LIMIT_PATTERNS:
            match = pattern.search(error_str)
            if match:
                # 提取 Retry-After header 值（如有）
                retry_after = self._extract_retry_after(
                    response_headers, match
                )
                # 限流退避加倍: multiplier=2.0
                delay = retry_after or self._calculate_delay(
                    attempt, multiplier=2.0
                )
                return ErrorClassification(
                    is_retryable=True,
                    action=RecoveryAction.BACKOFF,
                    delay_ms=delay,
                    reason=f"限流错误（匹配 {pattern.pattern}），建议退避",
                    extra={"retry_after": retry_after} if retry_after else None,
                )

        # ── 步骤 5: 未知错误 → 保守视为不可重试 ──
        # 设计理由: fail-closed 策略，未知错误不盲目重试
        return ErrorClassification(
            is_retryable=False,
            action=RecoveryAction.FAIL,
            delay_ms=0,
            reason=f"未知错误类型: {error_type.__name__}: {error_str}",
        )

    def should_retry(
        self,
        error: Exception,
        attempt: int,
        tool_name: str,
        retryable_tools: set[str] | None = None,
    ) -> bool:
        """判断是否应该重试。

        Args:
            error: 捕获到的异常。
            attempt: 当前重试次数（1-based）。
            tool_name: 工具名称。
            retryable_tools: 可重试工具白名单。

        Returns:
            是否应该重试。
        """
        # 检查工具是否在可重试白名单中
        if retryable_tools and tool_name not in retryable_tools:
            logger.debug(f"工具 '{tool_name}' 不在可重试白名单中，跳过重试")
            return False

        # 检查重试次数上限
        if attempt > self.max_retries:
            logger.debug(f"工具 '{tool_name}' 已达最大重试次数 {self.max_retries}")
            return False

        # 检查错误是否可重试
        classification = self.classify(error, attempt)
        return classification.is_retryable

    def get_retry_info(
        self,
        error: Exception,
        attempt: int,
    ) -> ErrorClassification | None:
        """获取重试信息（延迟 + 动作）。

        Args:
            error: 捕获到的异常。
            attempt: 当前重试次数（1-based）。

        Returns:
            重试信息，如果不可重试则返回 None。
        """
        classification = self.classify(error, attempt)
        if not classification.is_retryable:
            return None
        return classification

    # ─── 内部方法 ─────────────────────────────────────────────

    def _calculate_delay(
        self,
        attempt: int,
        multiplier: float = 1.0,
    ) -> int:
        """计算指数退避延迟 + 随机抖动。

        参考 Claude Code:
          - BASE_DELAY_MS = 500
          - 指数退避: base * 2^attempt
          - 限流场景 multiplier = 2.0（退避加倍）
          - 最大延迟 PERSISTENT_MAX_BACKOFF_MS = 5min

        为什么加抖动？
          - 避免多个工具同时重试导致的惊群效应（thundering herd）
          - 抖动范围: delay ± (delay * JITTER_RATIO)

        Args:
            attempt: 当前重试次数（1-based）。
            multiplier: 延迟倍数（限流场景为 2.0）。

        Returns:
            延迟毫秒数。
        """
        import random

        # 指数退避: 500 * 2^1 = 1000ms, 500 * 2^2 = 2000ms, ...
        base = self.base_delay_ms * (2 ** attempt) * multiplier

        # 添加随机抖动: ±50%
        jitter = base * JITTER_RATIO * (random.random() - 0.5) * 2
        delay = int(base + jitter)

        # 限制最大延迟
        return min(delay, self.max_delay_ms)

    def _extract_retry_after(
        self,
        headers: dict | None,
        pattern_match: re.Match | None,
    ) -> int | None:
        """从响应头或错误信息中提取 Retry-After 值。

        参考 Claude Code: getRetryAfterMs(error) 从 HTTP header 提取。

        Args:
            headers: HTTP 响应头。
            pattern_match: 正则匹配结果。

        Returns:
            Retry-After 毫秒数，如果未找到则返回 None。
        """
        # 优先从 HTTP header 提取
        if headers:
            retry_after = headers.get("Retry-After")
            if retry_after:
                try:
                    # Retry-After 可能是秒数或 HTTP 日期
                    return int(retry_after) * 1000
                except ValueError:
                    pass

        # 从错误信息中的正则匹配提取
        if pattern_match and pattern_match.lastindex:
            try:
                return int(pattern_match.group(1)) * 1000
            except (ValueError, IndexError):
                pass

        return None
```

### Requirement: Retryable tool whitelist

系统 SHALL 维护可重试工具白名单。只有白名单中的工具在失败时才会自动重试。

#### Scenario: 只读工具默认可重试
- **WHEN** 工具为 `read_file`、`search_files`、`skill_view`、`skills_list`
- **THEN** 自动加入可重试白名单，最大重试次数 = 3

#### Scenario: 写操作工具默认不可重试
- **WHEN** 工具为 `write_file`、`patch`、`terminal`
- **THEN** 不在白名单中，失败时直接返回错误

#### Scenario: 自定义工具声明可重试性
- **WHEN** `build_tool()` 创建时指定 `retryable=True`
- **THEN** 加入白名单，可通过 `max_retries` 自定义次数

### Implementation Pseudo-Code

```python
"""src/tools/retry_manager.py

工具重试管理器。

设计参考: Claude Code withRetry.ts 中的重试循环 + 退避逻辑。
核心流程:
  1. 检查工具是否在可重试白名单中
  2. 使用 classifier 分类错误
  3. 执行恢复动作（reconnect/refresh_credentials/backoff）
  4. 指数退避等待
  5. 重新执行工具
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

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
    改为同步版本以适配 NanoHermes 的 dispatch() 架构。
    """

    def __init__(
        self,
        classifier: ToolErrorClassifier | None = None,
        retryable_tools: set[str] | None = None,
        tool_configs: dict[str, RetryConfig] | None = None,
    ):
        self.classifier = classifier or ToolErrorClassifier()
        self.retryable_tools = retryable_tools or set(DEFAULT_RETRYABLE_TOOLS)
        self.tool_configs = tool_configs or {}

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

        Raises:
            当不可重试或超过最大重试次数时，返回错误 JSON（不抛异常）。
        """
        import json

        max_retries = max_retries or self._get_max_retries(tool_name)
        last_error = None

        for attempt in range(1, max_retries + 2):  # +1 为首次执行
            try:
                # ── 首次执行或重试后执行 ──
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

                # ── 检查是否应该重试 ──
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

                # ── 获取重试信息 ──
                retry_info = self.classifier.get_retry_info(error, attempt)
                if retry_info is None:
                    return json.dumps({
                        "error": f"工具执行失败: {type(error).__name__}: {error}"
                    })

                # ── 执行恢复动作 ──
                action = recover_fn or retry_info.action
                await self._apply_recovery(action, tool_name, error)

                # ── 记录重试日志 ──
                logger.info(
                    f"工具 '{tool_name}' 第 {attempt}/{max_retries} 次重试 "
                    f"({retry_info.reason}, 等待 {retry_info.delay_ms}ms)"
                )

                # ── 指数退避等待 ──
                await asyncio.sleep(retry_info.delay_ms / 1000)

        # ── 超过最大重试次数 ──
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
            # 自定义恢复函数
            result = action()
            if asyncio.iscoroutine(result):
                await result
            return

        if action == RecoveryAction.RECONNECT:
            logger.debug(f"工具 '{tool_name}': 执行重连恢复动作")
            # 设计理由: 对于工具级别，reconnect 主要意味着
            # 清理可能的连接池状态，下一次调用会创建新连接
            # 实际连接管理由具体工具（如 MCP 客户端）负责

        elif action == RecoveryAction.REFRESH_CREDENTIALS:
            logger.debug(f"工具 '{tool_name}': 执行凭证刷新恢复动作")
            # 设计理由: 触发凭证刷新事件
            # 具体的 OAuth/token 刷新由 provider 模块处理
            # 这里只是信号通知
            from src.conversation.events import EventBus, EventType
            EventBus.emit(EventType.CREDENTIAL_EXPIRED, {
                "tool": tool_name,
                "error": str(error),
            })

        elif action == RecoveryAction.BACKOFF:
            # backoff 的等待由主循环的 asyncio.sleep() 处理
            logger.debug(f"工具 '{tool_name}': 执行退避恢复动作")
```
