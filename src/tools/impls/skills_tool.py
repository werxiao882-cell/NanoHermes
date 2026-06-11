"""Skills 工具：技能管理。

调用 SkillManager 执行实际的技能管理操作。
"""

from __future__ import annotations

import json
from typing import Any

from src.tools.core.registry import register_tool
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
    **kwargs,
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


def skill_view(name: str = "", task_id: str = None, **kwargs) -> str:
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


def skills_list(category: str = "", task_id: str = None, **kwargs) -> str:
    """列出可用技能。"""
    skills = _skill_manager.list_skills_with_query(category)
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
        "description": (
            "Manage skills (create, update, delete). Skills are your procedural memory — reusable approaches for recurring task types. "
            "New skills go to ~/.hermes/skills/; existing skills can be modified wherever they live.\n\n"
            "Actions: create (full SKILL.md + optional category), patch (old_string/new_string — preferred for fixes), "
            "edit (full SKILL.md rewrite — major overhauls only), delete, write_file, remove_file.\n\n"
            "Create when: complex task succeeded (5+ calls), errors overcome, user-corrected approach worked, "
            "non-trivial workflow discovered, or user asks you to remember a procedure.\n"
            "Update when: instructions stale/wrong, OS-specific failures, missing steps or pitfalls found during use. "
            "If you used a skill and hit issues not covered by it, patch it immediately.\n\n"
            "After difficult/iterative tasks, offer to save as a skill. Skip for simple one-offs. "
            "Confirm with user before creating/deleting.\n\n"
            "Good skills: trigger conditions, numbered steps with exact commands, pitfalls section, verification steps. "
            "Use skill_view() to see format examples."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "patch", "edit", "delete", "write_file", "remove_file"],
                    "description": "The action to perform."
                },
                "name": {
                    "type": "string",
                    "description": "Skill name (lowercase, hyphens/underscores, max 64 chars). Must match an existing skill for patch/edit/delete/write_file/remove_file."
                },
                "content": {
                    "type": "string",
                    "description": "Full SKILL.md content (YAML frontmatter + markdown body). Required for 'create' and 'edit'. For 'edit', read the skill first with skill_view() and provide the complete updated text."
                },
                "old_string": {
                    "type": "string",
                    "description": "Text to find in the file (required for 'patch'). Must be unique unless replace_all=true. Include enough surrounding context to ensure uniqueness."
                },
                "new_string": {
                    "type": "string",
                    "description": "Replacement text (required for 'patch'). Can be empty string to delete the matched text."
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "For 'patch': replace all occurrences instead of requiring a unique match (default: false)."
                },
                "category": {
                    "type": "string",
                    "description": "Optional category/domain for organizing the skill (e.g., 'devops', 'data-science', 'mlops'). Creates a subdirectory grouping. Only used with 'create'."
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to a supporting file within the skill directory. For 'write_file'/'remove_file': required, must be under references/, templates/, scripts/, or assets/. For 'patch': optional, defaults to SKILL.md if omitted."
                },
                "file_content": {
                    "type": "string",
                    "description": "Content for the file. Required for 'write_file'."
                },
            },
            "required": ["action", "name"],
        },
    },
    handler=skill_manage,
    description="技能管理",
    defer_loading=True,
)

register_tool(
    name="skill_view",
    toolset="skills",
    schema={
        "name": "skill_view",
        "description": (
            "Skills allow for loading information about specific tasks and workflows, as well as scripts and templates. "
            "Load a skill's full content or access its linked files (references, templates, scripts). "
            "First call returns SKILL.md content plus a 'linked_files' dict showing available references/templates/scripts. "
            "To access those, call again with file_path parameter."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The skill name (use skills_list to see available skills). For plugin-provided skills, use the qualified form 'plugin:skill' (e.g. 'superpowers:writing-plans')."
                },
                "file_path": {
                    "type": "string",
                    "description": "OPTIONAL: Path to a linked file within the skill (e.g., 'references/api.md', 'templates/config.yaml', 'scripts/validate.py'). Omit to get the main SKILL.md content."
                },
            },
            "required": ["name"],
        },
    },
    handler=skill_view,
    description="查看技能",
    defer_loading=True,
)

register_tool(
    name="skills_list",
    toolset="skills",
    schema={
        "name": "skills_list",
        "description": "List available skills (name + description). Use skill_view(name) to load full content.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category filter to narrow results"
                },
            },
            "required": [],
        },
    },
    handler=skills_list,
    description="列出技能",
    defer_loading=True,
)
