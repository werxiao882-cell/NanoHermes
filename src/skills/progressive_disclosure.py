"""渐进式披露架构 + 平台过滤 + 条件激活。

三层加载策略，减少 system prompt token 消耗：
- Tier 1: 系统提示索引（始终存在），name + description 分类索引
- Tier 2: 工具发现（按需加载），skills_list / skill_view
- Tier 3: 条件激活（动态显示），requires_tools / fallback_for_toolsets

两层缓存：
- 内存 LRU: OrderedDict，max 8 entries
- 磁盘快照: .skills_prompt_snapshot.json，mtime/size manifest 验证

参考 hermes-agent-ref: agent/skill_utils.py, agent/prompt_builder.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PLATFORM_MAP = {
    "macos": "darwin",
    "linux": "linux",
    "windows": "win32",
}

_CACHE_MAX = 8
_SNAPSHOT_VERSION = 1


def skill_matches_platform(platforms: list[str] | None) -> bool:
    """检查技能是否匹配当前平台。

    设计理由：
    - platforms 为 None 或空列表表示全平台兼容（向后兼容）
    - 使用 PLATFORM_MAP 将友好名称映射到 sys.platform 值
    - Termux/Android 特殊处理：sys.platform 可能是 "linux" 或 "android"

    Args:
        platforms: 支持的平台列表，如 ["linux", "macos"]。

    Returns:
        True 表示匹配当前平台。
    """
    if not platforms:
        return True

    current = sys.platform
    is_termux = os.environ.get("ANDROID_ROOT") is not None

    for p in platforms:
        mapped = PLATFORM_MAP.get(p, p)
        if mapped == current:
            return True
        if p in ("termux", "android") and is_termux:
            return True
        if is_termux and mapped == "linux":
            return True

    return False


def extract_skill_conditions(frontmatter: dict[str, Any]) -> dict[str, list[str]]:
    """从 frontmatter 提取条件激活字段。

    路径: metadata.hermes.{field}

    Args:
        frontmatter: 解析后的 YAML frontmatter 字典。

    Returns:
        包含四个条件字段的字典。
    """
    hermes = {}
    metadata = frontmatter.get("metadata")
    if isinstance(metadata, dict):
        hermes = metadata.get("hermes", {}) or {}
    if not isinstance(hermes, dict):
        hermes = {}

    return {
        "fallback_for_toolsets": _ensure_list(hermes.get("fallback_for_toolsets")),
        "requires_toolsets": _ensure_list(hermes.get("requires_toolsets")),
        "fallback_for_tools": _ensure_list(hermes.get("fallback_for_tools")),
        "requires_tools": _ensure_list(hermes.get("requires_tools")),
    }


def _ensure_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        return [str(v) for v in val]
    return []


def skill_should_show(
    conditions: dict[str, list[str]],
    available_tools: set[str] | None = None,
    available_toolsets: set[str] | None = None,
) -> bool:
    """评估条件激活规则，决定是否显示技能。

    设计理由：
    - fallback_for_*: 当主工具/工具集可用时隐藏（技能是后备方案）
    - requires_*: 当必需工具/工具集不可用时隐藏（技能无法工作）
    - 当 available_tools 和 available_toolsets 都为 None 时，显示所有技能

    Args:
        conditions: extract_skill_conditions() 的返回值。
        available_tools: 当前可用的工具名称集合。
        available_toolsets: 当前可用的工具集名称集合。

    Returns:
        True 表示应该显示该技能。
    """
    if available_tools is None and available_toolsets is None:
        return True

    tools = available_tools or set()
    toolsets = available_toolsets or set()

    for ts in conditions.get("requires_toolsets", []):
        if ts not in toolsets:
            return False

    for t in conditions.get("requires_tools", []):
        if t not in tools:
            return False

    for ts in conditions.get("fallback_for_toolsets", []):
        if ts in toolsets:
            return False

    for t in conditions.get("fallback_for_tools", []):
        if t in tools:
            return False

    return True


class SkillProgressiveDisclosure:
    """渐进式披露管理器。

    构建系统提示索引（Tier 1），支持两层缓存和条件过滤。
    """

    def __init__(self, skills_dir: Path | None = None):
        if skills_dir is None:
            skills_dir = Path.home() / ".nanohermes" / "skills"
        self._skills_dir = Path(skills_dir)
        self._cache: OrderedDict[tuple, str] = OrderedDict()
        self._lock = threading.Lock()

    def build_system_prompt_index(
        self,
        available_tools: set[str] | None = None,
        available_toolsets: set[str] | None = None,
        disabled: set[str] | None = None,
    ) -> str:
        """构建系统提示索引（Tier 1）。

        返回分类索引：name + 一行描述。
        使用两层缓存（内存 LRU + 磁盘快照）减少重复扫描。

        Args:
            available_tools: 当前可用工具集合。
            available_toolsets: 当前可用工具集集合。
            disabled: 被禁用的技能名称集合。

        Returns:
            技能索引文本。
        """
        disabled = disabled or set()
        cache_key = (
            str(self._skills_dir),
            frozenset(available_tools or set()),
            frozenset(available_toolsets or set()),
            frozenset(disabled),
        )

        with self._lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                return self._cache[cache_key]

        result = self._build_index(available_tools, available_toolsets, disabled)

        with self._lock:
            self._cache[cache_key] = result
            if len(self._cache) > _CACHE_MAX:
                self._cache.popitem(last=False)

        return result

    def _build_index(
        self,
        available_tools: set[str] | None,
        available_toolsets: set[str] | None,
        disabled: set[str],
    ) -> str:
        """从磁盘扫描构建索引（冷路径）。"""
        snapshot = self._load_snapshot()
        entries: list[dict[str, Any]] = []

        if snapshot and snapshot.get("version") == _SNAPSHOT_VERSION:
            manifest = snapshot.get("manifest", {})
            current_manifest = self._build_manifest()
            if manifest == current_manifest:
                entries = snapshot.get("entries", [])
            else:
                entries = self._scan_entries()
                self._save_snapshot(entries, current_manifest)
        else:
            entries = self._scan_entries()
            manifest = self._build_manifest()
            self._save_snapshot(entries, manifest)

        categories: dict[str, list[tuple[str, str]]] = {}
        for entry in entries:
            name = entry.get("skill_name", "")
            if name in disabled:
                continue

            platforms = entry.get("platforms")
            if not skill_matches_platform(platforms):
                continue

            conditions = entry.get("conditions", {})
            if not skill_should_show(conditions, available_tools, available_toolsets):
                continue

            cat = entry.get("category", "other")
            desc = entry.get("description", "")
            categories.setdefault(cat, []).append((name, desc))

        if not categories:
            return ""

        lines = ["# Skills", ""]
        for cat in sorted(categories.keys()):
            skills = categories[cat]
            if len(categories) > 1:
                lines.append(f"## {cat}")
                lines.append("")
            for name, desc in sorted(skills):
                lines.append(f"- **{name}**: {desc}")
            lines.append("")

        lines.append("Before replying, scan the skills above. If a skill matches your task, load it with skill_view(name).")
        return "\n".join(lines)

    def _scan_entries(self) -> list[dict[str, Any]]:
        """扫描技能目录，构建元数据条目列表。"""
        from src.skills.loader import SkillLoader

        loader = SkillLoader()
        entries: list[dict[str, Any]] = []

        if not self._skills_dir.exists():
            return entries

        for item in sorted(self._skills_dir.iterdir()):
            if not item.is_dir():
                continue
            if item.name.startswith("."):
                continue

            skill_file = item / "SKILL.md"
            if not skill_file.exists():
                for sub in sorted(item.iterdir()):
                    if sub.is_dir():
                        sub_skill = sub / "SKILL.md"
                        if sub_skill.exists():
                            entry = self._load_entry(loader, sub_skill, sub)
                            if entry:
                                entries.append(entry)
                continue

            entry = self._load_entry(loader, skill_file, item)
            if entry:
                entries.append(entry)

        return entries

    def _load_entry(self, loader: Any, skill_file: Path, skill_dir: Path) -> dict[str, Any] | None:
        """加载单个技能条目。"""
        try:
            skill = loader.load(skill_file)
            text = skill_file.read_text(encoding="utf-8")
            fm_match = text.find("---")
            fm_end = text.find("---", fm_match + 3) if fm_match >= 0 else -1
            frontmatter: dict[str, Any] = {}
            if fm_match >= 0 and fm_end > fm_match:
                try:
                    import yaml
                    frontmatter = yaml.safe_load(text[fm_match + 3:fm_end]) or {}
                except Exception:
                    pass

            rel = skill_dir.relative_to(self._skills_dir)
            parts = rel.parts
            category = parts[0] if len(parts) > 1 else "other"

            return {
                "skill_name": skill.name,
                "category": category,
                "description": skill.description,
                "platforms": skill.platforms,
                "conditions": extract_skill_conditions(frontmatter),
            }
        except Exception as e:
            logger.debug(f"Failed to scan skill {skill_dir}: {e}")
            return None

    def _build_manifest(self) -> dict[str, list[int]]:
        """构建 mtime/size manifest 用于缓存验证。"""
        manifest: dict[str, list[int]] = {}
        if not self._skills_dir.exists():
            return manifest

        for item in self._skills_dir.rglob("SKILL.md"):
            try:
                rel = str(item.relative_to(self._skills_dir))
                stat = item.stat()
                manifest[rel] = [stat.st_mtime_ns, stat.st_size]
            except OSError:
                continue
        return manifest

    def _snapshot_path(self) -> Path:
        return self._skills_dir / ".skills_prompt_snapshot.json"

    def _load_snapshot(self) -> dict[str, Any] | None:
        """加载磁盘快照。"""
        path = self._snapshot_path()
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _save_snapshot(self, entries: list[dict[str, Any]], manifest: dict[str, list[int]]) -> None:
        """保存磁盘快照。"""
        data = {
            "version": _SNAPSHOT_VERSION,
            "manifest": manifest,
            "entries": entries,
        }
        try:
            path = self._snapshot_path()
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.debug(f"Failed to save skills snapshot: {e}")

    def clear_cache(self) -> None:
        """清除内存缓存和磁盘快照。"""
        with self._lock:
            self._cache.clear()
        try:
            path = self._snapshot_path()
            if path.exists():
                path.unlink()
        except OSError:
            pass
