"""Curator - 后台技能维护。

定期审查 Agent 创建的技能，自动转换生命周期状态：
active → stale → archived

配置：
- min_idle_hours: 空闲多少小时后触发审查
- interval_hours: 审查间隔
- stale_after_days: 多少天后标记 stale
- archive_after_days: 多少天后归档
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SkillUsage:
    """技能使用追踪数据。

    Attributes:
        use_count: 使用次数。
        view_count: 查看次数。
        patch_count: 补丁次数。
        last_activity_at: 最后活动时间戳。
        state: 生命周期状态 (active/stale/archived)。
        pinned: 是否置顶（豁免自动转换）。
    """
    use_count: int = 0
    view_count: int = 0
    patch_count: int = 0
    last_activity_at: float = 0.0
    state: str = "active"
    pinned: bool = False


class Curator:
    """Curator 后台技能维护。

    定期审查 Agent 创建的技能，自动转换生命周期状态。
    """

    def __init__(
        self,
        skills_dir: str | Path,
        min_idle_hours: float = 24.0,
        interval_hours: float = 168.0,  # 7 天
        stale_after_days: int = 30,
        archive_after_days: int = 90,
    ):
        """初始化 Curator。

        Args:
            skills_dir: 技能目录路径。
            min_idle_hours: 空闲触发时间。
            interval_hours: 审查间隔。
            stale_after_days: stale 阈值。
            archive_after_days: archive 阈值。
        """
        self._skills_dir = Path(skills_dir)
        self._min_idle_hours = min_idle_hours
        self._interval_hours = interval_hours
        self._stale_after_days = stale_after_days
        self._archive_after_days = archive_after_days
        self._usage_file = self._skills_dir / ".usage.json"
        self._last_run: float = 0.0

    def maybe_run(self) -> bool:
        """检查是否应该运行审查。

        Returns:
            True 表示已运行，False 表示跳过。
        """
        now = time.time()
        idle_hours = (now - self._last_run) / 3600

        if idle_hours < self._min_idle_hours:
            return False

        if idle_hours < self._interval_hours:
            return False

        self._run_review()
        self._last_run = now
        return True

    def _run_review(self) -> None:
        """执行审查。

        遍历所有 Agent 创建的技能，检查活动时间，
        自动转换状态：active → stale → archived。
        """
        usage = self._load_usage()

        for skill_name, data in usage.items():
            entry = SkillUsage(**data)

            # pinned 技能豁免
            if entry.pinned:
                continue

            days_inactive = (time.time() - entry.last_activity_at) / 86400

            if entry.state == "active" and days_inactive > self._stale_after_days:
                entry.state = "stale"
                usage[skill_name] = self._entry_to_dict(entry)

            elif entry.state == "stale" and days_inactive > self._archive_after_days:
                entry.state = "archived"
                usage[skill_name] = self._entry_to_dict(entry)

        self._save_usage(usage)

    def record_use(self, skill_name: str) -> None:
        """记录技能使用。

        Args:
            skill_name: 技能名称。
        """
        usage = self._load_usage()
        if skill_name not in usage:
            usage[skill_name] = {
                "use_count": 0,
                "view_count": 0,
                "patch_count": 0,
                "last_activity_at": time.time(),
                "state": "active",
                "pinned": False,
            }
        usage[skill_name]["use_count"] = usage[skill_name].get("use_count", 0) + 1
        usage[skill_name]["last_activity_at"] = time.time()
        self._save_usage(usage)

    def _load_usage(self) -> dict[str, Any]:
        """加载使用追踪数据。"""
        if self._usage_file.exists():
            return json.loads(self._usage_file.read_text(encoding="utf-8"))
        return {}

    def _save_usage(self, usage: dict[str, Any]) -> None:
        """保存使用追踪数据。"""
        self._skills_dir.mkdir(parents=True, exist_ok=True)
        self._usage_file.write_text(
            json.dumps(usage, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _entry_to_dict(entry: SkillUsage) -> dict[str, Any]:
        return {
            "use_count": entry.use_count,
            "view_count": entry.view_count,
            "patch_count": entry.patch_count,
            "last_activity_at": entry.last_activity_at,
            "state": entry.state,
            "pinned": entry.pinned,
        }
    # ========================================================================
    # 显式生命周期转换
    # ========================================================================

    def mark_stale(self, skill_name: str) -> bool:
        """显式标记技能为 stale。

        Args:
            skill_name: 技能名称。

        Returns:
            True 如果成功标记，False 如果技能不存在或已是 stale/archived。
        """
        usage = self._load_usage()
        if skill_name not in usage:
            return False

        entry = SkillUsage(**usage[skill_name])
        if entry.state in ("stale", "archived"):
            return False

        entry.state = "stale"
        usage[skill_name] = self._entry_to_dict(entry)
        self._save_usage(usage)
        return True

    def archive_skill(self, skill_name: str) -> bool:
        """归档指定技能。

        创建 tar.gz 备份后标记为 archived。

        Args:
            skill_name: 技能名称。

        Returns:
            True 如果成功归档，False 如果技能不存在。
        """
        usage = self._load_usage()
        if skill_name not in usage:
            return False

        # 创建备份
        self._create_backup(skill_name)

        entry = SkillUsage(**usage[skill_name])
        entry.state = "archived"
        usage[skill_name] = self._entry_to_dict(entry)
        self._save_usage(usage)
        return True

    def unarchive_skill(self, skill_name: str) -> bool:
        """恢复归档技能到 active 状态。

        Args:
            skill_name: 技能名称。

        Returns:
            True 如果成功恢复，False 如果技能不存在或未归档。
        """
        usage = self._load_usage()
        if skill_name not in usage:
            return False

        entry = SkillUsage(**usage[skill_name])
        if entry.state != "archived":
            return False

        entry.state = "active"
        entry.last_activity_at = time.time()
        usage[skill_name] = self._entry_to_dict(entry)
        self._save_usage(usage)
        return True

    # ========================================================================
    # 备份
    # ========================================================================

    def _create_backup(self, skill_name: str) -> str | None:
        """为技能创建 tar.gz 备份。

        Args:
            skill_name: 技能名称。

        Returns:
            备份文件路径，失败返回 None。
        """
        import tarfile

        skill_dir = self._skills_dir / skill_name
        if not skill_dir.exists() or not skill_dir.is_dir():
            return None

        backup_dir = self._skills_dir / ".backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{skill_name}_{timestamp}.tar.gz"

        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(skill_dir, arcname=skill_name)
            return str(backup_path)
        except Exception as e:
            print(f"备份失败 {skill_name}: {e}")
            return None

    # ========================================================================
    # 自动转换
    # ========================================================================

    def auto_transitions(self, skill_name: str) -> dict[str, str] | None:
        """执行单个技能的自动状态转换。

        根据 idle 天数执行：active → stale → archived。

        Args:
            skill_name: 技能名称。

        Returns:
            状态转换信息 {"from": "active", "to": "stale"}，无转换返回 None。
        """
        usage = self._load_usage()
        if skill_name not in usage:
            return None

        entry = SkillUsage(**usage[skill_name])

        if entry.pinned:
            return None

        days_inactive = (time.time() - entry.last_activity_at) / 86400
        old_state = entry.state

        if entry.state == "active" and days_inactive > self._stale_after_days:
            entry.state = "stale"
        elif entry.state == "stale" and days_inactive > self._archive_after_days:
            entry.state = "archived"

        if entry.state != old_state:
            usage[skill_name] = self._entry_to_dict(entry)
            self._save_usage(usage)
            return {"from": old_state, "to": entry.state}

        return None

    # ========================================================================
    # 审查 Agent 生成
    # ========================================================================

    def spawn_review_agent(self, skill_name: str) -> dict[str, str]:
        """生成审查任务描述（用于委托 review agent）。

        Args:
            skill_name: 技能名称。

        Returns:
            审查任务描述。
        """
        usage = self._load_usage()
        info = usage.get(skill_name, {})

        return {
            "task": "review_skill",
            "skill_name": skill_name,
            "usage": info,
            "action": "check_quality_and_relevance",
        }

    # ========================================================================
    # 使用追踪
    # ========================================================================

    def record_view(self, skill_name: str) -> None:
        """记录技能查看。

        Args:
            skill_name: 技能名称。
        """
        usage = self._load_usage()
        if skill_name not in usage:
            usage[skill_name] = {
                "use_count": 0,
                "view_count": 0,
                "patch_count": 0,
                "last_activity_at": time.time(),
                "state": "active",
                "pinned": False,
            }
        usage[skill_name]["view_count"] = usage[skill_name].get("view_count", 0) + 1
        usage[skill_name]["last_activity_at"] = time.time()
        self._save_usage(usage)

    def record_patch(self, skill_name: str) -> None:
        """记录技能补丁。

        Args:
            skill_name: 技能名称。
        """
        usage = self._load_usage()
        if skill_name not in usage:
            usage[skill_name] = {
                "use_count": 0,
                "view_count": 0,
                "patch_count": 0,
                "last_activity_at": time.time(),
                "state": "active",
                "pinned": False,
            }
        usage[skill_name]["patch_count"] = usage[skill_name].get("patch_count", 0) + 1
        usage[skill_name]["last_activity_at"] = time.time()
        self._save_usage(usage)

    def set_pinned(self, skill_name: str, pinned: bool) -> bool:
        """设置技能置顶状态。

        Args:
            skill_name: 技能名称。
            pinned: 是否置顶。

        Returns:
            True 如果成功，False 如果技能不存在。
        """
        usage = self._load_usage()
        if skill_name not in usage:
            return False

        usage[skill_name]["pinned"] = pinned
        usage[skill_name]["last_activity_at"] = time.time()
        self._save_usage(usage)
        return True

