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

        interval_hours = (now - self._last_run) / 3600
        if interval_hours < self._interval_hours:
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
