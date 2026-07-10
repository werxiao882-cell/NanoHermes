"""MemoryStore：记忆系统唯一数据源。

管理 MEMORY.md 和 USER.md 两个目标文件，提供：
- § 分隔符条目解析（支持多行内容）
- 字符数限制（memory 2200, user 1375）
- 冻结快照（系统提示使用，会话内不变）
- 跨平台文件锁（fcntl / msvcrt / 降级无锁）
- 原子写入（tempfile + os.replace）
- 漂移检测（外部修改拒绝覆盖 + .bak 备份）
- 内容扫描（注入/渗出模式检测）
- 去重和使用量追踪

设计理由：
三条并行读写路径（memory_tool.py, FileMemoryProvider, PromptAssembler）
各自独立操作文件，数据一致性无法保证。MemoryStore 统一为单一数据源，
所有路径通过委托调用，确保原子性和一致性。
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ENTRY_DELIMITER = "\n§\n"
MEMORY_CHAR_LIMIT = 2200
USER_CHAR_LIMIT = 1375

_MEMORY_THREAT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"ignore\s+(?:\w+\s+)*(?:previous|all|above|prior)\s+(?:\w+\s+)*instructions?", re.IGNORECASE), "prompt_injection"),
    (re.compile(r"you\s+are\s+(?:\w+\s+)*now\s+(?:a|an|the)\s+", re.IGNORECASE), "role_hijack"),
    (re.compile(r"curl\s+[^\n]*\$\{?\w*(?:KEY|TOKEN|SECRET|PASSWORD)", re.IGNORECASE), "exfil_curl"),
    (re.compile(r"wget\s+[^\n]*\$\{?\w*(?:KEY|TOKEN|SECRET|PASSWORD)", re.IGNORECASE), "exfil_wget"),
    (re.compile(r"(?:api[_-]?key|secret|token|password)\s*[=:]\s*['\"]?[a-zA-Z0-9]{20,}", re.IGNORECASE), "secret_assignment"),
    (re.compile(r"from\s+(?:now\s+on|this\s+point\s+forward)", re.IGNORECASE), "rule_override"),
    (re.compile(r"disregard\s+(?:all\s+)?(?:rules?|guidelines?|constraints?)", re.IGNORECASE), "disregard_rules"),
    (re.compile(r"new\s+instructions?\s*:", re.IGNORECASE), "new_instructions"),
    (re.compile(r"(?:enable|activate)\s+(?:developer|debug|admin)\s+mode", re.IGNORECASE), "developer_mode"),
    (re.compile(r"system\s*:\s*override", re.IGNORECASE), "system_override"),
]

_INVISIBLE_CHARS: set[str] = {
    "\u200b", "\u200c", "\u200d", "\u200e", "\u200f",
    "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
    "\u2060", "\u2061", "\u2062", "\u2063", "\u2064",
    "\ufeff",
    "\ufff9", "\ufffa", "\ufffb",
}

_TARGET_LABELS = {
    "memory": ("MEMORY", "your personal notes"),
    "user": ("USER PROFILE", "who the user is"),
}


class MemoryStore:
    """记忆系统唯一数据源。

    双状态模型：
    - live state: 实时条目列表，工具响应反映此状态
    - frozen snapshot: 系统提示使用，load_from_disk() 时捕获，会话内不变

    设计理由：
    Anthropic prompt caching 要求系统提示前缀稳定。
    冻结快照在会话启动时捕获一次，之后不再变化，
    工具调用修改实时状态并持久化到磁盘，下次会话快照刷新。
    """

    def __init__(
        self,
        memory_dir: Path,
        memory_char_limit: int = MEMORY_CHAR_LIMIT,
        user_char_limit: int = USER_CHAR_LIMIT,
    ):
        self._memory_dir = Path(memory_dir)
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._memory_path = self._memory_dir / "MEMORY.md"
        self._user_path = self._memory_dir / "USER.md"
        self._memory_char_limit = memory_char_limit
        self._user_char_limit = user_char_limit

        self.memory_entries: list[str] = []
        self.user_entries: list[str] = []

        self._system_prompt_snapshot: dict[str, str] = {"memory": "", "user": ""}

    def _path_for(self, target: str) -> Path:
        return self._user_path if target == "user" else self._memory_path

    def _entries_for(self, target: str) -> list[str]:
        return self.user_entries if target == "user" else self.memory_entries

    def _set_entries(self, target: str, entries: list[str]) -> None:
        if target == "user":
            self.user_entries = entries
        else:
            self.memory_entries = entries

    def _char_limit(self, target: str) -> int:
        return self._user_char_limit if target == "user" else self._memory_char_limit

    def _char_count(self, target: str) -> int:
        entries = self._entries_for(target)
        if not entries:
            return 0
        return sum(len(e) for e in entries) + len(ENTRY_DELIMITER) * (len(entries) - 1)

    def _success_response(self, target: str, message: str) -> dict:
        entries = self._entries_for(target)
        limit = self._char_limit(target)
        count = self._char_count(target)
        pct = int(count / limit * 100) if limit else 0
        return {
            "success": True,
            "target": target,
            "entries": list(entries),
            "usage": f"{pct}% — {count:,}/{limit:,} chars",
            "entry_count": len(entries),
            "message": message,
        }

    @staticmethod
    def _read_file(path: Path) -> list[str]:
        """读取文件并按 § 分隔符解析条目列表。

        空文件或不存在的文件返回空列表。
        每个条目 strip 后过滤空条目，保留顺序去重。
        """
        if not path.exists():
            return []
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []
        if not content.strip():
            return []
        raw = content.split(ENTRY_DELIMITER)
        seen: dict[str, None] = {}
        entries: list[str] = []
        for item in raw:
            item = item.strip()
            if item and item not in seen:
                seen[item] = None
                entries.append(item)
        return entries

    @staticmethod
    def _write_file(path: Path, entries: list[str]) -> None:
        """原子写入条目列表到文件。

        设计理由：
        使用 tempfile + os.replace 保证原子性。
        open("w") 会先截断文件，写入中途崩溃则数据丢失。
        原子写入保证读者始终看到完整的旧文件或新文件。
        """
        content = ENTRY_DELIMITER.join(entries) if entries else ""
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @staticmethod
    @contextmanager
    def _file_lock(path: Path):
        """跨平台排他文件锁。

        设计理由：
        使用 .lock 文件而非锁定原文件，因为记忆文件使用原子写入（temp + os.replace），
        如果锁定原文件，os.replace 会被阻塞。单独的 .lock 文件不影响原子写入流程。

        Unix: fcntl.flock(fd, LOCK_EX)
        Windows: msvcrt.locking(fd, LK_LOCK, 1)
        两者都不可用: 降级为无锁（单用户场景可接受）
        """
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        try:
            _acquire_lock(fd)
            yield
        finally:
            _release_lock(fd)
            try:
                os.close(fd)
            except OSError:
                pass

    def load_from_disk(self) -> None:
        """从磁盘加载条目，捕获系统提示冻结快照。

        读取 MEMORY.md 和 USER.md，按 § 分隔符解析，
        strip + 过滤空条目 + 去重（dict.fromkeys 保留首次出现）。
        加载完成后捕获冻结快照，会话内不再变化。
        """
        self.memory_entries = self._read_file(self._memory_path)
        self.user_entries = self._read_file(self._user_path)
        self._capture_snapshot()

    def _capture_snapshot(self) -> None:
        memory_block = self._render_block("memory", self.memory_entries)
        user_block = self._render_block("user", self.user_entries)
        self._system_prompt_snapshot = {
            "memory": memory_block or "",
            "user": user_block or "",
        }

    def _scan_memory_content(self, content: str) -> Optional[str]:
        """扫描记忆内容中的威胁模式和不可见字符。

        返回第一个匹配的威胁名称，无威胁返回 None。
        """
        for pattern, name in _MEMORY_THREAT_PATTERNS:
            if pattern.search(content):
                return name
        for ch in content:
            if ch in _INVISIBLE_CHARS:
                return f"invisible_unicode(U+{ord(ch):04X})"
        return None

    def _detect_external_drift(self, target: str) -> Optional[str]:
        """检测外部修改并拒绝覆盖。

        信号 1: 往返不匹配 — 解析后重新序列化 ≠ 原文件内容
        信号 2: 条目大小溢出 — 单个条目 > 整个文件的字符限制

        检测到漂移时：创建 .bak.<timestamp> 备份，返回备份路径。
        """
        path = self._path_for(target)
        if not path.exists():
            return None

        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        if not raw.strip():
            return None

        limit = self._char_limit(target)
        entries = self._read_file(path)

        round_trip = ENTRY_DELIMITER.join(entries) if entries else ""
        if round_trip.strip() != raw.strip():
            bak_path = path.with_suffix(f".bak.{int(time.time())}")
            try:
                bak_path.write_text(raw, encoding="utf-8")
            except OSError:
                pass
            return str(bak_path)

        for entry in entries:
            if len(entry) > limit:
                bak_path = path.with_suffix(f".bak.{int(time.time())}")
                try:
                    bak_path.write_text(raw, encoding="utf-8")
                except OSError:
                    pass
                return str(bak_path)

        return None

    def _reload_target(self, target: str) -> Optional[str]:
        """锁内重新加载磁盘状态，检测漂移和并行会话写入。

        返回漂移备份路径（如果检测到漂移），否则 None。
        """
        drift_bak = self._detect_external_drift(target)
        if drift_bak:
            return drift_bak
        path = self._path_for(target)
        self._set_entries(target, self._read_file(path))
        return None

    def add(self, target: str, content: str) -> dict:
        """追加新条目。

        流程：内容扫描 → 获取文件锁 → 重新加载磁盘状态 → 检查重复 → 检查字符限制 → 追加 → 原子写入
        """
        if not content or not content.strip():
            return {"success": False, "error": "Content cannot be empty."}

        content = content.strip()

        threat = self._scan_memory_content(content)
        if threat:
            return {"success": False, "error": f"Blocked: content matches threat pattern '{threat}'."}

        path = self._path_for(target)
        with self._file_lock(path):
            drift_bak = self._reload_target(target)
            if drift_bak:
                return {
                    "success": False,
                    "error": (
                        f"Refusing to write {path.name}: file on disk has content that "
                        f"wouldn't round-trip through our parser. Backup saved to {drift_bak}. "
                        f"Review and resolve manually."
                    ),
                }

            entries = self._entries_for(target)
            if content in entries:
                return self._success_response(target, "Entry already exists (no duplicate added).")

            limit = self._char_limit(target)
            current = self._char_count(target)
            new_total = current + len(content) + (len(ENTRY_DELIMITER) if entries else 0)
            if new_total > limit:
                return {
                    "success": False,
                    "error": (
                        f"Memory at {current}/{limit} chars. "
                        f"Adding this entry ({len(content)} chars) would exceed the limit."
                    ),
                }

            entries.append(content)
            self._set_entries(target, entries)
            self._write_file(path, entries)

        return self._success_response(target, "Entry added.")

    def replace(self, target: str, old_text: str, new_content: str) -> dict:
        """查找包含 old_text 子串的条目，替换为 new_content。

        流程：参数校验 → 内容扫描 → 获取文件锁 → 重新加载 → 子串匹配 → 歧义检测 → 字符限制 → 原子写入
        """
        if not old_text or not old_text.strip():
            return {"success": False, "error": "old_text cannot be empty."}
        if not new_content or not new_content.strip():
            return {"success": False, "error": "new_content cannot be empty. Use 'remove' to delete entries."}

        new_content = new_content.strip()

        threat = self._scan_memory_content(new_content)
        if threat:
            return {"success": False, "error": f"Blocked: content matches threat pattern '{threat}'."}

        path = self._path_for(target)
        with self._file_lock(path):
            drift_bak = self._reload_target(target)
            if drift_bak:
                return {
                    "success": False,
                    "error": (
                        f"Refusing to write {path.name}: file on disk has content that "
                        f"wouldn't round-trip through our parser. Backup saved to {drift_bak}."
                    ),
                }

            entries = self._entries_for(target)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e]

            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}

            if len(matches) > 1:
                match_list = [e[:80] for _, e in matches]
                return {
                    "success": False,
                    "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                    "matches": match_list,
                }

            idx, _ = matches[0]
            old_entry = entries[idx]
            new_entry = old_entry.replace(old_text, new_content, 1)

            test_entries = list(entries)
            test_entries[idx] = new_entry
            test_count = sum(len(e) for e in test_entries) + len(ENTRY_DELIMITER) * (len(test_entries) - 1)
            limit = self._char_limit(target)
            if test_count > limit:
                return {
                    "success": False,
                    "error": f"Replacement would put {target} at {test_count}/{limit} chars.",
                }

            entries[idx] = new_entry
            self._set_entries(target, entries)
            self._write_file(path, entries)

        return self._success_response(target, "Entry replaced.")

    def remove(self, target: str, old_text: str) -> dict:
        """删除包含 old_text 子串的条目。

        流程：参数校验 → 获取文件锁 → 重新加载 → 子串匹配 → 歧义检测 → 原子写入
        """
        if not old_text or not old_text.strip():
            return {"success": False, "error": "old_text cannot be empty."}

        path = self._path_for(target)
        with self._file_lock(path):
            drift_bak = self._reload_target(target)
            if drift_bak:
                return {
                    "success": False,
                    "error": (
                        f"Refusing to write {path.name}: file on disk has content that "
                        f"wouldn't round-trip through our parser. Backup saved to {drift_bak}."
                    ),
                }

            entries = self._entries_for(target)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e]

            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}

            if len(matches) > 1:
                match_list = [e[:80] for _, e in matches]
                return {
                    "success": False,
                    "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                    "matches": match_list,
                }

            idx, _ = matches[0]
            entries.pop(idx)
            self._set_entries(target, entries)
            self._write_file(path, entries)

        return self._success_response(target, "Entry removed.")

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        """返回冻结快照用于系统提示注入。

        返回 _system_prompt_snapshot 中对应 target 的内容。
        无条目时返回 None。
        """
        block = self._system_prompt_snapshot.get(target, "")
        return block if block else None

    def _render_block(self, target: str, entries: list[str]) -> Optional[str]:
        """渲染系统提示块（含标题和使用量指示器）。"""
        if not entries:
            return None

        label, desc = _TARGET_LABELS.get(target, (target.upper(), ""))
        limit = self._char_limit(target)
        count = sum(len(e) for e in entries) + len(ENTRY_DELIMITER) * (len(entries) - 1) if entries else 0
        pct = int(count / limit * 100) if limit else 0

        lines = [
            "═" * 42,
            f"{label} ({desc}) [{pct}% — {count:,}/{limit:,} chars]",
            "═" * 42,
        ]
        lines.append("\n§\n".join(entries))
        return "\n".join(lines)


def _acquire_lock(fd: int) -> None:
    """跨平台获取排他锁。"""
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX)
    except ImportError:
        try:
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        except (ImportError, OSError):
            pass


def _release_lock(fd: int) -> None:
    """跨平台释放排他锁。"""
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)
    except ImportError:
        pass
    try:
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    except (ImportError, OSError):
        pass


# ─── 多层记忆路径辅助方法 ─────────────────────────────────────

def get_session_summary_path(session_id: str, memory_dir: Path) -> Path:
    """获取会话摘要文件路径。"""
    return memory_dir.parent / "summaries" / f"{session_id}.md"


def get_agent_memory_path(agent_id: str, memory_dir: Path) -> Path:
    """获取 Agent 记忆文件路径。"""
    agent_dir = memory_dir.parent / "agents" / agent_id
    return agent_dir / "memory.json"


def get_team_memory_path(team_id: str, memory_dir: Path) -> Path:
    """获取团队记忆文件路径。"""
    team_dir = memory_dir.parent / "teams" / team_id
    return team_dir / "memory.json"
