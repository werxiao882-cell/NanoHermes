"""TUI 补全器。

实现命令补全、文件路径补全和上下文感知补全。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class CommandCompleter(Completer):
    """命令补全器。
    
    补全斜杠命令（如 /help, /clear, /resume）。
    """
    
    COMMANDS = {
        "/help": "显示帮助信息",
        "/clear": "清空屏幕",
        "/quit": "退出 TUI",
        "/resume": "恢复会话",
        "/status": "显示当前状态",
        "/tools": "显示工具调用历史",
    }
    
    def get_completions(self, document: Document, complete_event) -> list[Completion]:
        """获取命令补全。
        
        Args:
            document: 当前文档。
            complete_event: 补全事件。
            
        Yields:
            Completion 实例。
        """
        text = document.text_before_cursor
        
        # 只在输入 / 时触发命令补全
        if text.startswith("/"):
            parts = text.split()
            cmd = parts[0]
            
            for command, description in self.COMMANDS.items():
                if command.startswith(cmd):
                    yield Completion(
                        command,
                        start_position=-len(cmd),
                        display=command,
                        display_meta=description,
                    )


class FilePathCompleter(Completer):
    """文件路径补全器。
    
    补全文件和目录路径。
    """
    
    def __init__(self, max_items: int = 20):
        """初始化文件路径补全器。
        
        Args:
            max_items: 最大补全项数。
        """
        self.max_items = max_items
    
    def get_completions(self, document: Document, complete_event) -> list[Completion]:
        """获取文件路径补全。
        
        Args:
            document: 当前文档。
            complete_event: 补全事件。
            
        Yields:
            Completion 实例。
        """
        text = document.text_before_cursor
        
        # 查找路径片段
        words = text.split()
        if not words:
            return
        
        last_word = words[-1]
        
        # 检查是否像路径
        if "/" in last_word or "\\" in last_word or last_word.startswith("."):
            # 解析路径
            if os.path.isabs(last_word):
                base_path = Path(last_word)
            else:
                base_path = Path.cwd() / last_word
            
            parent = base_path.parent
            prefix = base_path.name
            
            if parent.exists():
                count = 0
                for item in sorted(parent.iterdir()):
                    if item.name.startswith(prefix):
                        is_dir = item.is_dir()
                        suffix = "/" if is_dir else ""
                        
                        yield Completion(
                            item.name + suffix,
                            start_position=-len(prefix),
                            display=item.name + suffix,
                            display_meta="目录" if is_dir else "文件",
                        )
                        
                        count += 1
                        if count >= self.max_items:
                            break


class ContextAwareCompleter(Completer):
    """上下文感知补全器。
    
    根据当前状态提供智能补全。
    """
    
    def __init__(self, context_fn: Callable | None = None):
        """初始化上下文感知补全器。
        
        Args:
            context_fn: 获取当前上下文的函数。
        """
        self.context_fn = context_fn
        self.command_completer = CommandCompleter()
        self.file_completer = FilePathCompleter()
    
    def get_completions(self, document: Document, complete_event) -> list[Completion]:
        """获取上下文感知补全。
        
        Args:
            document: 当前文档。
            complete_event: 补全事件。
            
        Yields:
            Completion 实例。
        """
        text = document.text_before_cursor
        
        # 命令补全
        if text.startswith("/"):
            yield from self.command_completer.get_completions(document, complete_event)
            return
        
        # 文件路径补全
        yield from self.file_completer.get_completions(document, complete_event)
        
        # 上下文感知补全（未来扩展）
        if self.context_fn:
            context = self.context_fn()
            # 可以根据上下文提供额外补全
