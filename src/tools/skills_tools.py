"""Skills 工具：技能管理。

参考 Hermes Agent 的 skill_manager_tool.py 实现，支持：
- create: 创建新技能（SKILL.md + 目录结构）
- edit: 替换技能的 SKILL.md 内容（完全重写）
- patch: 在 SKILL.md 或支持文件中进行查找替换
- delete: 删除用户技能
- write_file: 添加/覆盖支持文件（reference, template, script, asset）
- remove_file: 删除支持文件

技能目录结构：
    ~/.nanohermes/skills/
    ├── my-skill/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── templates/
    │   ├── scripts/
    │   └── assets/
    └── category-name/
        └── another-skill/
            └── SKILL.md
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from src.tools.registry import register_tool
from src.skills.loader import SkillLoader
from src.skills.manager import SkillManager

# ============================================================================
# 常量
# ============================================================================
SKILLS_DIR = Path.home() / ".nanohermes" / "skills"
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_SKILL_CONTENT_CHARS = 100_000  # ~36k tokens
MAX_SKILL_FILE_BYTES = 1_048_576   # 1 MiB per supporting file

# 技能名称允许的字符（文件系统安全，URL 友好）
VALID_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')

# write_file/remove_file 允许的子目录
ALLOWED_SUBDIRS = {"references", "templates", "scripts", "assets"}


# ============================================================================
# 验证辅助函数
# ============================================================================
def _validate_name(name: str) -> str | None:
    """验证技能名称。返回错误消息或 None。"""
    if not name:
        return "Skill name is required."
    if len(name) > MAX_NAME_LENGTH:
        return f"Skill name exceeds {MAX_NAME_LENGTH} characters."
    if not VALID_NAME_RE.match(name):
        return (
            f"Invalid skill name '{name}'. Use lowercase letters, numbers, "
            f"hyphens, dots, and underscores. Must start with a letter or digit."
        )
    return None


def _validate_category(category: str | None) -> str | None:
    """验证可选的分类名称。"""
    if category is None:
        return None
    if not isinstance(category, str):
        return "Category must be a string."

    category = category.strip()
    if not category:
        return None
    if "/" in category or "\\" in category:
        return (
            f"Invalid category '{category}'. Categories must be a single directory name."
        )
    if len(category) > MAX_NAME_LENGTH:
        return f"Category exceeds {MAX_NAME_LENGTH} characters."
    if not VALID_NAME_RE.match(category):
        return (
            f"Invalid category '{category}'. Use lowercase letters, numbers, "
            "hyphens, dots, and underscores."
        )
    return None


def _validate_frontmatter(content: str) -> str | None:
    """验证 SKILL.md 内容是否有正确的前置元数据。"""
    if not content.strip():
        return "Content cannot be empty."

    if not content.startswith("---"):
        return "SKILL.md must start with YAML frontmatter (---)."

    end_match = re.search(r'\n---\s*\n', content[3:])
    if not end_match:
        return "SKILL.md frontmatter is not closed. Ensure you have a closing '---' line."

    yaml_content = content[3:end_match.start() + 3]

    # 简单 YAML 解析
    frontmatter = {}
    for line in yaml_content.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            frontmatter[key] = value

    if "name" not in frontmatter:
        return "Frontmatter must include 'name' field."
    if "description" not in frontmatter:
        return "Frontmatter must include 'description' field."
    if len(str(frontmatter.get("description", ""))) > MAX_DESCRIPTION_LENGTH:
        return f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters."

    body = content[end_match.end() + 3:].strip()
    if not body:
        return "SKILL.md must have content after the frontmatter."

    return None


def _validate_content_size(content: str, label: str = "SKILL.md") -> str | None:
    """检查内容是否超出字符限制。"""
    if len(content) > MAX_SKILL_CONTENT_CHARS:
        return (
            f"{label} content is {len(content):,} characters "
            f"(limit: {MAX_SKILL_CONTENT_CHARS:,})."
        )
    return None


def _resolve_skill_dir(name: str, category: str | None = None) -> Path:
    """构建新技能的目录路径。"""
    if category:
        return SKILLS_DIR / category / name
    return SKILLS_DIR / name


def _find_skill(name: str) -> dict[str, Any] | None:
    """按名称查找技能。"""
    if not SKILLS_DIR.exists():
        return None

    for skill_md in SKILLS_DIR.rglob("SKILL.md"):
        if skill_md.parent.name == name:
            return {"path": skill_md.parent}
    return None


def _atomic_write_text(file_path: Path, content: str, encoding: str = "utf-8") -> None:
    """原子写入文本内容到文件。"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        dir=str(file_path.parent),
        prefix=f".{file_path.name}.tmp.",
        suffix="",
    )
    try:
        import os
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
        os.replace(temp_path, file_path)
    except Exception:
        import os
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def _validate_file_path(file_path: str) -> str | None:
    """验证 write_file/remove_file 的文件路径。"""
    if not file_path:
        return "file_path is required."

    normalized = Path(file_path)

    # 防止路径遍历
    if ".." in normalized.parts:
        return "Path traversal ('..') is not allowed."

    # 必须在允许的子目录下
    if not normalized.parts or normalized.parts[0] not in ALLOWED_SUBDIRS:
        allowed = ", ".join(sorted(ALLOWED_SUBDIRS))
        return f"File must be under one of: {allowed}. Got: '{file_path}'"

    # 必须有文件名
    if len(normalized.parts) < 2:
        return f"Provide a file path, not just a directory."

    return None


