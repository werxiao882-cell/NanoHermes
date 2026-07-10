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
        "/clear": "清空对话",
        "/status": "显示当前状态",
        "/sessions": "列出历史会话",
        "/resume": "恢复历史会话",
        "/title": "设置会话标题",
        "/skills": "列出所有技能",
        "/skills enable": "启用技能",
        "/skills disable": "禁用技能",
        "/tools": "列出所有工具",
        "/compress": "压缩上下文",
        "/reasoning": "切换推理模式",
        "/loop": "循环执行任务（/loop [间隔] [提示]）",
        "/stop-loop": "停止当前循环",
        "/quit": "退出",
        "/exit": "退出",
    }

    def __init__(self, skill_manager=None):
        self._skill_manager = skill_manager

    def get_completions(self, document: Document, complete_event) -> list[Completion]:
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        parts = text.split()

        # /skills enable <partial> 或 /skills disable <partial> → 补全技能名
        # 处理 "/skills enable " (末尾空格) 和 "/skills enable ar" (部分输入)
        if len(parts) >= 2 and parts[0] == "/skills" and parts[1] in ("enable", "disable"):
            if len(parts) == 2 and text.endswith(" "):
                # "/skills enable " → 显示所有技能名
                yield from self._complete_skill_names("")
                return
            elif len(parts) == 3:
                # "/skills enable ar" → 按前缀过滤
                yield from self._complete_skill_names(parts[2])
                return
            elif len(parts) == 2 and not text.endswith(" "):
                # "/skills enable" (无空格) → 补全子命令
                pass
            else:
                return

        # /skills enable|disable → 补全子命令
        if len(parts) == 2 and parts[0] == "/skills":
            sub = parts[1]
            for action in ("enable", "disable"):
                if action.startswith(sub):
                    yield Completion(
                        f"/skills {action}",
                        start_position=-len(text),
                        display=f"/skills {action}",
                        display_meta="启用技能" if action == "enable" else "禁用技能",
                    )
            return

        # 普通命令补全
        stripped = text.rstrip()
        for command, description in self.COMMANDS.items():
            if command.startswith(stripped):
                yield Completion(
                    command,
                    start_position=-len(text),
                    display=command,
                    display_meta=description,
                )

        # 技能名作为斜杠命令补全（/skill-name）
        if self._skill_manager and len(parts) == 1:
            prefix = parts[0][1:]  # 去掉开头的 /
            for entry in self._skill_manager.list_skills(enabled_only=True):
                name = entry.skill.name
                if name.startswith(prefix):
                    yield Completion(
                        f"/{name}",
                        start_position=-len(text),
                        display=f"/{name}",
                        display_meta=f"[skill] {entry.skill.description[:40]}",
                    )

    def _complete_skill_names(self, prefix: str) -> list[Completion]:
        """补全技能名称。"""
        if not self._skill_manager:
            return
        for entry in self._skill_manager.list_skills():
            name = entry.skill.name
            if name.startswith(prefix):
                status = "✓ 已启用" if entry.enabled else "✗ 已禁用"
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display=name,
                    display_meta=f"{status} | {entry.skill.description[:40]}",
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
    def __init__(self, context_fn: Callable | None = None, skill_manager=None):
        self.context_fn = context_fn
        self.command_completer = CommandCompleter(skill_manager=skill_manager)
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
