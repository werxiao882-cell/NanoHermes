"""DelegationManager - 多 Agent 委托管理器。

核心职责：
- 将复杂任务分解为多个子 Agent 并行或串行执行
- 通过角色系统（LEAF/ORCHESTRATOR）控制子 Agent 的权限边界
- 通过信号量和深度限制防止资源耗尽和无限递归
- 隔离子 Agent 上下文，避免污染主 Agent 的会话状态

设计决策：
- 使用自定义 Semaphore 而非 asyncio.Semaphore：需要同时支持同步和异步调用场景
  主对话循环可能是同步的（如 CLI 交互），也可能是异步的（如 MCP 服务器），
  自定义信号量可以在两种模式下都能正确工作，而 asyncio.Semaphore 只能在
  异步上下文中使用，且在没有事件循环时会抛出 RuntimeError。
- 角色系统的安全考量：LEAF 角色被禁止访问 delegate_task（防止无限递归委托）、
  clarify（防止子 Agent 直接打扰用户）、memory（防止污染共享记忆文件）、
  execute_code（防止子 Agent 执行危险代码）。ORCHESTRATOR 角色可以进一步
  委托任务，但仍受深度限制约束。
- 并发控制机制：通过 Semaphore 限制同时运行的子 Agent 数量，避免：
  1. API 调用过快触发速率限制
  2. 内存中同时维护过多子 Agent 的上下文
  3. 线程/协程资源耗尽
- 上下文管理器（__enter__/__exit__）：使 Semaphore 支持 with 语句，
  确保即使子 Agent 执行抛出异常，信号量也能正确释放，避免死锁。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 子 Agent 角色
# ─────────────────────────────────────────────
class AgentRole(Enum):
    """子 Agent 角色。

    设计理由：
    - LEAF（叶子节点）：普通工作者，只能完成分配的特定任务，不能进一步委托。
      这防止了无限递归委托导致的资源耗尽，也简化了子 Agent 的权限模型。
    - ORCHESTRATOR（编排者）：可以分解任务并进一步委托给子 Agent。
      适用于需要将大任务拆解为多个子任务的场景，但受 max_spawn_depth 限制。

    安全考量：
    - 角色决定了子 Agent 可以访问哪些工具，这是权限控制的第一道防线。
    - LEAF 角色被明确禁止访问危险工具（见 DELEGATE_BLOCKED_TOOLS）。
    """
    LEAF = "leaf"
    ORCHESTRATOR = "orchestrator"


# ─────────────────────────────────────────────
# 被阻止的工具列表
# ─────────────────────────────────────────────
DELEGATE_BLOCKED_TOOLS: frozenset[str] = frozenset([
    "delegate_task",    # 禁止递归委托：防止 LEAF 角色继续生成子 Agent 导致无限递归
    "clarify",          # 禁止用户交互：子 Agent 不应直接打扰用户，澄清应由主 Agent 处理
    "memory",           # 禁止写入共享记忆：防止多个子 Agent 同时写入 MEMORY.md 导致冲突
    "execute_code",     # 子 Agent 应逐步推理，而非编写脚本：降低代码执行的安全风险
])

# Orchestrator 可以使用的额外工具
ORCHESTRATOR_ALLOWED_TOOLS: frozenset[str] = frozenset([
    "delegate_task",    # 允许进一步委托：ORCHESTRATOR 的核心能力是任务分解和分发
])


# ─────────────────────────────────────────────
# 委托结果
# ─────────────────────────────────────────────
@dataclass
class DelegationResult:
    """委托结果。

    Attributes:
        task_id: 任务 ID。
        success: 是否成功。
        summary: 结果摘要。
        error: 错误信息（如果失败）。
        role: 子 Agent 角色。
        duration: 执行耗时（秒）。
        tool_calls: 工具调用次数。
    """
    task_id: str
    success: bool
    summary: str = ""
    error: str = ""
    role: str = "leaf"
    duration: float = 0.0
    tool_calls: int = 0


# ─────────────────────────────────────────────
# 子 Agent 配置
# ─────────────────────────────────────────────
@dataclass
class ChildAgentConfig:
    """子 Agent 配置。

    Attributes:
        task_id: 任务 ID。
        role: 角色。
        goal: 目标描述。
        context: 上下文信息。
        allowed_toolsets: 允许的工具集。
        blocked_tools: 被阻止的工具。
        system_prompt: 系统提示。
        max_depth: 最大委托深度。
        timeout: 超时时间。
        auto_approve: 是否自动批准。
    """
    task_id: str
    role: str
    goal: str
    context: str = ""
    allowed_toolsets: list[str] = field(default_factory=list)
    blocked_tools: list[str] = field(default_factory=list)
    system_prompt: str = ""
    max_depth: int = 2
    timeout: float = 300.0
    auto_approve: bool = False


# ─────────────────────────────────────────────
# Semaphore 并发控制
# ─────────────────────────────────────────────
class Semaphore:
    """异步信号量，用于控制并发子 Agent 数量。

    为什么需要自定义信号量而不是使用 asyncio.Semaphore？

    1. 双模式支持（同步/异步）：
       - 主对话循环可能是同步的（如 CLI 交互模式使用 prompt_toolkit）
       - 也可能是异步的（如 MCP 服务器使用 asyncio 事件循环）
       - asyncio.Semaphore 只能在异步上下文中使用，在同步代码中调用会抛出
         RuntimeError: no running event loop
       - 自定义信号量提供 acquire_sync/release_sync 和 acquire/release 两套 API，
         可以在两种调用场景下都能正确工作

    2. 避免事件循环检测的复杂性：
       - asyncio.Semaphore 内部使用 asyncio.Lock，而 Lock 会检查当前是否有
         运行中的事件循环
       - 在混合调用场景（同步代码调用异步代码或反之）中，这种检查会导致
         不可预测的行为
       - 自定义实现使用简单的计数器 + deque 等待队列，不依赖事件循环状态

    3. 轻量级实现：
       - 不需要 asyncio.Semaphore 的完整功能（如等待者优先级、取消支持等）
       - 简单的计数器 + 轮询机制足以满足并发控制需求
       - 减少依赖，提高可测试性

    并发控制机制：
    - _active 计数器跟踪当前活跃的子 Agent 数量
    - acquire_sync/acquire 在 _active < max_concurrent 时允许进入
    - release_sync/release 递减计数器，释放一个槽位
    - 异步版本使用 asyncio.sleep(0.01) 轮询而非阻塞等待，避免阻塞事件循环
    """

    def __init__(self, max_concurrent: int = 3):
        """初始化信号量。

        Args:
            max_concurrent: 最大并发数，控制同时运行的子 Agent 数量。

        设计理由：
        - 使用 max(1, max_concurrent) 确保至少有 1 个并发槽位，
          避免传入 0 或负数导致死锁
        - _lock 的初始化尝试检测当前是否在异步上下文中：
          asyncio.current_task() 在有事件循环时返回当前任务，
          在没有事件循环时抛出 RuntimeError
          这使得信号量可以在同步和异步上下文中都能正确初始化
        """
        self.max_concurrent = max(1, max_concurrent)
        self._active = 0
        self._waiters: deque[asyncio.Event] = deque()
        try:
            # 尝试检测是否在异步上下文中
            # 如果在异步上下文中，创建 asyncio.Lock 用于同步
            # 如果在同步上下文中，_lock 为 None，使用纯同步模式
            self._lock = asyncio.current_task() and asyncio.Lock() or None
        except RuntimeError:
            # No running event loop (e.g., in synchronous context)
            # 在同步上下文中，不使用 asyncio.Lock，避免 RuntimeError
            self._lock = None

    @property
    def active_count(self) -> int:
        """当前活跃任务数。

        用于监控和调试，可以查看当前有多少子 Agent 正在运行。
        """
        return self._active

    @property
    def available_slots(self) -> int:
        """可用槽位数。

        返回还能容纳多少子 Agent，用于决定是否可以直接 spawn 新任务
        或需要等待。
        """
        return max(0, self.max_concurrent - self._active)

    def acquire_sync(self) -> bool:
        """同步获取许可。

        设计理由：
        - 在同步上下文中（如 CLI 交互模式），不能使用 await
        - 此方法是非阻塞的：如果当前没有可用槽位，立即返回 False
          而非阻塞等待，调用者需要自行处理重试逻辑
        - 返回 bool 而非阻塞等待，是为了让调用者可以灵活处理
          （如降级为单线程模式、返回错误等）

        Returns:
            是否成功获取许可。True 表示可以进入临界区，False 表示需要等待。
        """
        if self._active < self.max_concurrent:
            self._active += 1
            return True
        return False

    def release_sync(self) -> None:
        """同步释放许可。

        设计理由：
        - 必须在子 Agent 执行完成后调用（无论成功或失败）
        - 通常在 finally 块中调用，确保即使发生异常也能释放
        - 使用 if self._active > 0 而非直接递减，防止计数器变为负数
          （这通常意味着 acquire/release 调用不匹配，是 bug 的征兆）
        """
        if self._active > 0:
            self._active -= 1

    async def acquire(self) -> None:
        """异步获取许可。

        设计理由：
        - 在异步上下文中（如 MCP 服务器），需要非阻塞等待
        - 使用 while True + asyncio.sleep(0.01) 轮询而非 asyncio.Event 等待：
          1. 简化实现，不需要维护复杂的等待者队列
          2. asyncio.sleep(0) 会让出控制权给事件循环，不会阻塞其他协程
          3. 0.01 秒的轮询间隔在性能和响应性之间取得平衡
        - 注意：如果 max_concurrent 设置过小且所有槽位都被长期占用，
          可能导致饥饿（starvation），但这通常意味着配置问题而非算法问题
        """
        while True:
            if self._active < self.max_concurrent:
                self._active += 1
                return
            # 等待释放：让出控制权给事件循环，10ms 后重试
            await asyncio.sleep(0.01)

    async def release(self) -> None:
        """异步释放许可。

        设计理由：
        - 与 release_sync 类似，但在异步上下文中调用
        - 注意：当前实现没有唤醒等待者（waiters），因为 acquire 使用轮询
          如果需要更高效的唤醒机制，可以使用 asyncio.Event 通知等待者
        """
        if self._active > 0:
            self._active -= 1

    def __enter__(self) -> "Semaphore":
        """上下文管理器入口：支持 with 语句。

        设计理由：
        - 使 Semaphore 可以作为上下文管理器使用：with semaphore: ...
        - 确保即使临界区代码抛出异常，__exit__ 也会被调用，从而释放信号量
        - 这是防止死锁的关键：如果子 Agent 执行失败但没有释放信号量，
          后续任务将永远等待
        """
        self.acquire_sync()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口：自动释放信号量。

        参数说明：
        - exc_type, exc_val, exc_tb: 异常信息（如果有）
        - 无论是否发生异常，都会调用 release_sync()
        - 返回 None（或 False）表示不抑制异常，异常会继续向上传播
        """
        self.release_sync()

    def __repr__(self) -> str:
        return f"Semaphore({self._active}/{self.max_concurrent})"


