"""DelegationManager - 多 Agent 委托管理器。

核心职责：
- 将复杂任务分解为多个子 Agent 并行或串行执行
- 通过角色系统（LEAF/ORCHESTRATOR）控制子 Agent 的权限边界
- 通过信号量和深度限制防止资源耗尽和无限递归
- 隔离子 Agent 上下文，避免污染主 Agent 的会话状态
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from typing import Any, Callable

from src.delegation.types import (
    AgentRole,
    ChildAgentConfig,
    DelegationResult,
    DELEGATE_BLOCKED_TOOLS,
    ORCHESTRATOR_ALLOWED_TOOLS,
)
from src.delegation.semaphore import Semaphore

logger = logging.getLogger(__name__)


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
        model_caller: Callable | None = None,
        tool_dispatch: Callable | None = None,
        tool_schemas: list[dict[str, Any]] | None = None,
        parent_event_bus: Any | None = None,
        parent_session_id: str = "",
    ):
        """初始化委托管理器。

        Args:
            max_concurrent_children: 最大并发子 Agent 数。
            max_spawn_depth: 最大委托深度。
            child_timeout_seconds: 子 Agent 超时时间（秒）。
            subagent_auto_approve: 是否自动批准危险命令。
            model_caller: LLM 调用函数，注入给子 Agent 使用。
            tool_dispatch: 工具分发函数，注入给子 Agent 使用。
            tool_schemas: 完整工具 schema 列表，用于过滤子 Agent 可用工具。
            parent_event_bus: 父 Agent 的事件总线，用于转发子 Agent 事件到 TUI。
            parent_session_id: 父 Agent 的会话 ID，用于子 Agent JSONL 命名关联。
        """
        self.max_concurrent_children = max(1, max_concurrent_children)
        self.max_spawn_depth = max(0, max_spawn_depth)
        self.child_timeout_seconds = max(1.0, child_timeout_seconds)
        self.subagent_auto_approve = subagent_auto_approve

        self._model_caller = model_caller
        self._tool_dispatch = tool_dispatch
        self._tool_schemas = tool_schemas or []

        # 内部创建 EventBus，用于内部事件管理
        from src.conversation.events import EventBus
        self._event_bus = EventBus()

        # 父 Agent 上下文：事件总线和会话 ID
        # 设计理由：子 Agent 的事件需要转发到父 Agent 的 TUI 显示，
        # 子 Agent 的 JSONL 文件名需要包含父会话 ID 以建立关联
        self._parent_event_bus = parent_event_bus
        self._parent_session_id = parent_session_id

        self._current_depth = 0
        self._semaphore = Semaphore(max_concurrent_children)
        self._active_children: dict[str, dict[str, Any]] = {}
        self._completed_results: list[DelegationResult] = []

        self._auto_deny_callback: Callable[[dict], bool] | None = None
        self._auto_approve_callback: Callable[[dict], bool] | None = None

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """发射委托事件到事件总线。"""
        if not self._event_bus:
            return
        try:
            from src.conversation.events import EventType
            et = getattr(EventType, event_type, None)
            if et:
                self._event_bus.emit(et, data)
        except Exception as e:
            logger.debug(f"委托事件发射失败 [{event_type}]: {e}")

    def _forward_to_parent(self, event_type, data: dict[str, Any]) -> None:
        """转发子 Agent 事件到父 Agent 事件总线。

        设计理由：
        子 Agent 运行在独立线程和独立 EventBus 中，TUI 只订阅了父 Agent 的 EventBus。
        通过转发，TUI 可以实时显示子 Agent 的工具执行和消息状态。
        data 中注入 child_task_id 字段，TUI 据此添加标识符区分主/子 Agent。
        """
        if not self._parent_event_bus:
            return
        try:
            self._parent_event_bus.emit(event_type, data)
        except Exception as e:
            logger.debug(f"事件转发到父总线失败: {e}")

    def _forward_to_parent_delegation(self, event_type_str: str, data: dict[str, Any]) -> None:
        """转发委托生命周期事件到父 Agent 事件总线。"""
        if not self._parent_event_bus:
            return
        try:
            from src.conversation.events import EventType
            et = getattr(EventType, event_type_str, None)
            if et:
                self._parent_event_bus.emit(et, data)
        except Exception as e:
            logger.debug(f"委托事件转发到父总线失败 [{event_type_str}]: {e}")

    def set_parent_context(
        self,
        parent_event_bus: Any | None = None,
        parent_session_id: str = "",
    ) -> None:
        """更新父 Agent 上下文（会话创建后调用）。

        设计理由：
        TUI 初始化时 session_id 为 "new_session"，实际 ID 在 run() 中创建。
        此方法允许在会话创建后延迟注入正确的上下文。
        """
        if parent_event_bus is not None:
            self._parent_event_bus = parent_event_bus
        if parent_session_id:
            self._parent_session_id = parent_session_id

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

        Args:
            goal: 单任务目标描述。
            tasks: 批量任务列表。
            role: 子 Agent 角色。
            toolsets: 允许使用的工具集。
            context: 上下文信息。

        Returns:
            委托结果列表。
        """
        if self._current_depth >= self.max_spawn_depth:
            return [DelegationResult(
                task_id="depth_limit",
                success=False,
                error=f"达到最大委托深度 ({self.max_spawn_depth})，无法生成子 Agent。",
            )]

        if isinstance(role, str):
            role = AgentRole(role.lower())

        if goal and not tasks:
            return [self.delegate_single(
                goal=goal,
                role=role,
                toolsets=toolsets,
                context=context,
            )]

        if tasks:
            return self.delegate_batch(
                tasks=tasks,
                role=role,
                toolsets=toolsets,
            )

        return []

    def delegate_single(
        self,
        goal: str,
        role: AgentRole | str = AgentRole.LEAF,
        toolsets: list[str] | None = None,
        context: str | None = None,
    ) -> DelegationResult:
        """委托单个任务。

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

        if self._current_depth >= self.max_spawn_depth:
            result = DelegationResult(
                task_id="depth_limit",
                success=False,
                error=f"达到最大委托深度 ({self.max_spawn_depth})",
            )
            self._emit_event("DELEGATION_FAIL", {
                "task_id": result.task_id,
                "error": result.error,
                "duration": 0,
            })
            return result

        config = self.build_child_agent_config(
            goal=goal,
            role=role,
            toolsets=toolsets,
            context=context,
        )

        with self._semaphore:
            delegation_start_data = {
                "task_id": config.task_id,
                "goal": config.goal,
                "role": config.role,
                "depth": self._current_depth,
            }
            self._emit_event("DELEGATION_START", delegation_start_data)
            self._forward_to_parent_delegation("DELEGATION_START", delegation_start_data)

            result = self._execute_single_agent(config)

            if result.success:
                delegation_complete_data = {
                    "task_id": result.task_id,
                    "summary": result.summary,
                    "duration": result.duration,
                    "tool_calls": result.tool_calls,
                }
                self._emit_event("DELEGATION_COMPLETE", delegation_complete_data)
                self._forward_to_parent_delegation("DELEGATION_COMPLETE", delegation_complete_data)
            else:
                delegation_fail_data = {
                    "task_id": result.task_id,
                    "error": result.error,
                    "duration": result.duration,
                }
                self._emit_event("DELEGATION_FAIL", delegation_fail_data)
                self._forward_to_parent_delegation("DELEGATION_FAIL", delegation_fail_data)

            self._completed_results.append(result)
            return result

    def delegate_batch(
        self,
        tasks: list[dict[str, Any]],
        role: AgentRole | str = AgentRole.LEAF,
        toolsets: list[str] | None = None,
    ) -> list[DelegationResult]:
        """批量并行委托任务。

        Args:
            tasks: 任务列表。
            role: 角色。
            toolsets: 工具集。

        Returns:
            委托结果列表。
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        limited_tasks = tasks[:self.max_concurrent_children]

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return self._delegate_batch_sync(limited_tasks, role, toolsets)
            else:
                return asyncio.run(self._delegate_batch_async(limited_tasks, role, toolsets))
        except RuntimeError:
            return self._delegate_batch_sync(limited_tasks, role, toolsets)

    def _delegate_batch_sync(
        self,
        tasks: list[dict[str, Any]],
        role: AgentRole,
        toolsets: list[str] | None,
    ) -> list[DelegationResult]:
        """同步批量执行。"""
        results = []
        for i, task in enumerate(tasks):
            goal = task.get("goal", task.get("description", ""))
            task_context = task.get("context", "")
            task_toolsets = task.get("toolsets", toolsets)

            result = self.delegate_single(
                goal=goal,
                role=role,
                toolsets=task_toolsets,
                context=task_context,
            )
            result.task_id = f"batch_{i}_{result.task_id}"
            results.append(result)

        return results

    async def _delegate_batch_async(
        self,
        tasks: list[dict[str, Any]],
        role: AgentRole,
        toolsets: list[str] | None,
    ) -> list[DelegationResult]:
        """异步批量并行执行。"""
        async def execute_task(i: int, task: dict[str, Any]) -> DelegationResult:
            goal = task.get("goal", task.get("description", ""))
            task_context = task.get("context", "")
            task_toolsets = task.get("toolsets", toolsets)

            await self._semaphore.acquire()
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.delegate_single(
                        goal=goal,
                        role=role,
                        toolsets=task_toolsets,
                        context=task_context,
                    )
                )
                result.task_id = f"batch_{i}_{result.task_id}"
                return result
            finally:
                await self._semaphore.release()

        coros = [execute_task(i, task) for i, task in enumerate(tasks)]
        results = await asyncio.gather(*coros, return_exceptions=True)

        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(DelegationResult(
                    task_id=f"batch_{i}_error",
                    success=False,
                    error=str(result),
                    role=role.value,
                ))
            else:
                final_results.append(result)

        return final_results

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

        tid = task_id or str(uuid.uuid4())[:8]
        blocked = self.filter_blocked_tools(role, toolsets)
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
            parent_session_id=self._parent_session_id,
        )

    def filter_blocked_tools(
        self,
        role: AgentRole | str,
        toolsets: list[str] | None = None,
    ) -> list[str]:
        """过滤被阻止的工具。

        Args:
            role: 角色。
            toolsets: 原始工具集（白名单）。

        Returns:
            过滤后的工具列表。
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        blocked = set(DELEGATE_BLOCKED_TOOLS)

        if role == AgentRole.ORCHESTRATOR:
            blocked -= ORCHESTRATOR_ALLOWED_TOOLS

        if toolsets:
            return [t for t in toolsets if t not in blocked]

        return list(blocked)

    # ── 系统提示构建 ──

    def _build_system_prompt(
        self,
        role: AgentRole,
        goal: str,
        context: str | None = None,
    ) -> str:
        """构建子 Agent 系统提示。"""
        if role == AgentRole.LEAF:
            return self._build_leaf_system_prompt(goal, context)
        else:
            return self._build_orchestrator_system_prompt(goal, context)

    def _build_leaf_system_prompt(self, goal: str, context: str | None) -> str:
        """构建 Leaf 角色系统提示。"""
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
        """构建 Orchestrator 角色系统提示。"""
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
        """最大并发数（兼容属性）。"""
        return self.max_concurrent_children

    @property
    def max_depth(self) -> int:
        """最大深度（兼容属性）。"""
        return self.max_spawn_depth

    @property
    def timeout_seconds(self) -> float:
        """超时时间（兼容属性）。"""
        return self.child_timeout_seconds

    @property
    def auto_approve(self) -> bool:
        """自动批准（兼容属性）。"""
        return self.subagent_auto_approve

    def set_auto_deny_callback(self, callback: Callable[[dict], bool]) -> None:
        """设置自动拒绝回调。"""
        self._auto_deny_callback = callback

    def set_auto_approve_callback(self, callback: Callable[[dict], bool]) -> None:
        """设置自动批准回调。"""
        self._auto_approve_callback = callback

    def _subagent_auto_deny(self, tool_call: dict) -> bool:
        """子 Agent 自动拒绝回调。"""
        if self._auto_deny_callback:
            return self._auto_deny_callback(tool_call)
        dangerous = {"terminal", "execute_code", "write_file", "delete_file"}
        tool_name = tool_call.get("name", tool_call.get("tool", ""))
        return tool_name in dangerous

    def _subagent_auto_approve(self, tool_call: dict) -> bool:
        """子 Agent 自动批准回调。"""
        if self._auto_approve_callback:
            return self._auto_approve_callback(tool_call)
        return self.subagent_auto_approve

    # ── 执行 ──

    def _execute_single_agent(self, config: ChildAgentConfig) -> DelegationResult:
        """在独立线程中 fork 子 Agent 执行。

        子 Agent 拥有独立的 ConversationLoop、消息列表和过滤后的工具集。
        在后台线程中运行，通过 threading.Event 等待结果。

        JSONL 录制：
        - 子 Agent 消息写入 ~/.nanohermes/agents/{parent_session_id}__{task_id}.jsonl
        - 格式与主 Agent 一致（session_start + user/assistant/tool 消息）
        - 通过订阅子 ConversationLoop 的 MESSAGE_APPEND 事件实现

        TUI 事件转发：
        - 子 Agent 的 TOOL_START/TOOL_END 事件转发到父 Agent 的 EventBus
        - 注入 child_task_id 字段，TUI 据此显示子 Agent 标识符
        """
        task_id = config.task_id

        self._active_children[task_id] = {
            "config": config,
            "start_time": time.time(),
            "status": "running",
            "goal": config.goal,
            "role": config.role,
        }

        start_time = time.time()
        result_container: list[DelegationResult] = []
        done_event = threading.Event()

        def _child_agent_thread():
            """子 Agent 线程：运行独立的 ConversationLoop。"""
            try:
                if not self._model_caller:
                    summary = self._simulate_execution(config)
                    result_container.append(DelegationResult(
                        task_id=task_id,
                        success=True,
                        summary=summary,
                        role=config.role,
                        duration=time.time() - start_time,
                    ))
                    return

                # 构建子 Agent 独立的消息列表（深拷贝确保完全独立）
                child_messages = [
                    {"role": "system", "content": config.system_prompt},
                    {"role": "user", "content": config.goal},
                ]
                
                # 调试日志：记录初始消息
                logger.debug(f"子 Agent [{task_id}] 初始消息: {[m['role'] for m in child_messages]}")

                # 过滤工具 schema：排除被阻止的工具
                child_tools = self._get_filtered_tool_schemas(config.blocked_tools)

                # 创建独立的 ConversationLoop
                from src.conversation.loop import ConversationLoop
                child_loop = ConversationLoop(
                    model_call=self._model_caller,
                    tool_dispatch=self._tool_dispatch,
                    max_iterations=30,
                )

                # 子 Agent JSONL 录制：订阅 MESSAGE_APPEND 事件写入独立文件
                # 文件路径: ~/.nanohermes/agents/{parent_session_id}__{task_id}.jsonl
                child_jsonl_store = self._create_child_jsonl_store()
                child_session_id = self._build_child_session_id(config)
                self._record_child_session_start(
                    child_jsonl_store, child_session_id, config,
                    tools_schema=child_tools,
                )
                self._subscribe_child_jsonl_handler(
                    child_loop, child_jsonl_store, child_session_id,
                )

                # 子 Agent 事件转发到父 Agent 的 TUI
                self._subscribe_child_event_forwarding(child_loop, task_id)

                # 深度计数
                self._current_depth += 1

                try:
                    loop_result = child_loop.run(
                        messages=child_messages,
                        tools=child_tools if child_tools else None,
                    )
                finally:
                    self._current_depth -= 1

                summary = loop_result.get("final_response", "")
                iterations = loop_result.get("iterations", 0)

                result_container.append(DelegationResult(
                    task_id=task_id,
                    success=True,
                    summary=summary,
                    role=config.role,
                    duration=time.time() - start_time,
                    tool_calls=iterations,
                ))

            except Exception as e:
                logger.error(f"子 Agent 执行失败 [{task_id}]: {e}", exc_info=True)
                result_container.append(DelegationResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                    role=config.role,
                    duration=time.time() - start_time,
                ))
            finally:
                done_event.set()

        # 在独立线程中 fork 子 Agent
        thread = threading.Thread(
            target=_child_agent_thread,
            name=f"child-{task_id}",
            daemon=True,
        )
        thread.start()

        # 等待子 Agent 完成（带超时保护）
        finished = done_event.wait(timeout=config.timeout)

        if not finished:
            # 超时：中断子 Agent
            logger.warning(f"子 Agent 超时 [{task_id}]: {config.timeout}s")
            self._active_children[task_id]["status"] = "timeout"
            result = DelegationResult(
                task_id=task_id,
                success=False,
                error=f"子 Agent 执行超时 ({config.timeout}s)",
                role=config.role,
                duration=config.timeout,
            )
        else:
            result = result_container[0]
            self._active_children[task_id]["status"] = "completed" if result.success else "failed"

        # 清理
        if task_id in self._active_children:
            del self._active_children[task_id]

        return result

    def _get_filtered_tool_schemas(
        self,
        blocked_tools: list[str],
    ) -> list[dict[str, Any]]:
        """获取过滤后的工具 schema 列表。

        过滤掉被阻止的工具，并清理非标准字段（如 defer_loading），
        确保返回的 schema 符合内部工具定义格式（flat format）。
        build_caller() 会将其包装为 OpenAI API 格式。
        """
        if not self._tool_schemas:
            return []

        blocked_set = set(blocked_tools)
        result = []
        for schema in self._tool_schemas:
            name = schema.get("name", "")
            if not name or name in blocked_set:
                continue
            # 清理非标准字段，保留 flat format（name, description, parameters）
            clean_schema = {k: v for k, v in schema.items() if k != "defer_loading"}
            result.append(clean_schema)
        return result

    # ── 子 Agent JSONL 录制 ──

    def _create_child_jsonl_store(self):
        """创建子 Agent 专用的 JSONL 存储。

        存储路径: ~/.nanohermes/agents/
        与主 Agent 的 ~/.nanohermes/sessions/ 分离，避免混淆。
        """
        from pathlib import Path
        from src.session.jsonl_store import JsonlSessionStore
        agents_dir = Path.home() / ".nanohermes" / "agents"
        return JsonlSessionStore(base_dir=agents_dir)

    def _build_child_session_id(self, config: ChildAgentConfig) -> str:
        """构建子 Agent 的会话 ID，与父 Agent 建立命名关联。

        格式: {parent_session_id}__{task_id}
        双下划线分隔，确保父 ID 中的单下划线不产生歧义。
        """
        parent_id = config.parent_session_id or self._parent_session_id or "unknown"
        return f"{parent_id}__{config.task_id}"

    def _record_child_session_start(
        self,
        jsonl_store,
        session_id: str,
        config: ChildAgentConfig,
        tools_schema: list[dict[str, Any]] | None = None,
    ) -> None:
        """写入子 Agent 的 session_start 记录和初始 user 消息。"""
        try:
            jsonl_store.start_session(
                session_id=session_id,
                model="child-agent",
                tools_schema=tools_schema,
                system_prompt=config.system_prompt if config.system_prompt else None,
            )
            jsonl_store.append_message(
                session_id=session_id,
                role="user",
                content=config.goal,
                metadata={
                    "parent_session_id": config.parent_session_id,
                    "task_id": config.task_id,
                    "role": config.role,
                },
            )
        except Exception as e:
            logger.debug(f"子 Agent session_start 写入失败 [{session_id}]: {e}")

    def _subscribe_child_jsonl_handler(
        self,
        child_loop,
        jsonl_store,
        session_id: str,
    ) -> None:
        """订阅子 Agent 的 MESSAGE_APPEND 事件，持久化到 JSONL。

        与主 Agent 的 ConversationEventHandler._on_message_append 逻辑一致，
        支持 assistant（含 tool_calls）、tool、assistant（纯文本）三种消息类型。
        """
        from src.conversation.events import EventType

        def _on_child_message_append(data: dict[str, Any]) -> None:
            message = data.get("message", {})
            role = message.get("role")
            content = message.get("content") or ""
            reasoning = data.get("reasoning")
            usage = data.get("usage")

            try:
                if role == "assistant" and message.get("tool_calls"):
                    jsonl_store.append_message(
                        session_id, role="assistant",
                        content=content,
                        tool_calls=message["tool_calls"],
                        reasoning=reasoning, usage=usage,
                    )
                elif role == "tool":
                    jsonl_store.append_message(
                        session_id, role="tool",
                        content=content,
                        tool_call_id=message.get("tool_call_id", ""),
                        tool_name=message.get("tool_name", ""),
                    )
                elif role == "assistant":
                    jsonl_store.append_message(
                        session_id, role="assistant", content=content,
                        reasoning=reasoning, usage=usage,
                    )
            except Exception as e:
                logger.debug(f"子 Agent JSONL 写入失败 [{session_id}]: {e}")

        child_loop.events.on(EventType.MESSAGE_APPEND, _on_child_message_append)

    def _subscribe_child_event_forwarding(
        self,
        child_loop,
        task_id: str,
    ) -> None:
        """订阅子 Agent 事件并转发到父 Agent 的 TUI。

        转发 TOOL_START 和 TOOL_END 事件，注入 child_task_id 字段。
        TUI 的 ConversationEventHandler 据此显示子 Agent 标识符。
        """
        if not self._parent_event_bus:
            return

        from src.conversation.events import EventType

        def _forward_tool_start(data: dict[str, Any]) -> None:
            forwarded = {**data, "child_task_id": task_id}
            self._forward_to_parent(EventType.TOOL_START, forwarded)

        def _forward_tool_end(data: dict[str, Any]) -> None:
            forwarded = {**data, "child_task_id": task_id}
            self._forward_to_parent(EventType.TOOL_END, forwarded)

        child_loop.events.on(EventType.TOOL_START, _forward_tool_start)
        child_loop.events.on(EventType.TOOL_END, _forward_tool_end)

    def _simulate_execution(self, config: ChildAgentConfig) -> str:
        """模拟子 Agent 执行（降级实现）。"""
        goal_preview = config.goal[:80] if len(config.goal) > 80 else config.goal
        return f"已完成任务: {goal_preview}"

    def _spawn_single(
        self,
        goal: str,
        role: AgentRole,
        toolsets: list[str] | None,
        context: str | None,
    ) -> DelegationResult:
        """Spawn 单个子 Agent（兼容方法）。"""
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
        """批量 Spawn 子 Agent（兼容方法）。"""
        return self.delegate_batch(
            tasks=tasks,
            role=role,
            toolsets=toolsets,
        )

    # ── 状态查询 ──

    def get_active_children(self) -> dict[str, dict[str, Any]]:
        """获取活跃子 Agent 信息。"""
        return dict(self._active_children)

    def get_completed_results(self) -> list[DelegationResult]:
        """获取已完成的结果。"""
        return list(self._completed_results)

    def reset(self) -> None:
        """重置管理器状态。"""
        self._current_depth = 0
        self._active_children.clear()
        self._completed_results.clear()
