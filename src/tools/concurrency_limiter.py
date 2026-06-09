"""工具并发限流器。

设计参考: Claude Code toolOrchestration.ts 中的并发控制:
  - getMaxToolUseConcurrency(): 环境变量 NANOHERMES_MAX_TOOL_CONCURRENCY
  - partitionToolCalls(): 按 isConcurrencySafe 分为并发组/串行组
  - runToolsConcurrently(): 并发组内并行执行

NanoHermes 适配:
  - 使用 asyncio.Semaphore 替代 Promise.all 的并发控制
  - 支持每工具自定义 max_concurrent_instances
  - 排队超时保护防止无限等待

设计理由:
- 全局信号量控制总并发数，避免系统过载
- 每工具信号量控制单个工具的并发实例数（如 terminal 只能 1 个）
- 并发分组优化：连续的安全工具合并执行，减少竞争
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ─── 配置常量 ─────────────────────────────────────────────────
# 参考 Claude Code:
#   function getMaxToolUseConcurrency(): number {
#     return parseInt(
#       process.env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY || '', 10
#     ) || 10
#   }

DEFAULT_MAX_CONCURRENCY = 10
ENV_VAR_NAME = "NANOHERMES_MAX_TOOL_CONCURRENCY"
QUEUE_TIMEOUT = 120  # 排队超时 120 秒


def get_max_tool_concurrency() -> int:
    """获取最大工具并发数。

    参考 Claude Code getMaxToolUseConcurrency() 的设计:
    - 优先读取环境变量
    - 未设置时使用默认值 10
    - 环境变量解析失败时回退到默认值
    """
    env_value = os.environ.get(ENV_VAR_NAME, "")
    if env_value:
        try:
            value = int(env_value)
            if value > 0:
                return value
        except ValueError:
            logger.warning(
                f"无效的环境变量 {ENV_VAR_NAME}='{env_value}'，"
                f"使用默认值 {DEFAULT_MAX_CONCURRENCY}"
            )
    return DEFAULT_MAX_CONCURRENCY


# ─── 并发限流器 ───────────────────────────────────────────────


@dataclass
class ToolConcurrencyConfig:
    """单个工具的并发配置。

    参考 Claude Code: 不同工具有不同的并发特性。
    - terminal: 通常只允许 1 个实例（避免命令交叉）
    - read_file: 允许较高并发（纯读取，无副作用）
    - write_file: 通常只允许 1 个实例（避免文件冲突）
    """
    tool_name: str
    max_concurrent_instances: int = 1    # 该工具最大并发实例数
    is_concurrency_safe: bool = False    # 是否可与其他工具并发执行


class ToolConcurrencyLimiter:
    """工具并发限流器。

    使用方式:
        limiter = ToolConcurrencyLimiter(max_concurrency=10)

        # 方式 1: 单个工具执行
        result = await limiter.execute("read_file", lambda: dispatch("read_file", args))

        # 方式 2: 批量工具执行（自动分组）
        results = await limiter.execute_batch(tool_calls)

    并发控制层次:
      1. 全局信号量: max_tool_concurrency (默认 10)
      2. 每工具信号量: max_concurrent_instances (默认 1)
      3. 并发分组: is_concurrency_safe 决定串行/并行
    """

    def __init__(
        self,
        max_concurrency: int | None = None,
        tool_configs: dict[str, ToolConcurrencyConfig] | None = None,
    ):
        # 全局信号量: 控制所有工具的总并发数
        self.max_concurrency = max_concurrency or get_max_tool_concurrency()
        self.global_semaphore = asyncio.Semaphore(self.max_concurrency)

        # 每工具信号量: 控制单个工具的并发实例数
        self.tool_configs: dict[str, ToolConcurrencyConfig] = tool_configs or {}
        self._tool_semaphores: dict[str, asyncio.Semaphore] = {}

        # 执行状态追踪
        self._active_tools: dict[str, int] = {}  # tool_name → 正在执行的数量
        self._lock = asyncio.Lock()

    def register_tool(
        self,
        tool_name: str,
        max_concurrent_instances: int = 1,
        is_concurrency_safe: bool = False,
    ):
        """注册工具的并发配置。"""
        config = ToolConcurrencyConfig(
            tool_name=tool_name,
            max_concurrent_instances=max_concurrent_instances,
            is_concurrency_safe=is_concurrency_safe,
        )
        self.tool_configs[tool_name] = config
        self._tool_semaphores[tool_name] = asyncio.Semaphore(
            max_concurrent_instances
        )

    async def execute(
        self,
        tool_name: str,
        executor: callable,
        timeout: float | None = None,
    ) -> str:
        """执行单个工具调用，受并发限流器控制。

        执行流程:
          1. 获取全局信号量（总并发数限制）
          2. 获取工具信号量（单工具并发数限制）
          3. 执行工具
          4. 释放信号量
        """
        timeout = timeout or QUEUE_TIMEOUT

        try:
            # 步骤 1: 获取全局信号量（带超时保护）
            await asyncio.wait_for(
                self.global_semaphore.acquire(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error(
                f"工具 '{tool_name}' 排队超时（{timeout}s），"
                f"系统负载过高（当前限制: {self.max_concurrency}）"
            )
            return json.dumps({
                "error": f"工具执行排队超时（{timeout}s），系统负载过高"
            })

        try:
            # 步骤 2: 获取工具信号量
            tool_sem = self._get_tool_semaphore(tool_name)
            await tool_sem.acquire()

            try:
                # 步骤 3: 更新活跃计数
                async with self._lock:
                    self._active_tools[tool_name] = \
                        self._active_tools.get(tool_name, 0) + 1

                # 步骤 4: 执行工具
                result = executor()

                # 处理异步 executor
                if asyncio.iscoroutine(result):
                    result = await result

                return result

            finally:
                # 步骤 5: 清理
                async with self._lock:
                    self._active_tools[tool_name] -= 1
                    if self._active_tools[tool_name] <= 0:
                        del self._active_tools[tool_name]

                tool_sem.release()

        finally:
            self.global_semaphore.release()

    async def execute_batch(
        self,
        tool_calls: list[dict],
        executor: callable,
    ) -> list[str]:
        """批量执行工具调用，自动分组和限流。

        参考 Claude Code partitionToolCalls() 的分组逻辑:
          - 连续的安全工具合并为并发组
          - 非安全工具单独执行为串行组
          - 并发组内通过 asyncio.gather() 并行执行
          - 组间严格顺序
        """
        # 步骤 1: 分组
        batches = self.partition_tool_calls(tool_calls)

        # 步骤 2: 按组执行
        all_results = []

        for batch in batches:
            is_safe = batch["is_concurrency_safe"]
            calls = batch["calls"]

            if is_safe and len(calls) > 1:
                # 并发组: 并行执行
                tasks = [
                    self.execute(
                        tool_name=call["name"],
                        executor=lambda c=call: executor(
                            c["name"], c.get("args", {})
                        ),
                    )
                    for call in calls
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理异常结果
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        results[i] = json.dumps({
                            "error": f"工具执行失败: "
                                     f"{type(result).__name__}: {result}"
                        })

                all_results.extend(results)

            else:
                # 串行组: 逐个执行
                for call in calls:
                    result = await self.execute(
                        tool_name=call["name"],
                        executor=lambda c=call: executor(
                            c["name"], c.get("args", {})
                        ),
                    )
                    all_results.append(result)

        return all_results

    # ─── 分组逻辑 ─────────────────────────────────────────────

    def partition_tool_calls(
        self,
        tool_calls: list[dict],
    ) -> list[dict]:
        """将工具调用分为并发组和串行组。

        参考 Claude Code partitionToolCalls() 的 reduce 逻辑:
          - 连续的安全工具合并为同一个并发组
          - 遇到非安全工具时，开始新的串行组
          - 每个组标记 isConcurrencySafe
        """
        batches: list[dict] = []

        for call in tool_calls:
            tool_name = call["name"]
            config = self.tool_configs.get(tool_name)
            is_safe = config.is_concurrency_safe if config else False

            # 如果当前工具是安全的，且最后一组也是安全的 → 合并
            if is_safe and batches and batches[-1]["is_concurrency_safe"]:
                batches[-1]["calls"].append(call)
            else:
                # 开始新组
                batches.append({
                    "is_concurrency_safe": is_safe,
                    "calls": [call],
                })

        return batches

    # ─── 内部方法 ─────────────────────────────────────────────

    def _get_tool_semaphore(self, tool_name: str) -> asyncio.Semaphore:
        """获取或创建工具信号量。

        设计理由:
          - 懒加载信号量，避免预创建所有工具的信号量
          - 未注册的工具使用默认信号量（max=1）
        """
        if tool_name not in self._tool_semaphores:
            config = self.tool_configs.get(tool_name)
            max_instances = config.max_concurrent_instances if config else 1
            self._tool_semaphores[tool_name] = asyncio.Semaphore(max_instances)
        return self._tool_semaphores[tool_name]

    @property
    def active_count(self) -> int:
        """当前正在执行的工具总数。"""
        return sum(self._active_tools.values())

    def get_tool_active_count(self, tool_name: str) -> int:
        """获取指定工具正在执行的数量。"""
        return self._active_tools.get(tool_name, 0)

    def get_status(self) -> dict:
        """获取限流器状态。"""
        return {
            "max_concurrency": self.max_concurrency,
            "active_tools": dict(self._active_tools),
            "total_active": self.active_count,
            "registered_tools": {
                name: {
                    "max_concurrent_instances": cfg.max_concurrent_instances,
                    "is_concurrency_safe": cfg.is_concurrency_safe,
                }
                for name, cfg in self.tool_configs.items()
            },
        }