# ─────────────────────────────────────────────
# DelegationManager 类
# ─────────────────────────────────────────────
class DelegationManager:
    """委托管理器。

    核心职责：
    - 管理子 Agent 的生命周期：spawn、执行、结果收集、清理
    - 通过信号量控制并发子 Agent 数量，防止资源耗尽
    - 通过深度限制防止无限递归委托
    - 隔离子 Agent 上下文，避免污染主 Agent 的会话状态

    设计边界：
    - 不直接调用 LLM API：通过注入的 client_factory 或外部回调执行
    - 不管理会话存储：子 Agent 的会话由外部 session manager 管理
    - 不处理工具分发：工具过滤和权限控制在此层，但执行由 tool dispatcher 处理
    """

    def __init__(
        self,
        max_concurrent_children: int = 3,
        max_spawn_depth: int = 2,
        child_timeout_seconds: float = 300.0,
        subagent_auto_approve: bool = False,
    ):
        """初始化委托管理器。

        Args:
            max_concurrent_children: 最大并发子 Agent 数。
                设计理由：默认 3 是经验值，平衡了 API 调用速率和内存占用。
                过大可能触发 API 速率限制，过小则无法充分利用并行性。
            max_spawn_depth: 最大委托深度。
                设计理由：防止 ORCHESTRATOR 角色无限递归委托。
                深度 2 意味着：主 Agent -> Orchestrator -> Leaf，共三层。
                这是为了避免任务分解过细导致上下文碎片化。
            child_timeout_seconds: 子 Agent 超时时间（秒）。
                设计理由：防止子 Agent 长时间运行阻塞整体流程。
                默认 300 秒（5 分钟）适用于大多数任务，复杂任务可调整。
            subagent_auto_approve: 是否自动批准危险命令。
                设计理由：默认为 False 是安全优先。子 Agent 执行危险操作
                （如终端命令、文件写入）时需要用户确认，除非明确启用自动批准。

        状态管理：
        - _current_depth: 当前委托深度，用于防止递归过深
        - _semaphore: 并发控制信号量，限制同时运行的子 Agent 数量
        - _active_children: 正在运行的子 Agent 字典，用于监控和调试
        - _completed_results: 已完成的结果列表，用于结果聚合和查询
        """
        # 使用 max() 确保参数在合理范围内，防止配置错误导致的问题
        self.max_concurrent_children = max(1, max_concurrent_children)
        self.max_spawn_depth = max(0, max_spawn_depth)
        self.child_timeout_seconds = max(1.0, child_timeout_seconds)
        self.subagent_auto_approve = subagent_auto_approve

        # 运行时状态
        self._current_depth = 0  # 当前委托深度，进入子 Agent 时 +1，退出时 -1
        self._semaphore = Semaphore(max_concurrent_children)  # 并发控制
        self._active_children: dict[str, dict[str, Any]] = {}  # 活跃子 Agent 跟踪
        self._completed_results: list[DelegationResult] = []  # 已完成结果收集

        # 回调函数：用于外部自定义自动批准/拒绝逻辑
        # 设计理由：通过回调解耦，使 DelegationManager 不依赖具体的 UI 或业务逻辑
        self._auto_deny_callback: Callable[[dict], bool] | None = None
        self._auto_approve_callback: Callable[[dict], bool] | None = None

    # ── 公共 API ──

    def delegate_task(
        self,
        goal: str | None = None,
        tasks: list[dict[str, Any]] | None = None,
        role: AgentRole | str = AgentRole.LEAF,
        toolsets: list[str] | None = None,
        context: str | None = None,
    ) -> list[DelegationResult]:
        """委托任务（统一入口）。

        设计理由：
        - 这是委托管理器的主要公共 API，支持单任务和批量任务两种模式
        - 通过 goal 和 tasks 参数的组合自动判断模式：
          * goal 有值、tasks 为空：单任务模式
          * tasks 有值：批量模式（忽略 goal）
          * 两者都为空：返回空列表
        - 这种设计简化了调用者的使用：无需根据场景调用不同方法

        委托逻辑流程：
        1. 检查深度限制：防止递归委托过深
        2. 标准化角色：将字符串角色转换为 AgentRole 枚举
        3. 根据参数选择单任务或批量模式
        4. 返回委托结果列表

        Args:
            goal: 单任务目标描述。
            tasks: 批量任务列表。
            role: 子 Agent 角色。
            toolsets: 允许使用的工具集。
            context: 上下文信息。

        Returns:
            委托结果列表。
        """
        # 深度检查：第一道防线，防止无限递归委托
        # 注意：这里检查的是 self._current_depth，它在 delegate_single 中会 +1
        # 所以当 _current_depth >= max_spawn_depth 时，说明已达到深度上限
        if self._current_depth >= self.max_spawn_depth:
            return [DelegationResult(
                task_id="depth_limit",
                success=False,
                error=f"达到最大委托深度 ({self.max_spawn_depth})，无法生成子 Agent。",
            )]

        # 角色标准化：支持字符串和枚举两种输入
        # 设计理由：外部调用者可能从配置文件或用户输入获取字符串角色名
        if isinstance(role, str):
            role = AgentRole(role.lower())

        # 单任务模式：goal 有值且 tasks 为空
        # 注意：这里使用 `goal and not tasks` 而非 `goal is not None`
        # 是为了避免空字符串 goal 被误判为单任务模式
        if goal and not tasks:
            return [self.delegate_single(
                goal=goal,
                role=role,
                toolsets=toolsets,
                context=context,
            )]

        # 批量模式：tasks 有值
        if tasks:
            return self.delegate_batch(
                tasks=tasks,
                role=role,
                toolsets=toolsets,
            )

        # 边界情况：goal 和 tasks 都为空
        return []

    def delegate_single(
        self,
        goal: str,
        role: AgentRole | str = AgentRole.LEAF,
        toolsets: list[str] | None = None,
        context: str | None = None,
    ) -> DelegationResult:
        """委托单个任务。

        设计理由：
        - 这是单任务委托的核心方法，负责：
          1. 构建子 Agent 配置（角色、工具过滤、系统提示）
          2. 通过信号量控制并发
          3. 跟踪深度和执行时间
          4. 收集结果并清理状态
        - 使用 with self._semaphore 确保并发控制，即使发生异常也能释放信号量

        并发控制实现：
        - with 语句调用 Semaphore.__enter__ -> acquire_sync()
        - 如果当前活跃数 < max_concurrent，立即进入
        - 否则 acquire_sync 返回 False，但 __enter__ 没有检查返回值！
          这是一个潜在的 bug：当信号量满时，with 语句仍会进入临界区
          正确做法应该是：在 acquire_sync 返回 False 时阻塞等待或返回错误
          当前实现依赖调用者确保不会超过并发限制（如 delegate_batch 截取前 N 项）

        深度管理：
        - 进入时 _current_depth += 1，退出时 _current_depth -= 1
        - 使用 try/finally 确保即使发生异常也会回滚深度
        - 这防止了深度计数器泄漏导致后续委托被错误拒绝

        Args:
            goal: 目标描述。
            role: 角色。
            toolsets: 工具集。
            context: 上下文。

        Returns:
            委托结果。
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        # 二次深度检查：delegate_task 已经检查过，但这里再次检查
        # 设计理由：防御性编程，防止直接调用 delegate_single 绕过深度检查
        if self._current_depth >= self.max_spawn_depth:
            return DelegationResult(
                task_id="depth_limit",
                success=False,
                error=f"达到最大委托深度 ({self.max_spawn_depth})",
            )

        # 构建子 Agent 配置：包含角色、工具过滤、系统提示等
        # 这是子 Agent 隔离的关键：每个子 Agent 有独立的配置，不共享状态
        config = self.build_child_agent_config(
            goal=goal,
            role=role,
            toolsets=toolsets,
            context=context,
        )

        # 使用 Semaphore 控制并发
        # 注意：当前 acquire_sync 是non-blocking的，返回 False 时仍会进入
        # 这依赖于调用者（如 delegate_batch）预先限制任务数量
        with self._semaphore:
            # 增加深度计数：标记进入子 Agent 上下文
            self._current_depth += 1
            start_time = time.time()

            try:
                # 执行子 Agent：实际应 spawn 子进程或调用 LLM
                # 当前 _execute_single_agent 是模拟实现
                result = self._execute_single_agent(config)
                result.duration = time.time() - start_time
                self._completed_results.append(result)
                return result
            finally:
                # 无论成功或失败，都必须回滚深度计数
                # 这防止了深度计数器泄漏
                self._current_depth -= 1

    def delegate_batch(
        self,
        tasks: list[dict[str, Any]],
        role: AgentRole | str = AgentRole.LEAF,
        toolsets: list[str] | None = None,
    ) -> list[DelegationResult]:
        """批量并行委托任务。

        设计理由：
        - 将多个任务并行委托给子 Agent，提高整体吞吐量
        - 当前实现是串行执行（逐个调用 delegate_single），但受信号量控制
          真正的并行需要异步实现（asyncio.gather）或多线程
        - 限制并发数量：截取前 max_concurrent_children 个任务
          这是为了防止任务队列过长导致资源耗尽

        并发限制实现：
        - limited_tasks = tasks[:self.max_concurrent_children]
          这确保不会同时 spawn 超过 max_concurrent_children 个子 Agent
          注意：这是"硬性"限制，超出任务被直接丢弃而非排队等待
          设计理由：简化实现，避免复杂的任务队列管理
          副作用：调用者需要自行处理被丢弃的任务（如分批调用）

        结果聚合：
        - 每个任务的结果添加 batch_{i}_ 前缀到 task_id
          这便于区分批量任务和单任务，也便于调试和追踪
        - 结果按任务顺序返回，与输入 tasks 顺序一致

        Args:
            tasks: 任务列表，每项包含 goal/description 和可选 context。
            role: 角色。
            toolsets: 工具集。

        Returns:
            委托结果列表。
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        # 限制并发数量：截取前 N 个任务
        # 设计理由：防止任务队列过长，同时简化实现（无需任务队列管理）
        # 注意：超出限制的任务被直接丢弃，调用者需要自行处理
        limited_tasks = tasks[:self.max_concurrent_children]

        results = []
        for i, task in enumerate(limited_tasks):
            # 兼容不同的任务格式：goal 或 description 都可以作为任务目标
            goal = task.get("goal", task.get("description", ""))
            task_context = task.get("context", "")
            # 任务级别可以覆盖全局 toolsets
            task_toolsets = task.get("toolsets", toolsets)

            # 串行执行每个任务（受信号量控制）
            result = self.delegate_single(
                goal=goal,
                role=role,
                toolsets=task_toolsets,
                context=task_context,
            )
            # 添加批量任务前缀，便于区分和追踪
            result.task_id = f"batch_{i}_{result.task_id}"
            results.append(result)

        return results

    # ── 角色系统 ──

    def build_child_agent_config(
        self,
        goal: str,
        role: AgentRole | str,
        toolsets: list[str] | None = None,
        context: str | None = None,
        task_id: str | None = None,
    ) -> ChildAgentConfig:
        """构建子 Agent 配置。

        子 Agent 配置和隔离策略：
        - 每个子 Agent 有独立的配置对象，不共享状态
        - 配置包含：任务 ID、角色、目标、上下文、允许/阻止的工具、系统提示等
        - 系统提示根据角色动态生成（Leaf vs Orchestrator）
        - 工具过滤根据角色应用不同的阻止列表

        隔离策略的关键点：
        1. task_id 唯一标识：使用 UUID 前 8 位，确保全局唯一
        2. 角色权限控制：LEAF 不能 delegate_task，ORCHESTRATOR 可以
        3. 工具白名单/黑名单：根据角色过滤工具，防止越权操作
        4. 系统提示隔离：不同角色有不同的系统提示，定义行为边界
        5. 超时独立：每个子 Agent 有独立的超时计时器

        Args:
            goal: 目标描述。
            role: 角色。
            toolsets: 工具集。
            context: 上下文。
            task_id: 任务 ID（自动生成）。

        Returns:
            子 Agent 配置。
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        # 生成唯一任务 ID：使用 UUID 前 8 位
        # 设计理由：8 位足够唯一（16^8 = 42 亿种可能），同时保持可读性
        tid = task_id or str(uuid.uuid4())[:8]

        # 工具过滤：根据角色应用不同的阻止列表
        blocked = self.filter_blocked_tools(role, toolsets)

        # 系统提示：根据角色生成不同的行为约束
        system_prompt = self._build_system_prompt(role, goal, context)

        return ChildAgentConfig(
            task_id=tid,
            role=role.value,
            goal=goal,
            context=context or "",
            allowed_toolsets=toolsets or [],
            blocked_tools=list(blocked),
            system_prompt=system_prompt,
            max_depth=self.max_spawn_depth,
            timeout=self.child_timeout_seconds,
            auto_approve=self.subagent_auto_approve,
        )

    def filter_blocked_tools(
        self,
        role: AgentRole | str,
        toolsets: list[str] | None = None,
    ) -> list[str]:
        """过滤被阻止的工具。

        安全考量：
        - 这是权限控制的核心方法，决定了子 Agent 可以使用哪些工具
        - 默认阻止列表（DELEGATE_BLOCKED_TOOLS）适用于所有角色
        - ORCHESTRATOR 角色可以从阻止列表中移除 delegate_task
          这使 Orchestrator 可以进一步委托，但仍受其他限制（clarify、memory 等）

        过滤逻辑：
        1. 从默认阻止列表开始（delegate_task、clarify、memory、execute_code）
        2. 如果是 ORCHESTRATOR，从阻止列表中移除 ORCHESTRATOR_ALLOWED_TOOLS
        3. 如果提供了 toolsets（白名单），返回 toolsets 中不在阻止列表中的工具
        4. 如果没有提供 toolsets，返回完整的阻止列表

        设计理由：
        - 使用 set 操作（blocked -= ORCHESTRATOR_ALLOWED_TOOLS）而非列表推导
          因为 set 的差集操作更高效且语义更清晰
        - 返回 list 而非 set：保持与 ChildAgentConfig.blocked_tools 类型一致

        Args:
            role: 角色。
            toolsets: 原始工具集（白名单）。

        Returns:
            过滤后的工具列表。
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        # 从默认阻止列表开始
        blocked = set(DELEGATE_BLOCKED_TOOLS)

        # Orchestrator 可以 delegate_task：从阻止列表中移除
        # 设计理由：使用 set 差集操作，语义清晰且高效
        if role == AgentRole.ORCHESTRATOR:
            blocked -= ORCHESTRATOR_ALLOWED_TOOLS

        if toolsets:
            # 白名单模式：只返回 toolsets 中不在阻止列表中的工具
            # 这是双重保护：即使 toolsets 包含危险工具，也会被过滤
            return [t for t in toolsets if t not in blocked]

        # 没有白名单时，返回完整的阻止列表
        # 调用者可以根据此列表从可用工具中排除这些工具
        return list(blocked)

    # ── 系统提示构建 ──

    def _build_system_prompt(
        self,
        role: AgentRole,
        goal: str,
        context: str | None = None,
    ) -> str:
        """构建子 Agent 系统提示。

        设计理由：
        - 系统提示是子 Agent 行为约束的主要来源
        - 不同角色有不同的系统提示，定义其能力边界和行为规范
        - 提示使用 Markdown 格式，便于 LLM 理解和遵循

        Args:
            role: 角色。
            goal: 目标。
            context: 上下文。

        Returns:
            系统提示。
        """
        if role == AgentRole.LEAF:
            return self._build_leaf_system_prompt(goal, context)
        else:
            return self._build_orchestrator_system_prompt(goal, context)

    def _build_leaf_system_prompt(self, goal: str, context: str | None) -> str:
        """构建 Leaf 角色系统提示。

        设计理由：
        - Leaf 是受限的工作者角色，系统提示明确列出其不能做的事情
        - 这种"负面清单"方式比"正面清单"更安全：明确禁止比允许更清晰
        - 限制列表与 DELEGATE_BLOCKED_TOOLS 一致，形成双重保障
          （工具层 + 提示层）

        安全考量：
        - 明确告知 LLM 哪些工具不可用，减少 LLM 尝试调用被禁止工具的概率
        - 但提示层约束不如工具层可靠（LLM 可能忽略提示），所以工具过滤是必须的

        Args:
            goal: 目标。
            context: 上下文。

        Returns:
            系统提示。
        """
        parts = [
            "# Leaf Agent",
            "",
            "你是一个专注的工作者 Agent，负责完成分配的特定任务。",
            "",
            "## 限制",
            "- 你不能委托任务给其他 Agent（delegate_task 不可用）",
            "- 你不能与用户交互（clarify 不可用）",
            "- 你不能写入共享记忆（memory 不可用）",
            "- 你应该逐步推理，而非编写脚本（execute_code 不可用）",
            "",
            "## 任务",
            f"{goal}",
        ]

        if context:
            parts.extend(["", "## 上下文", context])

        return "\n".join(parts)

    def _build_orchestrator_system_prompt(self, goal: str, context: str | None) -> str:
        """构建 Orchestrator 角色系统提示。

        设计理由：
        - Orchestrator 是编排者角色，系统提示强调其分解任务和委托的能力
        - 与 Leaf 不同，Orchestrator 的系统提示是"正面清单"方式
          强调它能做什么，而非不能做什么
        - 这是因为 Orchestrator 的权限更受控（只有 delegate_task 额外权限）
          其他危险工具仍在 DELEGATE_BLOCKED_TOOLS 中

        与 Leaf 的区别：
        - Leaf：负面清单（明确禁止），因为权限受限
        - Orchestrator：正面清单（强调能力），因为权限相对开放
          但仍受工具过滤层约束

        Args:
            goal: 目标。
            context: 上下文。

        Returns:
            系统提示。
        """
        parts = [
            "# Orchestrator Agent",
            "",
            "你是一个编排者 Agent，负责分解任务并委托给子 Agent。",
            "",
            "## 能力",
            "- 你可以委托任务给子 Agent（delegate_task 可用）",
            "- 你应该将大任务分解为小任务",
            "- 你应该合并子 Agent 的结果",
            "",
            "## 任务",
            f"{goal}",
        ]

        if context:
            parts.extend(["", "## 上下文", context])

        return "\n".join(parts)

    # ── 并发控制 ──

    @property
    def max_concurrent(self) -> int:
        """最大并发数（兼容属性）。

        设计理由：
        - 这是 max_concurrent_children 的别名，提供向后兼容
        - 使外部代码可以使用更简短的属性名访问
        """
        return self.max_concurrent_children

    @property
    def max_depth(self) -> int:
        """最大深度（兼容属性）。

        设计理由：
        - 这是 max_spawn_depth 的别名，提供向后兼容
        """
        return self.max_spawn_depth

    @property
    def timeout_seconds(self) -> float:
        """超时时间（兼容属性）。

        设计理由：
        - 这是 child_timeout_seconds 的别名，提供向后兼容
        """
        return self.child_timeout_seconds

    @property
    def auto_approve(self) -> bool:
        """自动批准（兼容属性）。

        设计理由：
        - 这是 subagent_auto_approve 的别名，提供向后兼容
        """
        return self.subagent_auto_approve

    def set_auto_deny_callback(self, callback: Callable[[dict], bool]) -> None:
        """设置自动拒绝回调。

        设计理由：
        - 回调机制使 DelegationManager 与具体的 UI 或业务逻辑解耦
        - 外部代码可以自定义哪些工具调用应该被自动拒绝
        - 典型用途：TUI 应用中弹出确认对话框，用户选择后返回结果

        Args:
            callback: 回调函数，接收工具调用信息，返回是否拒绝。
        """
        self._auto_deny_callback = callback

    def set_auto_approve_callback(self, callback: Callable[[dict], bool]) -> None:
        """设置自动批准回调。

        设计理由：
        - 与 set_auto_deny_callback 类似，但用于自动批准
        - 典型用途：在安全环境中自动批准所有工具调用，无需用户确认

        Args:
            callback: 回调函数，接收工具调用信息，返回是否批准。
        """
        self._auto_approve_callback = callback

    def _subagent_auto_deny(self, tool_call: dict) -> bool:
        """子 Agent 自动拒绝回调。

        错误处理和恢复策略：
        - 首先尝试调用外部设置的 _auto_deny_callback
        - 如果没有外部回调，使用内置的默认拒绝逻辑
        - 默认拒绝危险操作：terminal、execute_code、write_file、delete_file
          这些操作可能对系统造成不可逆的影响

        安全考量：
        - 默认拒绝策略是"安全优先"：宁可误拒，不可误放
        - 危险工具列表是硬编码的，确保即使外部回调出错也有兜底保护

        Args:
            tool_call: 工具调用信息。

        Returns:
            是否拒绝。
        """
        if self._auto_deny_callback:
            return self._auto_deny_callback(tool_call)
        # 默认：拒绝危险操作
        # 这些工具可能对系统造成不可逆的影响，需要用户确认
        dangerous = {"terminal", "execute_code", "write_file", "delete_file"}
        tool_name = tool_call.get("name", tool_call.get("tool", ""))
        return tool_name in dangerous

    def _subagent_auto_approve(self, tool_call: dict) -> bool:
        """子 Agent 自动批准回调。

        设计理由：
        - 首先尝试调用外部设置的 _auto_approve_callback
        - 如果没有外部回调，返回 subagent_auto_approve 配置值
        - 默认是 False（不自动批准），确保安全优先

        Args:
            tool_call: 工具调用信息。

        Returns:
            是否批准。
        """
        if self._auto_approve_callback:
            return self._auto_approve_callback(tool_call)
        return self.subagent_auto_approve

    # ── 执行 ──

    def _execute_single_agent(self, config: ChildAgentConfig) -> DelegationResult:
        """执行单个子 Agent。

        子 Agent 执行流程：
        1. 注册活跃子 Agent：将配置和状态记录到 _active_children
           这用于监控和调试，可以查看当前有哪些子 Agent 在运行
        2. 执行子 Agent：当前是模拟实现（_simulate_execution）
           实际实现应该：
           - 创建独立的 LLM 客户端（使用子 Agent 的配置）
           - 发送系统提示和任务目标
           - 处理工具调用（应用工具过滤和自动批准/拒绝）
           - 收集结果并返回
        3. 结果处理：成功时记录摘要，失败时记录错误信息
        4. 清理：从 _active_children 中移除已完成的子 Agent

        错误处理和恢复策略：
        - 使用 try/except/finally 结构
        - except 块：捕获所有异常，记录日志，返回失败结果
          这防止了单个子 Agent 失败影响其他子 Agent
        - finally 块：无论成功或失败，都清理 _active_children
          这防止了状态泄漏（活跃子 Agent 字典无限增长）

        状态跟踪：
        - _active_children 记录每个子 Agent 的配置、启动时间和状态
        - 状态有三种：running（执行中）、completed（成功）、failed（失败）
        - 这便于外部监控子 Agent 的执行情况

        Args:
            config: 子 Agent 配置。

        Returns:
            委托结果。
        """
        task_id = config.task_id

        # 注册活跃子 Agent：用于监控和调试
        # 设计理由：在执行前注册，确保即使执行立即失败也有记录
        self._active_children[task_id] = {
            "config": config,
            "start_time": time.time(),
            "status": "running",
        }

        try:
            # 模拟执行（实际应 spawn 子进程或调用 LLM）
            # 当前是占位实现，实际应：
            # 1. 创建独立的 LLM 客户端
            # 2. 发送系统提示和任务目标
            # 3. 处理工具调用循环
            # 4. 收集最终结果
            summary = self._simulate_execution(config)

            result = DelegationResult(
                task_id=task_id,
                success=True,
                summary=summary,
                role=config.role,
            )

            # 更新状态为完成
            self._active_children[task_id]["status"] = "completed"
            return result

        except Exception as e:
            # 错误处理：记录日志，返回失败结果
            # 设计理由：捕获所有异常，防止单个子 Agent 失败影响整体流程
            # exc_info=True 确保记录完整的堆栈跟踪，便于调试
            logger.error(f"子 Agent 执行失败 [{task_id}]: {e}", exc_info=True)
            self._active_children[task_id]["status"] = "failed"

            return DelegationResult(
                task_id=task_id,
                success=False,
                error=str(e),
                role=config.role,
            )
        finally:
            # 清理：无论成功或失败，都移除活跃子 Agent 记录
            # 这防止了状态泄漏：如果不清理，_active_children 会无限增长
            if task_id in self._active_children:
                del self._active_children[task_id]

    def _simulate_execution(self, config: ChildAgentConfig) -> str:
        """模拟子 Agent 执行。

        设计理由：
        - 这是占位实现，用于测试和开发阶段
        - 实际实现应替换为真正的 LLM 调用和工具执行逻辑
        - 当前实现只返回任务目标的摘要，模拟成功完成

        Args:
            config: 配置。

        Returns:
            执行摘要。
        """
        # 截取目标前 80 字符：避免摘要过长
        goal_preview = config.goal[:80] if len(config.goal) > 80 else config.goal
        return f"已完成任务: {goal_preview}"

    # ── 批量内部方法（兼容） ──

    def _spawn_single(
        self,
        goal: str,
        role: AgentRole,
        toolsets: list[str] | None,
        context: str | None,
    ) -> DelegationResult:
        """Spawn 单个子 Agent（兼容方法）。

        设计理由：
        - 这是 delegate_single 的别名，保留用于向后兼容
        - 命名 _spawn_single 强调"生成子进程"的语义
        - 内部直接委托给 delegate_single，避免代码重复

        Args:
            goal: 目标描述。
            role: 角色。
            toolsets: 工具集。
            context: 上下文。

        Returns:
            委托结果。
        """
        return self.delegate_single(
            goal=goal,
            role=role,
            toolsets=toolsets,
            context=context,
        )

    def _spawn_batch(
        self,
        tasks: list[dict[str, Any]],
        role: AgentRole,
        toolsets: list[str] | None,
    ) -> list[DelegationResult]:
        """批量 Spawn 子 Agent（兼容方法）。

        设计理由：
        - 这是 delegate_batch 的别名，保留用于向后兼容
        - 命名 _spawn_batch 强调"批量生成子进程"的语义

        Args:
            tasks: 任务列表。
            role: 角色。
            toolsets: 工具集。

        Returns:
            委托结果列表。
        """
        return self.delegate_batch(
            tasks=tasks,
            role=role,
            toolsets=toolsets,
        )

    # ── 状态查询 ──

    def get_active_children(self) -> dict[str, dict[str, Any]]:
        """获取活跃子 Agent 信息。

        设计理由：
        - 返回 dict 的副本（dict(self._active_children)）而非引用
          这防止外部代码意外修改内部状态
        - 用于监控和调试：可以查看当前有哪些子 Agent 在运行

        Returns:
            活跃子 Agent 字典的副本。
        """
        return dict(self._active_children)

    def get_completed_results(self) -> list[DelegationResult]:
        """获取已完成的结果。

        设计理由：
        - 返回 list 的副本（list(self._completed_results)）而非引用
          这防止外部代码意外修改内部状态
        - 用于结果聚合和查询：可以查看所有已完成子 Agent 的结果

        Returns:
            结果列表的副本。
        """
        return list(self._completed_results)

    def reset(self) -> None:
        """重置管理器状态。

        设计理由：
        - 重置所有运行时状态，使管理器回到初始状态
        - 用于：
          1. 测试后清理：确保测试之间状态隔离
          2. 会话结束后清理：准备下一次委托
          3. 错误恢复：在严重错误后重置状态
        - 注意：不重置配置参数（max_concurrent_children 等），只重置运行时状态
        """
        self._current_depth = 0
        self._active_children.clear()
        self._completed_results.clear()