def _resolve_skill_target(skill_dir: Path, file_path: str) -> tuple[Path | None, str | None]:
    """解析支持文件路径并确保在技能目录内。"""
    target = skill_dir / file_path
    try:
        target.resolve().relative_to(skill_dir.resolve())
    except ValueError:
        return None, "File path escapes skill directory."
    return target, None


# ============================================================================
# 核心操作
# ============================================================================
def _create_skill(name: str, content: str, category: str | None = None) -> dict[str, Any]:
    """创建新技能。"""
    # 验证名称
    err = _validate_name(name)
    if err:
        return {"success": False, "error": err}

    err = _validate_category(category)
    if err:
        return {"success": False, "error": err}

    # 验证内容
    err = _validate_frontmatter(content)
    if err:
        return {"success": False, "error": err}

    err = _validate_content_size(content)
    if err:
        return {"success": False, "error": err}

    # 检查名称冲突
    existing = _find_skill(name)
    if existing:
        return {
            "success": False,
            "error": f"A skill named '{name}' already exists at {existing['path']}."
        }

    # 创建技能目录
    skill_dir = _resolve_skill_dir(name, category)
    skill_dir.mkdir(parents=True, exist_ok=True)

    # 原子写入 SKILL.md
    skill_md = skill_dir / "SKILL.md"
    _atomic_write_text(skill_md, content)

    result = {
        "success": True,
        "message": f"Skill '{name}' created.",
        "path": str(skill_dir.relative_to(SKILLS_DIR)),
        "skill_md": str(skill_md),
    }
    if category:
        result["category"] = category
    result["hint"] = (
        f"To add reference files, templates, or scripts, use "
        f"skill_manage(action='write_file', name='{name}', file_path='references/example.md', file_content='...')"
    )
    return result


def _edit_skill(name: str, content: str) -> dict[str, Any]:
    """替换技能的 SKILL.md 内容。"""
    err = _validate_frontmatter(content)
    if err:
        return {"success": False, "error": err}

    err = _validate_content_size(content)
    if err:
        return {"success": False, "error": err}

    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found. Use skills_list() to see available skills."}

    skill_md = existing["path"] / "SKILL.md"
    _atomic_write_text(skill_md, content)

    return {
        "success": True,
        "message": f"Skill '{name}' updated.",
        "path": str(existing["path"]),
    }


def _patch_skill(
    name: str,
    old_string: str,
    new_string: str,
    file_path: str | None = None,
    replace_all: bool = False,
) -> dict[str, Any]:
    """在技能文件中进行查找替换。"""
    if not old_string:
        return {"success": False, "error": "old_string is required for 'patch'."}
    if new_string is None:
        return {"success": False, "error": "new_string is required for 'patch'. Use empty string to delete."}

    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found."}

    skill_dir = existing["path"]

    if file_path:
        err = _validate_file_path(file_path)
        if err:
            return {"success": False, "error": err}
        target, err = _resolve_skill_target(skill_dir, file_path)
        if err:
            return {"success": False, "error": err}
    else:
        target = skill_dir / "SKILL.md"

    if not target.exists():
        return {"success": False, "error": f"File not found: {target.relative_to(skill_dir)}"}

    content = target.read_text(encoding="utf-8")

    # 查找替换
    count = content.count(old_string)
    if count == 0:
        preview = content[:500] + ("..." if len(content) > 500 else "")
        return {
            "success": False,
            "error": f"old_string not found in {'SKILL.md' if not file_path else file_path}.",
            "file_preview": preview,
        }
    if count > 1 and not replace_all:
        return {
            "success": False,
            "error": f"old_string found {count} times. Use replace_all=True to replace all, or be more specific.",
        }

    new_content = content.replace(old_string, new_string, 1 if not replace_all else -1)

    # 检查大小限制
    target_label = "SKILL.md" if not file_path else file_path
    err = _validate_content_size(new_content, label=target_label)
    if err:
        return {"success": False, "error": err}

    # 如果修改 SKILL.md，验证前置元数据
    if not file_path:
        err = _validate_frontmatter(new_content)
        if err:
            return {"success": False, "error": f"Patch would break SKILL.md structure: {err}"}

    _atomic_write_text(target, new_content)

    return {
        "success": True,
        "message": f"Patched {'SKILL.md' if not file_path else file_path} in skill '{name}' ({count} replacement{'s' if count > 1 else ''}).",
    }


