"""SkillManager - 技能编排器。

管理技能加载、启用/禁用、使用追踪。
将技能描述注入系统提示的 volatile 层，使模型知道可用技能。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.skills.loader import Skill, SkillLoader


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

    管理技能加载、启用/禁用、使用追踪。
    将已启用技能的描述注入系统提示 volatile 层。

    Attributes:
        skills_dir: 技能目录路径。
        _skills: 已加载的技能字典（名称 → SkillEntry）。
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
