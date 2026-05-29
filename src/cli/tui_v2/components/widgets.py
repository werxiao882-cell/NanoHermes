"""TUI 组件库。

实现 Ink UI 风格组件：面板、加载指示器、进度条等。
"""

from __future__ import annotations

import sys
import time
from typing import List as typing_list

from src.cli.tui_v2.utils.ansi import (
    ANSI_RESET,
    styled_text,
    move_cursor_up,
    clear_line,
    get_terminal_size,
)


# 加载动画帧
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]


class Panel:
    """面板组件。
    
    带边框和标题的面板，用于显示内容。
    """
    
    def __init__(
        self,
        title: str = "",
        border_color: str = "bright_black",
        title_color: str = "bright_blue",
    ):
        """初始化面板。
        
        Args:
            title: 面板标题。
            border_color: 边框颜色。
            title_color: 标题颜色。
        """
        self.title = title
        self.border_color = border_color
        self.title_color = title_color
    
    def render(self, content: str, width: int | None = None) -> str:
        """渲染面板。
        
        Args:
            content: 面板内容。
            width: 面板宽度（可选）。
            
        Returns:
            渲染后的面板字符串。
        """
        if width is None:
            width, _ = get_terminal_size()
            width = min(width, 120)
        
        lines = content.split("\n")
        inner_width = width - 4  # 边框占用
        
        # 构建面板
        result = []
        
        # 顶行
        if self.title:
            title_text = f" {self.title} "
            title_styled = styled_text(title_text, self.title_color)
            line_len = len(title_text)
            border_line = styled_text("┌" + "─" * (line_len + 2) + "┐", self.border_color)
            # 简化实现
            result.append(styled_text(f"┌─{title_text}{'─' * (width - len(title_text) - 3)}┐", self.border_color))
        else:
            result.append(styled_text("┌" + "─" * (width - 2) + "┐", self.border_color))
        
        # 内容行
        for line in lines:
            # 截断过长的行
            if len(line) > inner_width:
                line = line[:inner_width - 3] + "..."
            padded = line.ljust(inner_width)
            result.append(styled_text(f"│ {padded} │", self.border_color))
        
        # 底行
        result.append(styled_text("└" + "─" * (width - 2) + "┘", self.border_color))
        
        return "\n".join(result)


class Spinner:
    """加载指示器（旋转动画）。"""
    
    def __init__(self, message: str = "加载中...", color: str = "yellow"):
        """初始化加载指示器。
        
        Args:
            message: 显示消息。
            color: 动画颜色。
        """
        self.message = message
        self.color = color
        self._frame_index = 0
        self._running = False
    
    def _get_frame(self) -> str:
        """获取当前帧。
        
        Returns:
            当前帧字符串。
        """
        frame = SPINNER_FRAMES[self._frame_index % len(SPINNER_FRAMES)]
        self._frame_index += 1
        return styled_text(frame, self.color)
    
    def render(self) -> str:
        """渲染当前帧。
        
        Returns:
            渲染后的字符串。
        """
        return f"{self._get_frame()} {self.message}"
    
    def animate(self, duration: float = 1.0, fps: int = 10) -> None:
        """运行动画。
        
        Args:
            duration: 动画持续时间（秒）。
            fps: 帧率。
        """
        self._running = True
        start_time = time.time()
        
        while time.time() - start_time < duration:
            sys.stdout.write("\r" + self.render())
            sys.stdout.flush()
            time.sleep(1.0 / fps)
        
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()
        self._running = False


class ProgressBar:
    """进度条组件。"""
    
    def __init__(
        self,
        total: int = 100,
        width: int = 40,
        color: str = "green",
    ):
        """初始化进度条。
        
        Args:
            total: 总进度。
            width: 进度条宽度（字符数）。
            color: 进度条颜色。
        """
        self.total = total
        self.width = width
        self.color = color
        self.current = 0
    
    def update(self, value: int) -> str:
        """更新进度。
        
        Args:
            value: 当前进度值。
            
        Returns:
            渲染后的进度条字符串。
        """
        self.current = min(value, self.total)
        percent = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percent)
        empty = self.width - filled
        
        bar = "█" * filled + "░" * empty
        percent_str = f"{percent * 100:.1f}%"
        
        return styled_text(f"[{bar}] {percent_str}", self.color)
    
    def render(self) -> str:
        """渲染当前进度。
        
        Returns:
            渲染后的进度条字符串。
        """
        return self.update(self.current)
