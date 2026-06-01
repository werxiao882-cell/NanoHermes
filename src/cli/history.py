"""TUI 输入历史管理器。

维护输入历史记录和持久化。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List as typing_list

from prompt_toolkit.history import History

logger = logging.getLogger(__name__)

HISTORY_DIR = Path.home() / ".nanohermes" / "tui"
HISTORY_FILE = HISTORY_DIR / "input_history.json"


class TUIHistory(History):
    def __init__(self, max_items: int = 1000):
        super().__init__()
        self.max_items = max_items
        self._store: typing_list[str] = []
        self._load()

    def append_string(self, string: str) -> None:
        if not string or not string.strip():
            return
        if self._store and self._store[-1] == string:
            return
        self._store.append(string)
        if len(self._store) > self.max_items:
            self._store = self._store[-self.max_items:]
        self._save()

    def _load(self) -> None:
        if not HISTORY_FILE.exists():
            return
        try:
            HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            self._store = data.get("history", [])
            logger.debug(f"已加载 {len(self._store)} 条历史记录")
        except Exception as e:
            logger.warning(f"加载历史记录失败: {e}")
            self._store = []

    def _save(self) -> None:
        try:
            HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            data = {"history": self._store}
            HISTORY_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"保存历史记录失败: {e}")

    def load_history_strings(self) -> typing_list[str]:
        return list(reversed(self._store))

    def store_string(self, string: str) -> None:
        self.append_string(string)
