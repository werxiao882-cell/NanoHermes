"""Skills 工具：技能管理。

调用 SkillManager 执行实际的技能管理操作。
"""

from __future__ import annotations

import json
from typing import Any

from src.tools.registry import register_tool
from src.skills.manager import SkillManager

# 全局 SkillManager 实例
_skill_manager = SkillManager()


def skill_manage(
    action: str = "",
    name: str = "",
    content: str = "",
    category: str = "",
    old_string: str = "",
    new_string: str = "",
    file_path: str = "",
    file_content: str = "",
    replace_all: bool = False,
    task_id: str = None,
) -> str:
    """管理技能（创建、编辑、补丁、删除、写入文件、删除文件）。

    Actions:
        create: 创建新技能（需要 name, content）
        edit: 替换技能的 SKILL.md（需要 name, content）
        patch: 查找替换（需要 name, old_string, new_string）
        delete: 删除技能（需要 name）
        write_file: 写入支持文件（需要 name, file_path, file_content）
        remove_file: 删除支持文件（需要 name, file_path）
    """
    action = action.lower().strip()

    if action == "create":
        result = _skill_manager.create_skill(name, content, category if category else None)
    elif action == "edit":
        result = _skill_manager.edit_skill(name, content)
    elif action == "patch":
        result = _skill_manager.patch_skill(
            name, old_string, new_string,
            file_path if file_path else None,
            replace_all,
        )
    elif action == "delete":
        result = _skill_manager.delete_skill(name)
    elif action == "write_file":
        result = _skill_manager.write_file(name, file_path, file_content)
    elif action == "remove_file":
        result = _skill_manager.remove_file(name, file_path)
    else:
        result = {
            "success": False,
            "error": f"Unknown action '{action}'. Valid actions: create, edit, patch, delete, write_file, remove_file."
        }

    return json.dumps(result, ensure_ascii=False)


def skill_view(name: str = "", task_id: str = None) -> str:
    """查看技能详情。"""
    details = _skill_manager.get_skill_details(name)
    if details is None:
        return json.dumps({
            "success": False,
            "error": f"Skill '{name}' not found."
        }, ensure_ascii=False)

    return json.dumps({
        "success": True,
        "skill": details,
    }, ensure_ascii=False)


def skills_list(query: str = "", task_id: str = None, **kwargs) -> str:
    """列出可用技能。"""
    skills = _skill_manager.list_skills_with_query(query)
    return json.dumps({
        "success": True,
        "skills": skills,
        "count": len(skills),
    }, ensure_ascii=False)


# ============================================================================
# 注册工具
# ============================================================================
register_tool(
    name="skill_manage",
    toolset="skills",
    schema={
        "name": "skill_manage",
        "description": "管理技能（创建、编辑、补丁、删除、写入文件、删除文件）。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型：create, edit, patch, delete, write_file, remove_file",
                    "enum": ["create", "edit", "patch", "delete", "write_file", "remove_file"],
                },
                "name": {"type": "string", "description": "技能名称。"},
                "content": {"type": "string", "description": "SKILL.md 内容（create/edit 时使用）。"},
                "category": {"type": "string", "description": "可选分类目录名（create 时使用）。"},
                "old_string": {"type": "string", "description": "要查找的字符串（patch 时使用）。"},
                "new_string": {"type": "string", "description": "替换后的字符串（patch 时使用）。"},
                "file_path": {"type": "string", "description": "支持文件路径（patch/write_file/remove_file 时使用）。"},
                "file_content": {"type": "string", "description": "文件内容（write_file 时使用）。"},
                "replace_all": {"type": "boolean", "description": "是否替换所有匹配项（patch 时使用）。"},
            },
            "required": ["action"],
        },
    },
    handler=skill_manage,
    description="技能管理",
)

register_tool(
    name="skill_view",
    toolset="skills",
    schema={
        "name": "skill_view",
        "description": "查看技能详情，包括元数据和支持文件列表。",
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

register_tool(
    name="skills_list",
    toolset="skills",
    schema={
        "name": "skills_list",
        "description": "列出可用技能，支持关键词过滤。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词（可选）。"},
            },
            "required": [],
        },
    },
    handler=skills_list,
    description="列出技能",
)