def _delete_skill(name: str) -> dict[str, Any]:
    """删除技能。"""
    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found."}

    skill_dir = existing["path"]
    shutil.rmtree(skill_dir)

    # 清理空分类目录
    parent = skill_dir.parent
    if parent != SKILLS_DIR and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()

    return {
        "success": True,
        "message": f"Skill '{name}' deleted.",
    }


def _write_file(name: str, file_path: str, file_content: str) -> dict[str, Any]:
    """添加或覆盖技能中的支持文件。"""
    err = _validate_file_path(file_path)
    if err:
        return {"success": False, "error": err}

    if file_content is None:
        return {"success": False, "error": "file_content is required."}

    # 检查大小限制
    content_bytes = len(file_content.encode("utf-8"))
    if content_bytes > MAX_SKILL_FILE_BYTES:
        return {
            "success": False,
            "error": f"File content is {content_bytes:,} bytes (limit: {MAX_SKILL_FILE_BYTES:,} bytes / 1 MiB)."
        }

    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found. Create it first with action='create'."}

    target, err = _resolve_skill_target(existing["path"], file_path)
    if err:
        return {"success": False, "error": err}

    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(target, file_content)

    return {
        "success": True,
        "message": f"File '{file_path}' written to skill '{name}'.",
        "path": str(target),
    }


def _remove_file(name: str, file_path: str) -> dict[str, Any]:
    """删除技能中的支持文件。"""
    err = _validate_file_path(file_path)
    if err:
        return {"success": False, "error": err}

    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found."}

    skill_dir = existing["path"]
    target, err = _resolve_skill_target(skill_dir, file_path)
    if err:
        return {"success": False, "error": err}

    if not target.exists():
        available = []
        for subdir in ALLOWED_SUBDIRS:
            d = skill_dir / subdir
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file():
                        available.append(str(f.relative_to(skill_dir)))
        return {
            "success": False,
            "error": f"File '{file_path}' not found in skill '{name}'.",
            "available_files": available if available else None,
        }

    target.unlink()

    # 清理空子目录
    parent = target.parent
    if parent != skill_dir and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()

    return {
        "success": True,
        "message": f"File '{file_path}' removed from skill '{name}'.",
    }


# ============================================================================
# 工具处理器
# ============================================================================
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
        result = _create_skill(name, content, category if category else None)
    elif action == "edit":
        result = _edit_skill(name, content)
    elif action == "patch":
        result = _patch_skill(
            name, old_string, new_string,
            file_path if file_path else None,
            replace_all,
        )
    elif action == "delete":
        result = _delete_skill(name)
    elif action == "write_file":
        result = _write_file(name, file_path, file_content)
    elif action == "remove_file":
        result = _remove_file(name, file_path)
    else:
        result = {
            "success": False,
            "error": f"Unknown action '{action}'. Valid actions: create, edit, patch, delete, write_file, remove_file."
        }

    return json.dumps(result, ensure_ascii=False)


def skill_view(name: str = "", task_id: str = None) -> str:
    """查看技能详情。"""
    existing = _find_skill(name)
    if not existing:
        return json.dumps({
            "success": False,
            "error": f"Skill '{name}' not found."
        }, ensure_ascii=False)

    skill_dir = existing["path"]
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        return json.dumps({
            "success": False,
            "error": f"SKILL.md not found for skill '{name}'."
        }, ensure_ascii=False)

    try:
        loader = SkillLoader()
        skill = loader.load(skill_md)

        # 列出支持文件
        files = []
        for subdir in ALLOWED_SUBDIRS:
            d = skill_dir / subdir
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file():
                        files.append(str(f.relative_to(skill_dir)))

        return json.dumps({
            "success": True,
            "skill": {
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
                "author": skill.author,
                "license": skill.license,
                "path": str(skill_dir.relative_to(SKILLS_DIR)),
                "files": files,
            },
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to load skill: {e}"
        }, ensure_ascii=False)


def skills_list(query: str = "", task_id: str = None) -> str:
    """列出可用技能。"""
    if not SKILLS_DIR.exists():
        return json.dumps({
            "success": True,
            "skills": [],
            "message": "No skills directory found."
        }, ensure_ascii=False)

    skills = []
    for skill_md in SKILLS_DIR.rglob("SKILL.md"):
        try:
            loader = SkillLoader()
            skill = loader.load(skill_md)

            # 过滤查询
            if query:
                query_lower = query.lower()
                if query_lower not in skill.name.lower() and query_lower not in skill.description.lower():
                    continue

            skills.append({
                "name": skill.name,
                "description": skill.description,
                "path": str(skill_md.parent.relative_to(SKILLS_DIR)),
            })
        except Exception:
            continue

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
