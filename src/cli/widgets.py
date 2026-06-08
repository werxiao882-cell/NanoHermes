"""TUI UI 组件库。

合并了 ANSI 控制、面板、状态栏、工具显示等组件。
"""

from __future__ import annotations

import sys
import time
from typing import Any, List as typing_list

from rich.console import Console, RenderableType
from rich.text import Text


# ============================================================================
# ANSI 终端控制
# ============================================================================

ANSI_RESET = "\033[0m"
ANSI_CLEAR_SCREEN = "\033[2J"
ANSI_CLEAR_LINE = "\033[2K"
ANSI_HOME = "\033[H"

ANSI_COLORS = {
    "black": "\033[30m", "red": "\033[31m", "green": "\033[32m",
    "yellow": "\033[33m", "blue": "\033[34m", "magenta": "\033[35m",
    "cyan": "\033[36m", "white": "\033[37m", "bright_black": "\033[90m",
    "bright_red": "\033[91m", "bright_green": "\033[92m",
    "bright_yellow": "\033[93m", "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m", "bright_cyan": "\033[96m",
    "bright_white": "\033[97m",
}

ANSI_BG_COLORS = {
    "black": "\033[40m", "red": "\033[41m", "green": "\033[42m",
    "yellow": "\033[43m", "blue": "\033[44m", "magenta": "\033[45m",
    "cyan": "\033[46m", "white": "\033[47m",
}


def set_color(color_name: str, bright: bool = False) -> str:
    if bright:
        return ANSI_COLORS.get(f"bright_{color_name}", "")
    return ANSI_COLORS.get(color_name, "")


def set_bg_color(color_name: str) -> str:
    return ANSI_BG_COLORS.get(color_name, "")


def move_cursor(row: int, col: int) -> str:
    return f"\033[{row};{col}H"


def move_cursor_up(lines: int = 1) -> str:
    return f"\033[{lines}A"


def move_cursor_down(lines: int = 1) -> str:
    return f"\033[{lines}B"


def move_cursor_right(cols: int = 1) -> str:
    return f"\033[{cols}C"


def move_cursor_left(cols: int = 1) -> str:
    return f"\033[{cols}D"


def clear_screen() -> str:
    return ANSI_CLEAR_SCREEN + ANSI_HOME


def clear_line() -> str:
    return ANSI_CLEAR_LINE


def styled_text(text: str, color: str, bg_color: str | None = None, bold: bool = False) -> str:
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
    try:
        import shutil
        size = shutil.get_terminal_size(fallback=(80, 24))
        return size.columns, size.lines
    except Exception:
        return 80, 24


# ============================================================================
# 面板组件
# ============================================================================

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]

# Kawaii 表情动画帧
KAWAII_FACES = [
    "(◕‿◕)",  # 正常
    "(◕‿◕✿)",  # 开心
    "(◠‿◠✿)",  # 微笑
    "(◕ᴗ◕✿)",  # 可爱
    "(◕‿◕)♡",  # 爱心
    "(◠ᴗ◠✿)",  # 期待
    "(◕‿◕)✨",  # 闪亮
    "(◠‿◠)💫",  # 星星
]

KAWAII_WAITING = [
    "(◕‿◕) ...",
    "(◕_◕)  ...",
    "(◕‿◕)  ...",
    "(◕._.◕)...",
    "(◕‿◕) ...",
]

KAWAII_WORKING = [
    "(◕‿◕)⊃━☆ﾟ.*",
    "(◕‿◕)つ━☆・*。",
    "(◠‿◠)つ━☆・*。",
    "(◕ᴗ◕)⊃━☆ﾟ.*",
]

KAWAII_SUCCESS = [
    "(◕‿◕)✨ 完成!",
    "(◠‿◠✿) ✅",
    "(◕ᴗ◕✿) 🎉",
]

KAWAII_ERROR = [
    "(◕﹏◕) ❌",
    "(◕︵◕) 💥",
    "(◕︿◕) ⚠️",
]


class Panel:
    def __init__(self, title: str = "", border_color: str = "bright_black", title_color: str = "bright_blue"):
        self.title = title
        self.border_color = border_color
        self.title_color = title_color

    def render(self, content: str, width: int | None = None) -> str:
        if width is None:
            width, _ = get_terminal_size()
            width = min(width, 120)

        lines = content.split("\n")
        inner_width = width - 4
        result = []

        if self.title:
            title_text = f" {self.title} "
            result.append(styled_text(f"┌─{title_text}{'─' * (width - len(title_text) - 3)}┐", self.border_color))
        else:
            result.append(styled_text("┌" + "─" * (width - 2) + "┐", self.border_color))

        for line in lines:
            if len(line) > inner_width:
                line = line[:inner_width - 3] + "..."
            padded = line.ljust(inner_width)
            result.append(styled_text(f"│ {padded} │", self.border_color))

        result.append(styled_text("└" + "─" * (width - 2) + "┘", self.border_color))
        return "\n".join(result)


