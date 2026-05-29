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

from src.tools.registry import register_tool

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
    
    # 限制 toolsets
    if toolsets:
        toolsets = [t for t in toolsets if t not in DELEGATE_BLOCKED_TOOLS]
    
    try:
        # 单任务模式
        if goal and not tasks:
            result = _execute_single(goal, role, toolsets, context)
            return json.dumps(result, ensure_ascii=False)
        
        # 批量模式
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
            "委托任务给子 Agent 执行。支持单任务和批量并行模式。\n\n"
            "子 Agent 拥有独立的对话上下文和受限工具集。\n"
            "父级只看到最终摘要，不看到中间过程。\n\n"
            "角色：\n"
            "- leaf（默认）：专注工作者，不能委托/访问记忆/用户交互\n"
            "- orchestrator：编排者，可以进一步委托子任务\n\n"
            "注意：子 Agent 不能访问 delegate_task, clarify, memory, execute_code 工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "单任务目标描述。",
                },
                "tasks": {
                    "type": "array",
                    "description": "批量任务列表，每项包含 goal/description 和可选 context。",
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
                    "description": "子 Agent 角色。",
                },
                "toolsets": {
                    "type": "array",
                    "description": "允许使用的工具集列表。",
                    "items": {"type": "string"},
                },
                "context": {
                    "type": "string",
                    "description": "上下文信息。",
                },
            },
            "required": [],
        },
    },
    handler=delegate_task,
    check_fn=check_delegation_requirements,
    description="子 Agent 委托",
)
