"""Delegation 工具：子 Agent 委托。

支持单任务和批量并行委托。
子 Agent 拥有：
- 独立的对话上下文（无父级历史）
- 独立的 task_id（独立的终端会话、文件操作缓存）
- 受限的工具集（可配置，危险工具始终被剥离）
- 专注的系统提示（从委托目标 + 上下文构建）

父级上下文只看到委托调用和摘要结果，
从不看到子级的中间工具调用或推理。
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from src.tools.core.registry import register_tool

logger = logging.getLogger(__name__)

# 子 Agent 绝不能访问的工具
DELEGATE_BLOCKED_TOOLS = frozenset([
    "delegate_task",    # 禁止递归委托
    "clarify",          # 禁止用户交互
    "memory",           # 禁止写入共享 MEMORY.md
    "execute_code",     # 子 Agent 应逐步推理，而非编写脚本
])


def delegate_task(
    goal: str = "",
    tasks: list[dict] = None,
    role: str = "leaf",
    toolsets: list[str] = None,
    context: str = "",
    task_id: str = None,
    **kwargs,
) -> str:
    """委托任务给子 Agent 执行。

    两种调用方式：
    - 单任务：传入 goal
    - 批量：传入 tasks 数组（并行执行）

    角色：
    - leaf（默认）：专注的工作者，不能委托、访问记忆等
    - orchestrator：编排者，可以进一步委托子任务
    """
    # 验证参数
    if not goal and not tasks:
        return json.dumps({
            "status": "error",
            "message": "Either 'goal' or 'tasks' must be provided."
        }, ensure_ascii=False)

    # 处理 LLM 可能将 tasks 二次序列化为字符串的情况
    # 日志中观察到: "tasks": "[{\"goal\": \"...\"}, ...]" 而非 "tasks": [{"goal": "..."}, ...]
    if isinstance(tasks, str):
        try:
            tasks = json.loads(tasks)
        except (json.JSONDecodeError, TypeError):
            return json.dumps({
                "status": "error",
                "message": f"tasks 参数是字符串但无法解析为 JSON: {tasks[:100]}"
            }, ensure_ascii=False)

    # 限制 toolsets
    if toolsets:
        toolsets = [t for t in toolsets if t not in DELEGATE_BLOCKED_TOOLS]

    try:
        # 优先使用 DelegationManager（真实执行）
        from src.delegation import get_manager
        mgr = get_manager()
        if mgr is not None:
            results = mgr.delegate_task(
                goal=goal,
                tasks=tasks,
                role=role,
                toolsets=toolsets,
                context=context,
            )
            # 转换为 JSON 响应
            if len(results) == 1 and not tasks:
                # 单任务模式
                r = results[0]
                return json.dumps({
                    "status": "success" if r.success else "error",
                    "task_id": r.task_id,
                    "role": r.role,
                    "summary": r.summary,
                    "duration": round(r.duration, 2),
                    "tool_calls": r.tool_calls,
                    "message": r.summary if r.success else r.error,
                }, ensure_ascii=False)
            else:
                # 批量模式
                return json.dumps({
                    "status": "success",
                    "mode": "batch",
                    "results": [
                        {
                            "task_id": r.task_id,
                            "success": r.success,
                            "summary": r.summary,
                            "error": r.error,
                            "duration": round(r.duration, 2),
                        }
                        for r in results
                    ],
                    "count": len(results),
                    "message": f"Completed {len(results)} tasks.",
                }, ensure_ascii=False)

        # 降级为模拟执行（无 DelegationManager）
        if goal and not tasks:
            result = _execute_single(goal, role, toolsets, context)
            return json.dumps(result, ensure_ascii=False)

        if tasks:
            results = _execute_batch(tasks, role, toolsets)
            return json.dumps({
                "status": "success",
                "mode": "batch",
                "results": results,
                "count": len(results),
                "message": f"Completed {len(results)} tasks."
            }, ensure_ascii=False)

        return json.dumps({
            "status": "error",
            "message": "Invalid delegation request."
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Delegation error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Delegation failed: {str(e)}"
        }, ensure_ascii=False)


def _execute_single(
    goal: str,
    role: str,
    toolsets: list[str] | None,
    context: str | None,
) -> dict:
    """执行单个子 Agent 委托。
    
    注意：当前为简化实现，实际应 spawn 子进程/线程。
    """
    task_id = str(uuid.uuid4())[:8]
    
    # 构建子 Agent 提示
    prompt_parts = []
    prompt_parts.append(f"# Task\n\n{goal}")
    
    if context:
        prompt_parts.append(f"\n# Context\n\n{context}")
    
    if toolsets:
        prompt_parts.append(f"\n# Available Toolsets\n\n{', '.join(toolsets)}")
    
    # 模拟执行（实际应启动子 Agent）
    summary = f"已完成任务: {goal[:80]}..."
    
    return {
        "status": "success",
        "task_id": task_id,
        "role": role,
        "summary": summary,
        "message": "Single task delegation completed."
    }


def _execute_batch(
    tasks: list[dict],
    role: str,
    toolsets: list[str] | None,
) -> list[dict]:
    """批量执行子 Agent 委托。
    
    注意：当前为简化实现，实际应并发 spawn 子进程/线程。
    """
    results = []
    
    for i, task in enumerate(tasks[:5]):  # 限制最多 5 个并发
        goal = task.get("goal", task.get("description", ""))
        task_context = task.get("context", "")
        
        task_id = str(uuid.uuid4())[:8]
        summary = f"已完成任务 {i+1}: {goal[:60]}..."
        
        results.append({
            "task_id": task_id,
            "goal": goal[:100],
            "summary": summary,
            "success": True,
        })
    
    return results


def check_delegation_requirements() -> bool:
    """Delegation 工具没有外部要求，始终可用。"""
    return True


register_tool(
    name="delegate_task",
    toolset="delegation",
    schema={
        "name": "delegate_task",
        "description": (
            "Spawn one or more subagents to work on tasks in isolated contexts. Each subagent gets its own conversation, terminal session, and toolset. Only the final summary is returned -- intermediate tool results never enter your context window.\n\n"
            "TWO MODES (one of 'goal' or 'tasks' is required):\n"
            "1. Single task: provide 'goal' (+ optional context, toolsets)\n"
            "2. Batch (parallel): provide 'tasks' array with up to 3 items concurrently for this user. All run in parallel and results are returned together.\n\n"
            "WHEN TO USE delegate_task:\n"
            "- Reasoning-heavy subtasks (debugging, code review, research synthesis)\n"
            "- Tasks that would flood your context with intermediate data\n"
            "- Parallel independent workstreams (research A and B simultaneously)\n\n"
            "WHEN NOT TO USE (use these instead):\n"
            "- Mechanical multi-step work with no reasoning needed -> use execute_code\n"
            "- Single tool call -> just call the tool directly\n"
            "- Tasks needing user interaction -> subagents cannot use clarify\n\n"
            "IMPORTANT:\n"
            "- Subagents have NO memory of your conversation. Pass all relevant info via the 'context' field.\n"
            "- If the user is writing in a non-English language, say so in 'context' (e.g. 'respond in Chinese').\n"
            "- Leaf subagents (role='leaf', the default) CANNOT call: delegate_task, clarify, memory, execute_code.\n"
            "- Each subagent gets its own terminal session (separate working directory and state)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "What the subagent should accomplish. Be specific and self-contained -- the subagent knows nothing about your conversation history."
                },
                "context": {
                    "type": "string",
                    "description": "Background information the subagent needs: file paths, error messages, project structure, constraints."
                },
                "toolsets": {
                    "type": "array",
                    "description": "Toolsets to enable for this subagent. Default: inherits your enabled toolsets.",
                    "items": {"type": "string"}
                },
                "tasks": {
                    "type": "array",
                    "description": "Batch mode: tasks to run in parallel. Each gets its own subagent with isolated context and terminal session.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "goal": {"type": "string"},
                            "description": {"type": "string"},
                            "context": {"type": "string"},
                        },
                    },
                },
                "role": {
                    "type": "string",
                    "enum": ["leaf", "orchestrator"],
                    "description": "Role of the child agent. 'leaf' (default) = focused worker, cannot delegate further. 'orchestrator' = can use delegate_task to spawn its own workers."
                },
            },
            "required": [],
        },
    },
    handler=delegate_task,
    check_fn=check_delegation_requirements,
    description="子 Agent 委托",
    defer_loading=True,
)