class Spinner:
    def __init__(self, message: str = "加载中...", color: str = "yellow"):
        self.message = message
        self.color = color
        self._frame_index = 0
        self._running = False

    def _get_frame(self) -> str:
        frame = SPINNER_FRAMES[self._frame_index % len(SPINNER_FRAMES)]
        self._frame_index += 1
        return styled_text(frame, self.color)

    def render(self) -> str:
        return f"{self._get_frame()} {self.message}"

    def animate(self, duration: float = 1.0, fps: int = 10) -> None:
        self._running = True
        start_time = time.time()
        while time.time() - start_time < duration:
            sys.stdout.write("\r" + self.render())
            sys.stdout.flush()
            time.sleep(1.0 / fps)
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()
        self._running = False


class KawaiiSpinner:
    """带动画表情的可爱 spinner，用于 API 调用时显示。"""

    def __init__(self, message: str = "思考中...", color: str = "cyan"):
        self.message = message
        self.color = color
        self._face_index = 0
        self._state = "waiting"  # waiting, working, success, error

    def _get_face(self) -> str:
        if self._state == "waiting":
            faces = KAWAII_WAITING
        elif self._state == "working":
            faces = KAWAII_WORKING
        elif self._state == "success":
            faces = KAWAII_SUCCESS
        elif self._state == "error":
            faces = KAWAII_ERROR
        else:
            faces = KAWAII_WAITING

        face = faces[self._face_index % len(faces)]
        self._face_index += 1
        return styled_text(face, self.color)

    def render(self) -> str:
        face = self._get_face()
        return f"{face} {self.message}"

    def animate(self, duration: float = 1.0, fps: int = 8) -> None:
        """动画显示指定时长。"""
        start_time = time.time()
        while time.time() - start_time < duration:
            sys.stdout.write("\r" + self.render())
            sys.stdout.flush()
            time.sleep(1.0 / fps)
        sys.stdout.write("\r" + " " * (len(self.message) + 20) + "\r")
        sys.stdout.flush()

    def set_state(self, state: str) -> None:
        """设置状态：waiting, working, success, error"""
        self._state = state
        self._face_index = 0

    def show_success(self) -> str:
        self._state = "success"
        face = self._get_face()
        return f"{face}"

    def show_error(self) -> str:
        self._state = "error"
        face = self._get_face()
        return f"{face}"


class ActivityFeed:
    """使用 ┊ 分隔符的活动流，显示工具调用状态。"""

    PREFIX = "┊"

    @staticmethod
    def format_start(tool_name: str, action: str = "") -> Text:
        action_text = f" {action}" if action else ""
        text = Text()
        text.append(f"{ActivityFeed.PREFIX} ")
        text.append("🟦", style="blue")
        text.append(f" preparing {tool_name}{action_text}...")
        return text

    @staticmethod
    def format_complete(tool_name: str, action: str = "", elapsed: float = 0.0) -> Text:
        action_text = f" {action}" if action else ""
        time_text = f" {elapsed:.1f}s" if elapsed > 0 else ""
        text = Text()
        text.append(f"{ActivityFeed.PREFIX} ")
        text.append("🟩", style="green")
        text.append(f" {tool_name}{action_text}{time_text}")
        return text

    @staticmethod
    def format_result(tool_name: str, summary: str) -> Text:
        icons = {
            "read_file": "📄",
            "write_file": "📝",
            "search_files": "🔍",
            "terminal": "💻",
            "glob": "📁",
            "grep": "🔎",
        }
        icon = icons.get(tool_name, "✅")
        text = Text()
        text.append(f"{ActivityFeed.PREFIX} ")
        text.append(f"{icon} {summary}")
        return text

    @staticmethod
    def format_error(tool_name: str, error: str = "") -> Text:
        error_text = f" - {error[:50]}" if error else ""
        text = Text()
        text.append(f"{ActivityFeed.PREFIX} ")
        text.append("🟥", style="red")
        text.append(f" {tool_name}{error_text}")
        return text


class ProgressBar:
    def __init__(self, total: int = 100, width: int = 40, color: str = "green"):
        self.total = total
        self.width = width
        self.color = color
        self.current = 0

    def update(self, value: int) -> str:
        self.current = min(value, self.total)
        percent = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percent)
        empty = self.width - filled
        bar = "█" * filled + "░" * empty
        percent_str = f"{percent * 100:.1f}%"
        return styled_text(f"[{bar}] {percent_str}", self.color)

    def render(self) -> str:
        return self.update(self.current)


# ============================================================================
# 状态栏组件
# ============================================================================

