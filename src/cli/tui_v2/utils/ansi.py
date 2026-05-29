"""ANSI 终端控制工具。

提供颜色、光标位置和清屏等底层终端控制功能。
"""

from __future__ import annotations

import sys


# ANSI 转义码
ANSI_RESET = "\033[0m"
ANSI_CLEAR_SCREEN = "\033[2J"
ANSI_CLEAR_LINE = "\033[2K"
ANSI_HOME = "\033[H"

# 颜色代码
ANSI_COLORS = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bright_black": "\033[90m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bright_white": "\033[97m",
}

# 背景颜色
ANSI_BG_COLORS = {
    "black": "\033[40m",
    "red": "\033[41m",
    "green": "\033[42m",
    "yellow": "\033[43m",
    "blue": "\033[44m",
    "magenta": "\033[45m",
    "cyan": "\033[46m",
    "white": "\033[47m",
}


def set_color(color_name: str, bright: bool = False) -> str:
    """设置文本颜色。
    
    Args:
        color_name: 颜色名称。
        bright: 是否使用亮色。
        
    Returns:
        ANSI 转义码。
    """
    if bright:
        return ANSI_COLORS.get(f"bright_{color_name}", "")
    return ANSI_COLORS.get(color_name, "")


def set_bg_color(color_name: str) -> str:
    """设置背景颜色。
    
    Args:
        color_name: 颜色名称。
        
    Returns:
        ANSI 转义码。
    """
    return ANSI_BG_COLORS.get(color_name, "")


def move_cursor(row: int, col: int) -> str:
    """移动光标到指定位置。
    
    Args:
        row: 行号（1-based）。
        col: 列号（1-based）。
        
    Returns:
        ANSI 转义码。
    """
    return f"\033[{row};{col}H"


def move_cursor_up(lines: int = 1) -> str:
    """移动光标向上。
    
    Args:
        lines: 移动行数。
        
    Returns:
        ANSI 转义码。
    """
    return f"\033[{lines}A"


def move_cursor_down(lines: int = 1) -> str:
    """移动光标向下。
    
    Args:
        lines: 移动行数。
        
    Returns:
        ANSI 转义码。
    """
    return f"\033[{lines}B"


def move_cursor_right(cols: int = 1) -> str:
    """移动光标向右。
    
    Args:
        cols: 移动列数。
        
    Returns:
        ANSI 转义码。
    """
    return f"\033[{cols}C"


def move_cursor_left(cols: int = 1) -> str:
    """移动光标向左。
    
    Args:
        cols: 移动列数。
        
    Returns:
        ANSI 转义码。
    """
    return f"\033[{cols}D"


def clear_screen() -> str:
    """清屏并移动光标到左上角。
    
    Returns:
        ANSI 转义码。
    """
    return ANSI_CLEAR_SCREEN + ANSI_HOME


def clear_line() -> str:
    """清除当前行。
    
    Returns:
        ANSI 转义码。
    """
    return ANSI_CLEAR_LINE


def styled_text(text: str, color: str, bg_color: str | None = None, bold: bool = False) -> str:
    """生成带样式的文本。
    
    Args:
        text: 文本内容。
        color: 前景颜色。
        bg_color: 背景颜色（可选）。
        bold: 是否加粗。
        
    Returns:
        带样式的文本。
    """
    codes = []
    codes.append(set_color(color))
    if bg_color:
        codes.append(set_bg_color(bg_color))
    if bold:
        codes.append("\033[1m")
    
    codes.append(text)
    codes.append(ANSI_RESET)
    
    return "".join(codes)


def get_terminal_size() -> tuple[int, int]:
    """获取终端尺寸。
    
    Returns:
        (列数, 行数) 元组。
    """
    try:
        import shutil
        size = shutil.get_terminal_size(fallback=(80, 24))
        return size.columns, size.lines
    except Exception:
        return 80, 24
