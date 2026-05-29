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

from src.cli.tui_v2.utils.ansi import styled_text


class TypewriterEffect:
    """打字机效果。
    
    逐字符输出，模拟打字机效果。
    """
    
    def __init__(self, speed_ms: int = 10, skip_key: str = "any"):
        """初始化打字机效果。
        
        Args:
            speed_ms: 每个字符的间隔时间（毫秒）。
            skip_key: 跳过按键（"any" 表示任意键）。
        """
        self.speed_ms = speed_ms
        self.skip_key = skip_key
        self._skipped = False
    
    async def print(self, text: str, end: str = "\n") -> None:
        """打印带打字机效果的文本。
        
        Args:
            text: 要打印的文本。
            end: 结束符。
        """
        for char in text:
            if self._skipped:
                # 已跳过，直接打印剩余
                print(text[text.index(char):], end=end, flush=True)
                return
            
            sys.stdout.write(char)
            sys.stdout.flush()
            
            # 等待指定时间
            await asyncio.sleep(self.speed_ms / 1000.0)
        
        sys.stdout.write(end)
        sys.stdout.flush()
    
    def skip(self) -> None:
        """跳过打字机效果。"""
        self._skipped = True


class StreamingMarkdown:
    """流式 Markdown 渲染。
    
    支持增量渲染 Markdown 内容。
    """
    
    def __init__(self):
        """初始化流式 Markdown 渲染器。"""
        self.console = Console(force_terminal=True)
        self._buffer = ""
    
    def update(self, chunk: str) -> None:
        """更新内容。
        
        Args:
            chunk: 新增的内容块。
        """
        self._buffer += chunk
    
    def render(self) -> None:
        """渲染当前缓冲区。"""
        if not self._buffer.strip():
            return
        
        md = Markdown(self._buffer)
        self.console.print(md)
    
    def clear(self) -> None:
        """清空缓冲区。"""
        self._buffer = ""
    
    @property
    def content(self) -> str:
        """获取当前内容。"""
        return self._buffer


class StreamingOutputBuffer:
    """流式输出缓冲区。
    
    管理流式输出的缓冲和刷新。
    """
    
    def __init__(self, flush_interval_ms: int = 50):
        """初始化输出缓冲区。
        
        Args:
            flush_interval_ms: 刷新间隔（毫秒）。
        """
        self.flush_interval_ms = flush_interval_ms
        self._buffer = ""
        self._last_flush = time.time()
    
    def write(self, text: str) -> None:
        """写入文本到缓冲区。
        
        Args:
            text: 要写入的文本。
        """
        self._buffer += text
        
        # 检查是否需要刷新
        if self._should_flush():
            self.flush()
    
    def _should_flush(self) -> bool:
        """检查是否应该刷新。
        
        Returns:
            True 如果应该刷新。
        """
        now = time.time()
        return (now - self._last_flush) >= (self.flush_interval_ms / 1000.0)
    
    def flush(self) -> None:
        """刷新缓冲区。"""
        if self._buffer:
            sys.stdout.write(self._buffer)
            sys.stdout.flush()
            self._buffer = ""
            self._last_flush = time.time()
    
    def clear(self) -> None:
        """清空缓冲区。"""
        self._buffer = ""


class StreamingStatusIndicator:
    """流式输出状态指示器。
    
    显示输出状态（输出中/完成）。
    """
    
    def __init__(self):
        """初始化状态指示器。"""
        self._is_streaming = False
    
    def start(self) -> None:
        """开始流式输出。"""
        self._is_streaming = True
        sys.stdout.write(styled_text("⏳ 输出中...", "yellow"))
        sys.stdout.flush()
    
    def update(self) -> None:
        """更新状态指示器。"""
        if self._is_streaming:
            # 移动光标并覆盖
            sys.stdout.write("\r" + " " * 20 + "\r")
            sys.stdout.write(styled_text("⏳ 输出中...", "yellow"))
            sys.stdout.flush()
    
    def complete(self) -> None:
        """完成流式输出。"""
        self._is_streaming = False
        sys.stdout.write("\r" + " " * 20 + "\r")
        sys.stdout.write(styled_text("✅ 完成", "green") + "\n")
        sys.stdout.flush()
