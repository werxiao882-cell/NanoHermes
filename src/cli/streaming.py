"""TUI 流式输出系统。

实现打字机效果、增量渲染和缓冲区管理。
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import Callable

from rich.console import Console
from rich.markdown import Markdown

from src.cli.widgets import styled_text, KawaiiSpinner


class TypewriterEffect:
    def __init__(self, speed_ms: int = 10, skip_key: str = "any"):
        self.speed_ms = speed_ms
        self.skip_key = skip_key
        self._skipped = False

    async def print(self, text: str, end: str = "\n") -> None:
        for char in text:
            if self._skipped:
                print(text[text.index(char):], end=end, flush=True)
                return
            sys.stdout.write(char)
            sys.stdout.flush()
            await asyncio.sleep(self.speed_ms / 1000.0)
        sys.stdout.write(end)
        sys.stdout.flush()

    def skip(self) -> None:
        self._skipped = True


class StreamingMarkdown:
    def __init__(self):
        self.console = Console(force_terminal=True)
        self._buffer = ""

    def update(self, chunk: str) -> None:
        self._buffer += chunk

    def render(self) -> None:
        if not self._buffer.strip():
            return
        md = Markdown(self._buffer)
        self.console.print(md)

    def clear(self) -> None:
        self._buffer = ""

    @property
    def content(self) -> str:
        return self._buffer


class StreamingOutputBuffer:
    def __init__(self, flush_interval_ms: int = 50):
        self.flush_interval_ms = flush_interval_ms
        self._buffer = ""
        self._last_flush = time.time()

    def write(self, text: str) -> None:
        self._buffer += text
        if self._should_flush():
            self.flush()

    def _should_flush(self) -> bool:
        now = time.time()
        return (now - self._last_flush) >= (self.flush_interval_ms / 1000.0)

    def flush(self) -> None:
        if self._buffer:
            sys.stdout.write(self._buffer)
            sys.stdout.flush()
            self._buffer = ""
            self._last_flush = time.time()

    def clear(self) -> None:
        self._buffer = ""


class StreamingStatusIndicator:
    def __init__(self):
        self._is_streaming = False
        self._spinner = KawaiiSpinner(message="思考中...", color="cyan")

    def start(self) -> None:
        self._is_streaming = True
        self._spinner.set_state("working")
        sys.stdout.write(self._spinner.render())
        sys.stdout.flush()

    def update(self) -> None:
        if self._is_streaming:
            sys.stdout.write("\r" + " " * 40 + "\r")
            self._spinner._face_index += 1
            sys.stdout.write(self._spinner.render())
            sys.stdout.flush()

    def complete(self) -> None:
        self._is_streaming = False
        sys.stdout.write("\r" + " " * 40 + "\r")
        sys.stdout.flush()
