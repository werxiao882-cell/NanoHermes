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
    COMMANDS = {
        "/help": "显示帮助信息",
        "/clear": "清空屏幕",
        "/quit": "退出 TUI",
        "/resume": "恢复会话",
        "/status": "显示当前状态",
        "/tools": "显示工具调用历史",
    }

    def get_completions(self, document: Document, complete_event) -> list[Completion]:
        text = document.text_before_cursor
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
    def __init__(self, max_items: int = 20):
        self.max_items = max_items

    def get_completions(self, document: Document, complete_event) -> list[Completion]:
        text = document.text_before_cursor
        words = text.split()
        if not words:
            return

        last_word = words[-1]
        if "/" in last_word or "\\" in last_word or last_word.startswith("."):
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
    def __init__(self, context_fn: Callable | None = None):
        self.context_fn = context_fn
        self.command_completer = CommandCompleter()
        self.file_completer = FilePathCompleter()

    def get_completions(self, document: Document, complete_event) -> list[Completion]:
        text = document.text_before_cursor
        # Determine if this looks like a command or file path
        if text.startswith("/") and len(text) > 1:
            first_word = text.split()[0] if text.split() else text
            after_slash = first_word[1:]  # everything after the leading /
            # If the part after / contains another /, it's a file path (e.g. /tmp/foo)
            # If after_slash is empty (just "/"), treat as command
            if "/" not in after_slash:
                yield from self.command_completer.get_completions(document, complete_event)
                return
        elif text == "/":
            yield from self.command_completer.get_completions(document, complete_event)
            return
        yield from self.file_completer.get_completions(document, complete_event)
        if self.context_fn:
            context = self.context_fn()
