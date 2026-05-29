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

# 历史文件路径
HISTORY_DIR = Path.home() / ".nanohermes" / "tui"
HISTORY_FILE = HISTORY_DIR / "input_history.json"


class TUIHistory(History):
    """TUI 输入历史。
    
    继承 prompt_toolkit History，提供持久化功能。
    """
    
    def __init__(self, max_items: int = 1000):
        """初始化历史记录。
        
        Args:
            max_items: 最大历史记录条数。
        """
        super().__init__()
        self.max_items = max_items
        self._store: typing_list[str] = []
        self._load()
    
    def append_string(self, string: str) -> None:
        """添加字符串到历史。
        
        Args:
            string: 要添加的字符串。
        """
        if not string or not string.strip():
            return
        
        # 避免重复添加相同的连续项
        if self._store and self._store[-1] == string:
            return
        
        self._store.append(string)
        
        # 限制大小
        if len(self._store) > self.max_items:
            self._store = self._store[-self.max_items:]
        
        # 持久化
        self._save()
    
    def _load(self) -> None:
        """从文件加载历史。"""
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
        """保存历史到文件。"""
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
        """加载历史字符串（prompt_toolkit 抽象方法）。
        
        prompt_toolkit 的基类 load() 会调用此方法并异步 yield 每个字符串。
        
        Returns:
            历史记录列表（最新的在前）。
        """
        return list(reversed(self._store))
    
    def store_string(self, string: str) -> None:
        """存储字符串（prompt_toolkit 抽象方法）。
        
        Args:
            string: 要存储的字符串。
        """
        self.append_string(string)
