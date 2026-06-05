"""SkillManager - 技能编排器。

管理技能加载、启用/禁用、使用追踪、创建、编辑、删除。
将技能描述注入系统提示的 volatile 层，使模型知道可用技能。

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
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.skills.loader import Skill, SkillLoader


# ============================================================================
# 常量
# ============================================================================
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_SKILL_CONTENT_CHARS = 100_000  # ~36k tokens
MAX_SKILL_FILE_BYTES = 1_048_576   # 1 MiB per supporting file

# 技能名称允许的字符（文件系统安全，URL 友好）
VALID_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')

# write_file/remove_file 允许的子目录
ALLOWED_SUBDIRS = {"references", "templates", "scripts", "assets"}


@dataclass
class SkillEntry:
    """技能条目。

    Attributes:
        skill: 技能元数据。
        enabled: 是否启用。
        use_count: 使用次数。
        last_used_at: 最后使用时间戳。
    """
    skill: Skill
    enabled: bool = True
    use_count: int = 0
    last_used_at: float = 0.0


class SkillManager:
    """技能编排器。

    管理技能加载、启用/禁用、使用追踪、创建、编辑、删除。
    将已启用技能的描述注入系统提示 volatile 层。

    Attributes:
        skills_dir: 技能目录路径。
        _skills: 已加载的技能字典（名称 → SkillEntry）。
        _loader: SKILL.md 加载器。
    """

    def __init__(self, skills_dir: str | Path | None = None):
        """初始化技能管理器。

        Args:
            skills_dir: 技能目录路径，None 时使用 ~/.nanohermes/skills/。
        """
        if skills_dir is None:
            skills_dir = Path.home() / ".nanohermes" / "skills"
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, SkillEntry] = {}
        self._loader = SkillLoader()
        self._load_all()

    def _load_all(self) -> None:
        """加载技能目录中的所有 SKILL.md 文件。"""
        if not self.skills_dir.exists():
            return

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                skill = self._loader.load(skill_file)
                self._skills[skill.name] = SkillEntry(skill=skill)
            except Exception as e:
                print(f"[警告] 加载技能失败 {skill_file}: {e}")

    def _reload(self) -> None:
        """重新加载所有技能。"""
        self._skills.clear()
        self._load_all()

    # ========================================================================
    # 公共 API - 技能查询
    # ========================================================================

    def get_skill(self, name: str) -> Skill | None:
        """获取技能。

        Args:
            name: 技能名称。

        Returns:
            技能实例，未找到返回 None。
        """
        entry = self._skills.get(name)
        return entry.skill if entry else None

    def list_skills(self, enabled_only: bool = False) -> list[SkillEntry]:
        """列出所有技能。

        Args:
            enabled_only: 是否只返回已启用的技能。

        Returns:
            技能条目列表。
        """
        entries = list(self._skills.values())
        if enabled_only:
            entries = [e for e in entries if e.enabled]
        return entries

    def list_skills_with_query(self, query: str = "") -> list[dict[str, Any]]:
        """列出可用技能，支持关键词过滤。

        Args:
            query: 搜索关键词。

        Returns:
            技能列表，每个技能包含 name, description, path。
        """
        if not self.skills_dir.exists():
            return []

        skills = []
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                skill = self._loader.load(skill_file)

                # 过滤查询
                if query:
                    query_lower = query.lower()
                    if query_lower not in skill.name.lower() and query_lower not in skill.description.lower():
                        continue

                skills.append({
                    "name": skill.name,
                    "description": skill.description,
                    "path": str(skill_dir.relative_to(self.skills_dir)),
                })
            except Exception:
                continue

        return skills

    def get_skills_by_category(self) -> dict[str, list[str]]:
        """按类别分类技能。

        从技能路径推断类别，返回类别到技能名称列表的映射。

        Returns:
            类别字典，键为类别名，值为该类别下的技能名称列表。
        """
        skill_categories: dict[str, list[str]] = {}
        for entry in self.list_skills():
            path = entry.skill.path
            if "/skills/" in path:
                parts = path.split("/skills/")[1].split("/")
                if len(parts) >= 2:
                    category = parts[0]
                else:
                    category = "other"
            else:
                category = "other"

            if category not in skill_categories:
                skill_categories[category] = []
            skill_categories[category].append(entry.skill.name)

        return skill_categories

    def get_skill_details(self, name: str) -> dict[str, Any] | None:
        """获取技能详情，包括元数据和支持文件列表。

        Args:
            name: 技能名称。

        Returns:
            技能详情字典，未找到返回 None。
        """
        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return None

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None

        try:
            skill = self._loader.load(skill_md)

            # 列出支持文件
            files = []
            for subdir in ALLOWED_SUBDIRS:
                d = skill_dir / subdir
                if d.exists():
                    for f in d.rglob("*"):
                        if f.is_file():
                            files.append(str(f.relative_to(skill_dir)))

            return {
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
                "author": skill.author,
                "license": skill.license,
                "path": str(skill_dir.relative_to(self.skills_dir)),
                "files": files,
            }
        except Exception:
            return None

    def enable_skill(self, name: str) -> bool:
        """启用技能。

        Args:
            name: 技能名称。

        Returns:
            True 表示成功，False 表示技能不存在。
        """
        entry = self._skills.get(name)
        if not entry:
            return False
        entry.enabled = True
        return True

    def disable_skill(self, name: str) -> bool:
        """禁用技能。

        Args:
            name: 技能名称。

        Returns:
            True 表示成功，False 表示技能不存在。
        """
        entry = self._skills.get(name)
        if not entry:
            return False
        entry.enabled = False
        return True

    def record_use(self, name: str) -> None:
        """记录技能使用。

        Args:
            name: 技能名称。
        """
        entry = self._skills.get(name)
        if entry:
            entry.use_count += 1
            entry.last_used_at = time.time()

    def build_skill_prompt(self) -> str:
        """构建技能提示文本，注入到系统提示 volatile 层。

        返回已启用技能的名称和描述列表，使模型知道可用技能。

        Returns:
            技能提示文本。
        """
        enabled = self.list_skills(enabled_only=True)
        if not enabled:
            return ""

        lines = ["## Available Skills", ""]
        for entry in enabled:
            lines.append(f"- **{entry.skill.name}**: {entry.skill.description}")
        lines.append("")
        lines.append("To use a skill, mention its name in your response.")

        return "\n".join(lines)

    # ========================================================================
    # 公共 API - 技能管理
    # ========================================================================

    def create_skill(self, name: str, content: str, category: str | None = None) -> dict[str, Any]:
        """创建新技能。

        Args:
            name: 技能名称。
            content: SKILL.md 内容。
            category: 可选分类目录名。

        Returns:
            操作结果字典。
        """
        # 验证名称
        err = self._validate_name(name)
        if err:
            return {"success": False, "error": err}

        err = self._validate_category(category)
        if err:
            return {"success": False, "error": err}

        # 验证内容
        err = self._validate_frontmatter(content)
        if err:
            return {"success": False, "error": err}

        err = self._validate_content_size(content)
        if err:
            return {"success": False, "error": err}

        # 检查名称冲突
        if self._find_skill_dir(name):
            return {
                "success": False,
                "error": f"A skill named '{name}' already exists."
            }

        # 创建技能目录
        skill_dir = self._resolve_skill_dir(name, category)
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 原子写入 SKILL.md
        skill_md = skill_dir / "SKILL.md"
        self._atomic_write_text(skill_md, content)

        # 重新加载技能列表
        self._reload()

        result = {
            "success": True,
            "message": f"Skill '{name}' created.",
            "path": str(skill_dir.relative_to(self.skills_dir)),
            "skill_md": str(skill_md),
        }
        if category:
            result["category"] = category
        result["hint"] = (
            f"To add reference files, templates, or scripts, use "
            f"skill_manage(action='write_file', name='{name}', file_path='references/example.md', file_content='...')"
        )
        return result

    def edit_skill(self, name: str, content: str) -> dict[str, Any]:
        """替换技能的 SKILL.md 内容。

        Args:
            name: 技能名称。
            content: 新的 SKILL.md 内容。

        Returns:
            操作结果字典。
        """
        err = self._validate_frontmatter(content)
        if err:
            return {"success": False, "error": err}

        err = self._validate_content_size(content)
        if err:
            return {"success": False, "error": err}

        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return {"success": False, "error": f"Skill '{name}' not found."}

        skill_md = skill_dir / "SKILL.md"
        self._atomic_write_text(skill_md, content)

        # 重新加载技能
        self._reload()

        return {
            "success": True,
            "message": f"Skill '{name}' updated.",
            "path": str(skill_dir),
        }

    def patch_skill(
        self,
        name: str,
        old_string: str,
        new_string: str,
        file_path: str | None = None,
        replace_all: bool = False,
    ) -> dict[str, Any]:
        """在技能文件中进行查找替换。

        Args:
            name: 技能名称。
            old_string: 要查找的字符串。
            new_string: 替换后的字符串。
            file_path: 支持文件路径（None 表示 SKILL.md）。
            replace_all: 是否替换所有匹配项。

        Returns:
            操作结果字典。
        """
        if not old_string:
            return {"success": False, "error": "old_string is required for 'patch'."}
        if new_string is None:
            return {"success": False, "error": "new_string is required for 'patch'. Use empty string to delete."}

        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return {"success": False, "error": f"Skill '{name}' not found."}

        if file_path:
            err = self._validate_file_path(file_path)
            if err:
                return {"success": False, "error": err}
            target, err = self._resolve_skill_target(skill_dir, file_path)
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
        err = self._validate_content_size(new_content, label=target_label)
        if err:
            return {"success": False, "error": err}

        # 如果修改 SKILL.md，验证前置元数据
        if not file_path:
            err = self._validate_frontmatter(new_content)
            if err:
                return {"success": False, "error": f"Patch would break SKILL.md structure: {err}"}

        self._atomic_write_text(target, new_content)

        # 如果修改了 SKILL.md，重新加载技能
        if not file_path:
            self._reload()

        return {
            "success": True,
            "message": f"Patched {'SKILL.md' if not file_path else file_path} in skill '{name}' ({count} replacement{'s' if count > 1 else ''}).",
        }

    def delete_skill(self, name: str) -> dict[str, Any]:
        """删除技能。

        Args:
            name: 技能名称。

        Returns:
            操作结果字典。
        """
        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return {"success": False, "error": f"Skill '{name}' not found."}

        shutil.rmtree(skill_dir)

        # 清理空分类目录
        parent = skill_dir.parent
        if parent != self.skills_dir and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

        # 重新加载技能列表
        self._reload()

        return {
            "success": True,
            "message": f"Skill '{name}' deleted.",
        }

    def write_file(self, name: str, file_path: str, file_content: str) -> dict[str, Any]:
        """添加或覆盖技能中的支持文件。

        Args:
            name: 技能名称。
            file_path: 支持文件路径（如 references/example.md）。
            file_content: 文件内容。

        Returns:
            操作结果字典。
        """
        err = self._validate_file_path(file_path)
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

        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return {"success": False, "error": f"Skill '{name}' not found. Create it first with action='create'."}

        target, err = self._resolve_skill_target(skill_dir, file_path)
        if err:
            return {"success": False, "error": err}

        target.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_text(target, file_content)

        return {
            "success": True,
            "message": f"File '{file_path}' written to skill '{name}'.",
            "path": str(target),
        }

    def remove_file(self, name: str, file_path: str) -> dict[str, Any]:
        """删除技能中的支持文件。

        Args:
            name: 技能名称。
            file_path: 支持文件路径。

        Returns:
            操作结果字典。
        """
        err = self._validate_file_path(file_path)
        if err:
            return {"success": False, "error": err}

        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return {"success": False, "error": f"Skill '{name}' not found."}

        target, err = self._resolve_skill_target(skill_dir, file_path)
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

    # ========================================================================
    # 内部辅助函数
    # ========================================================================

    def _validate_name(self, name: str) -> str | None:
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

    def _validate_category(self, category: str | None) -> str | None:
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

    def _validate_frontmatter(self, content: str) -> str | None:
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

    def _validate_content_size(self, content: str, label: str = "SKILL.md") -> str | None:
        """检查内容是否超出字符限制。"""
        if len(content) > MAX_SKILL_CONTENT_CHARS:
            return (
                f"{label} content is {len(content):,} characters "
                f"(limit: {MAX_SKILL_CONTENT_CHARS:,})."
            )
        return None

    def _validate_file_path(self, file_path: str) -> str | None:
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

    def _resolve_skill_dir(self, name: str, category: str | None = None) -> Path:
        """构建新技能的目录路径。"""
        if category:
            return self.skills_dir / category / name
        return self.skills_dir / name

    def _find_skill_dir(self, name: str) -> Path | None:
        """按名称查找技能目录。"""
        if not self.skills_dir.exists():
            return None

        for skill_md in self.skills_dir.rglob("SKILL.md"):
            if skill_md.parent.name == name:
                return skill_md.parent
        return None

    def _resolve_skill_target(self, skill_dir: Path, file_path: str) -> tuple[Path | None, str | None]:
        """解析支持文件路径并确保在技能目录内。"""
        target = skill_dir / file_path
        try:
            target.resolve().relative_to(skill_dir.resolve())
        except ValueError:
            return None, "File path escapes skill directory."
        return target, None

    def _atomic_write_text(self, file_path: Path, content: str, encoding: str = "utf-8") -> None:
        """原子写入文本内容到文件。"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            dir=str(file_path.parent),
            prefix=f".{file_path.name}.tmp.",
            suffix="",
        )
        try:
            with os.fdopen(fd, "w", encoding=encoding) as f:
                f.write(content)
            os.replace(temp_path, file_path)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