class StatusBar:
    def __init__(self, model: str = "", context_window: int = 1_000_000):
        self.model = model
        self.context_window = context_window
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost = 0.0
        self.elapsed_time = 0.0
        self.last_response_time = 0.0

    def update_tokens(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def update_cost(self, cost: float) -> None:
        self.cost += cost

    def update_time(self, elapsed: float) -> None:
        self.elapsed_time += elapsed
        self.last_response_time = elapsed

    def render(self) -> RenderableType:
        text = Text()
        text.append(f" {self.model} ", style="bold cyan")
        text.append("|")

        total_tokens = self.input_tokens + self.output_tokens
        usage_pct = (total_tokens / self.context_window * 100) if self.context_window > 0 else 0

        if usage_pct > 90:
            token_style = "bold red"
        elif usage_pct > 70:
            token_style = "bold yellow"
        else:
            token_style = "bold green"

        text.append(f" {total_tokens/1000:.1f}K/{self.context_window/1000:.0f}K ", style=token_style)
        text.append("|")

        bar_width = 10
        filled = int(usage_pct / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        text.append(f" [{bar}] {usage_pct:.0f}% ", style=token_style)
        text.append("|")

        if self.elapsed_time < 60:
            time_str = f"{self.elapsed_time:.0f}s"
        elif self.elapsed_time < 3600:
            time_str = f"{self.elapsed_time/60:.0f}m {self.elapsed_time%60:.0f}s"
        else:
            time_str = f"{self.elapsed_time/3600:.0f}h {self.elapsed_time%3600/60:.0f}m"

        text.append(f" {time_str} ", style="dim")
        text.append("|")
        text.append(f" {self.last_response_time:.1f}s ", style="dim")
        return text


# ============================================================================
# 工具调用显示
# ============================================================================

TOOL_STATUS_ICONS = {"start": "⏳", "running": "🔄", "success": "✅", "error": "❌"}
TOOL_STATUS_COLORS = {"start": "yellow", "running": "yellow", "success": "green", "error": "red"}


class ToolCallDisplay:
    def __init__(self):
        self.spinner = Spinner(message="执行中...", color="yellow")

    def render_start(self, tool_name: str, args: dict[str, Any] | None = None) -> str:
        icon = TOOL_STATUS_ICONS["start"]
        color = TOOL_STATUS_COLORS["start"]
        result = styled_text(f"{icon} {tool_name}", color, bold=True)
        if args:
            args_str = ", ".join(f"{k}={v}" for k, v in list(args.items())[:3])
            result += f" ({args_str})"
        return result

    def render_running(self, tool_name: str) -> str:
        icon = TOOL_STATUS_ICONS["running"]
        color = TOOL_STATUS_COLORS["running"]
        return styled_text(f"{icon} {tool_name} - 执行中...", color)

    def render_success(self, tool_name: str, result: str = "", summary: str = "") -> str:
        icon = TOOL_STATUS_ICONS["success"]
        color = TOOL_STATUS_COLORS["success"]
        text = f"{icon} {tool_name}"
        if summary:
            text += f" - {summary}"
        return styled_text(text, color)

    def render_error(self, tool_name: str, error: str = "") -> str:
        icon = TOOL_STATUS_ICONS["error"]
        color = TOOL_STATUS_COLORS["error"]
        text = f"{icon} {tool_name}"
        if error:
            text += f" - {error[:50]}"
        return styled_text(text, color, bold=True)


class ToolCallHistoryPanel:
    def __init__(self, max_display: int = 10):
        self.max_display = max_display
        self.display = ToolCallDisplay()

    def render(self, tool_calls: list) -> str:
        if not tool_calls:
            return styled_text("暂无工具调用记录", "bright_black")

        lines = []
        recent = tool_calls[-self.max_display:]

        for i, tc in enumerate(recent, 1):
            status = tc.status
            tool_name = tc.tool_name
            result = tc.result

            if status == "start":
                line = self.display.render_start(tool_name, tc.args)
            elif status == "running":
                line = self.display.render_running(tool_name)
            elif status == "success":
                summary = self._generate_summary(tool_name, result)
                line = self.display.render_success(tool_name, result, summary)
            elif status == "error":
                line = self.display.render_error(tool_name, result)
            else:
                line = f"❓ {tool_name} (未知状态)"

            lines.append(f"{i}. {line}")

        panel = Panel(title="工具调用历史")
        return panel.render("\n".join(lines))

    def _generate_summary(self, tool_name: str, result: str) -> str:
        if not result:
            return ""
        if tool_name == "read_file":
            lines = result.count("\n") + 1
            chars = len(result)
            return f"读取 {lines} 行，{chars} 字符"
        elif tool_name == "terminal":
            exit_code = "退出码: 0" if "exit code: 0" in result.lower() else "退出码: 非零"
            return exit_code
        elif tool_name == "search_files":
            count = result.count("\n") + 1
            return f"找到 {count} 个匹配"
        else:
            return result[:50] + "..." if len(result) > 50 else result


class ToolCallResultSummary:
    @staticmethod
    def generate(tool_name: str, result: str, max_length: int = 100) -> str:
        if not result:
            return "无结果"
        if len(result) > max_length:
            result = result[:max_length - 3] + "..."
        return result
