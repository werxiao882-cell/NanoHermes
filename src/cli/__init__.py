"""CLI 模块 - NanoHermes 终端界面。

仅支持 TUI v2 现代化终端界面。
"""

from src.cli.tui import TUIApp, create_tui_v2
from src.cli.state import TUIState, ToolCallRecord
from src.cli.event_handler import TUIEventHandler
from src.cli.completers import ContextAwareCompleter, CommandCompleter, FilePathCompleter
from src.cli.history import TUIHistory
from src.cli.streaming import TypewriterEffect, StreamingMarkdown, StreamingStatusIndicator
from src.cli.layout import LayoutManager, LayoutConfig, DynamicPanelManager
from src.cli.widgets import (
    StatusBar, Panel, Spinner, KawaiiSpinner, ProgressBar,
    ToolCallDisplay, ToolCallHistoryPanel, ToolCallResultSummary,
    ActivityFeed,
    styled_text, get_terminal_size, clear_screen, clear_line,
    set_color, set_bg_color, move_cursor,
    ANSI_RESET, ANSI_COLORS,
)

__all__ = [
    "TUIApp", "create_tui_v2",
    "TUIState", "ToolCallRecord",
    "TUIEventHandler",
    "ContextAwareCompleter", "CommandCompleter", "FilePathCompleter",
    "TUIHistory",
    "TypewriterEffect", "StreamingMarkdown", "StreamingStatusIndicator",
    "LayoutManager", "LayoutConfig", "DynamicPanelManager",
    "StatusBar", "Panel", "Spinner", "KawaiiSpinner", "ProgressBar",
    "ToolCallDisplay", "ToolCallHistoryPanel", "ToolCallResultSummary",
    "ActivityFeed",
    "styled_text", "get_terminal_size", "clear_screen", "clear_line",
    "set_color", "set_bg_color", "move_cursor",
    "ANSI_RESET", "ANSI_COLORS",
]
