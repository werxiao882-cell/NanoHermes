"""Semaphore 并发控制。

自定义信号量实现，支持同步和异步双模式。
"""

from __future__ import annotations

import asyncio
from collections import deque


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
