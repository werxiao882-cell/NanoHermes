"""默认工具集：clarify, execute_code, cronjob, delegate_task, memory, session_search, skills, process.

这些工具是 Agent 默认可用的核心工具。
"""

from __future__ import annotations

import json
from typing import Any

from src.tools.registry import register_tool


# ============================================================================
# clarify - 向用户提问
# ============================================================================
def clarify(question: str = "", task_id: str = None) -> str:
    """向用户提问，等待用户回答。

    Args:
        question: 要问的问题。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含提问状态。
    """
    return json.dumps({
        "status": "clarification_requested",
        "question": question,
        "message": "Waiting for user response..."
    }, ensure_ascii=False)


# ============================================================================
# execute_code - 运行 Python 脚本
# ============================================================================
def execute_code(code: str = "", language: str = "python", task_id: str = None) -> str:
    """运行 Python 脚本，可以调用 Hermes 工具。

    Args:
        code: 要执行的 Python 代码。
        language: 编程语言（默认 python）。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含执行结果。
    """
    # 简化实现：不实际执行代码，返回提示
    return json.dumps({
        "status": "code_execution_requested",
        "language": language,
        "code_length": len(code),
        "message": "Code execution is not available in this version."
    }, ensure_ascii=False)


# ============================================================================
# cronjob - 管理定时任务
# ============================================================================
def cronjob(action: str = "", job_id: str = "", schedule: str = "", prompt: str = "", task_id: str = None) -> str:
    """管理定时任务。

    Args:
        action: 操作类型（list, add, edit, pause, resume, run, remove）。
        job_id: 任务 ID。
        schedule: 调度表达式（如 "30m", "every 2h", "0 9 * * *"）。
        prompt: 任务提示。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含操作结果。
    """
    if action == "list":
        return json.dumps({
            "status": "success",
            "jobs": [],
            "message": "No cron jobs configured."
        }, ensure_ascii=False)

    return json.dumps({
        "status": "cronjob_requested",
        "action": action,
        "message": "Cron job management is not available in this version."
    }, ensure_ascii=False)


# ============================================================================
# delegate_task - 子 Agent 委托
# ============================================================================
def delegate_task(goal: str = "", tasks: list[dict] = None, role: str = "leaf",
                  toolsets: list[str] = None, context: str = "", task_id: str = None) -> str:
    """生成子 Agent 执行任务。

    Args:
        goal: 单任务目标。
        tasks: 批量任务列表。
        role: 角色（leaf/orchestrator）。
        toolsets: 允许的工具集。
        context: 上下文信息。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含委托结果。
    """
    return json.dumps({
        "status": "delegation_requested",
        "goal": goal,
        "role": role,
        "message": "Delegation is not available in this version."
    }, ensure_ascii=False)


# ============================================================================
# memory - 持久记忆
# ============================================================================
def memory(action: str = "", content: str = "", key: str = "", task_id: str = None) -> str:
    """保存持久记忆，跨会话保留。

    Args:
        action: 操作类型（add, replace, remove, view）。
        content: 记忆内容。
        key: 记忆键。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含操作结果。
    """
    return json.dumps({
        "status": "memory_requested",
        "action": action,
        "message": "Memory management is not available in this version."
    }, ensure_ascii=False)


# ============================================================================
# session_search - 历史会话搜索
# ============================================================================
def session_search(query: str = "", session_id: str = "", limit: int = 10, task_id: str = None) -> str:
    """搜索历史会话。

    Args:
        query: 搜索关键词。
        session_id: 指定会话 ID。
        limit: 最大结果数。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含搜索结果。
    """
    return json.dumps({
        "status": "search_requested",
        "query": query,
        "message": "Session search is not available in this version."
    }, ensure_ascii=False)


# ============================================================================
# skills 工具集
# ============================================================================
def skill_manage(action: str = "", name: str = "", content: str = "", task_id: str = None) -> str:
    """管理技能（创建、更新、删除）。

    Args:
        action: 操作类型（create, update, delete, list）。
        name: 技能名称。
        content: 技能内容。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含操作结果。
    """
    return json.dumps({
        "status": "skill_manage_requested",
        "action": action,
        "message": "Skill management is not available in this version."
    }, ensure_ascii=False)


def skill_view(name: str = "", task_id: str = None) -> str:
    """查看技能详情。

    Args:
        name: 技能名称。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含技能内容。
    """
    return json.dumps({
        "status": "skill_view_requested",
        "name": name,
        "message": "Skill viewing is not available in this version."
    }, ensure_ascii=False)


def skills_list(query: str = "", task_id: str = None) -> str:
    """列出可用技能。

    Args:
        query: 搜索关键词。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含技能列表。
    """
    return json.dumps({
        "status": "success",
        "skills": [],
        "message": "No skills loaded."
    }, ensure_ascii=False)


# ============================================================================
# process - 后台进程管理
# ============================================================================
def process(action: str = "", process_id: str = "", task_id: str = None) -> str:
    """管理后台进程。

    Args:
        action: 操作类型（list, stop, kill, output）。
        process_id: 进程 ID。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含操作结果。
    """
    return json.dumps({
        "status": "process_requested",
        "action": action,
        "message": "Process management is not available in this version."
    }, ensure_ascii=False)


# ============================================================================
# patch - 查找替换编辑
# ============================================================================
def patch(path: str = "", old_str: str = "", new_str: str = "", task_id: str = None) -> str:
    """文件查找替换编辑。

    Args:
        path: 文件路径。
        old_str: 要查找的字符串。
        new_str: 替换后的字符串。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含操作结果。
    """
    try:
        from pathlib import Path
        file_path = Path(path)
        if not file_path.exists():
            return json.dumps({"error": f"File not found: {path}"}, ensure_ascii=False)

        content = file_path.read_text(encoding="utf-8")
        if old_str not in content:
            return json.dumps({"error": f"String not found: {old_str[:50]}..."}, ensure_ascii=False)

        new_content = content.replace(old_str, new_str, 1)
        file_path.write_text(new_content, encoding="utf-8")

        return json.dumps({
            "status": "success",
            "path": path,
            "message": "Patch applied successfully."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Patch failed: {type(e).__name__}: {e}"}, ensure_ascii=False)


# ============================================================================
# 注册默认工具
# ============================================================================
def _register_default_tools() -> None:
    """注册所有默认工具到全局注册表。"""
    # clarify
    register_tool(
        name="clarify",
        toolset="clarify",
        schema={
            "name": "clarify",
            "description": "向用户提问，等待用户回答。",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "要问的问题。"},
                },
                "required": ["question"],
            },
        },
        handler=clarify,
        description="向用户提问",
    )

    # execute_code
    register_tool(
        name="execute_code",
        toolset="code_execution",
        schema={
            "name": "execute_code",
            "description": "运行 Python 脚本，可以调用 Hermes 工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要执行的 Python 代码。"},
                    "language": {"type": "string", "description": "编程语言（默认 python）。"},
                },
                "required": ["code"],
            },
        },
        handler=execute_code,
        description="运行 Python 脚本",
    )

    # cronjob
    register_tool(
        name="cronjob",
        toolset="cronjob",
        schema={
            "name": "cronjob",
            "description": "管理定时任务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "操作类型（list, add, edit, pause, resume, run, remove）。"},
                    "job_id": {"type": "string", "description": "任务 ID。"},
                    "schedule": {"type": "string", "description": "调度表达式。"},
                    "prompt": {"type": "string", "description": "任务提示。"},
                },
                "required": ["action"],
            },
        },
        handler=cronjob,
        description="管理定时任务",
    )

    # delegate_task
    register_tool(
        name="delegate_task",
        toolset="delegation",
        schema={
            "name": "delegate_task",
            "description": "生成子 Agent 执行任务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "单任务目标。"},
                    "tasks": {"type": "array", "description": "批量任务列表。"},
                    "role": {"type": "string", "description": "角色（leaf/orchestrator）。"},
                    "toolsets": {"type": "array", "description": "允许的工具集。"},
                    "context": {"type": "string", "description": "上下文信息。"},
                },
                "required": [],
            },
        },
        handler=delegate_task,
        description="子 Agent 委托",
    )

    # memory
    register_tool(
        name="memory",
        toolset="memory",
        schema={
            "name": "memory",
            "description": "保存持久记忆，跨会话保留。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "操作类型（add, replace, remove, view）。"},
                    "content": {"type": "string", "description": "记忆内容。"},
                    "key": {"type": "string", "description": "记忆键。"},
                },
                "required": ["action"],
            },
        },
        handler=memory,
        description="持久记忆",
    )

    # session_search
    register_tool(
        name="session_search",
        toolset="session_search",
        schema={
            "name": "session_search",
            "description": "搜索历史会话。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词。"},
                    "session_id": {"type": "string", "description": "指定会话 ID。"},
                    "limit": {"type": "integer", "description": "最大结果数。"},
                },
                "required": [],
            },
        },
        handler=session_search,
        description="历史会话搜索",
    )

    # skill_manage
    register_tool(
        name="skill_manage",
        toolset="skills",
        schema={
            "name": "skill_manage",
            "description": "管理技能（创建、更新、删除）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "操作类型（create, update, delete, list）。"},
                    "name": {"type": "string", "description": "技能名称。"},
                    "content": {"type": "string", "description": "技能内容。"},
                },
                "required": ["action"],
            },
        },
        handler=skill_manage,
        description="技能管理",
    )

    # skill_view
    register_tool(
        name="skill_view",
        toolset="skills",
        schema={
            "name": "skill_view",
            "description": "查看技能详情。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "技能名称。"},
                },
                "required": ["name"],
            },
        },
        handler=skill_view,
        description="查看技能",
    )

    # skills_list
    register_tool(
        name="skills_list",
        toolset="skills",
        schema={
            "name": "skills_list",
            "description": "列出可用技能。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词。"},
                },
                "required": [],
            },
        },
        handler=skills_list,
        description="列出技能",
    )

    # process
    register_tool(
        name="process",
        toolset="terminal",
        schema={
            "name": "process",
            "description": "管理后台进程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "操作类型（list, stop, kill, output）。"},
                    "process_id": {"type": "string", "description": "进程 ID。"},
                },
                "required": ["action"],
            },
        },
        handler=process,
        description="后台进程管理",
    )

    # patch
    register_tool(
        name="patch",
        toolset="file",
        schema={
            "name": "patch",
            "description": "文件查找替换编辑。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径。"},
                    "old_str": {"type": "string", "description": "要查找的字符串。"},
                    "new_str": {"type": "string", "description": "替换后的字符串。"},
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
        handler=patch,
        description="查找替换编辑",
    )


# 模块导入时自动注册
_register_default_tools()
