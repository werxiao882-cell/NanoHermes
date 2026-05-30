"""TUI 布局系统。

实现响应式布局、动态面板管理和窗口调整处理。
"""

from __future__ import annotations

import logging
import signal
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

from src.cli.widgets import get_terminal_size

logger = logging.getLogger(__name__)


@dataclass
class LayoutConfig:
    show_tool_panel: bool = True
    tool_panel_position: str = "right"
    min_width: int = 80
    min_height: int = 24
    panel_spacing: int = 2


class LayoutManager:
    def __init__(self, config: LayoutConfig | None = None):
        self.config = config or LayoutConfig()
        self._resize_handlers: list[Callable] = []
        self._current_width = 80
        self._current_height = 24

        if sys.platform != "win32":
            try:
                signal.signal(signal.SIGWINCH, self._handle_resize)
            except Exception as e:
                logger.warning(f"无法注册 SIGWINCH 处理: {e}")

    def _handle_resize(self, signum: int, frame) -> None:
        self._update_terminal_size()
        self._notify_resize_handlers()

    def _update_terminal_size(self) -> None:
        self._current_width, self._current_height = get_terminal_size()
        logger.debug(f"终端尺寸更新: {self._current_width}x{self._current_height}")

    def _notify_resize_handlers(self) -> None:
        for handler in self._resize_handlers:
            try:
                handler(self._current_width, self._current_height)
            except Exception as e:
                logger.warning(f"调整处理函数异常: {e}")

    def register_resize_handler(self, handler: Callable) -> None:
        self._resize_handlers.append(handler)

    def unregister_resize_handler(self, handler: Callable) -> None:
        if handler in self._resize_handlers:
            self._resize_handlers.remove(handler)

    def get_layout(self) -> dict[str, Any]:
        self._update_terminal_size()
        width = self._current_width
        height = self._current_height

        if width < self.config.min_width:
            logger.warning(f"终端宽度过小: {width} < {self.config.min_width}")
        if height < self.config.min_height:
            logger.warning(f"终端高度过小: {height} < {self.config.min_height}")

        if self.config.show_tool_panel:
            if self.config.tool_panel_position in ("left", "right"):
                panel_width = max(30, width // 3)
                main_width = width - panel_width - self.config.panel_spacing
                return {
                    "type": "vertical_split",
                    "width": width, "height": height,
                    "main": {"x": 0 if self.config.tool_panel_position == "left" else panel_width + self.config.panel_spacing, "y": 0, "width": main_width, "height": height},
                    "tool_panel": {"x": 0 if self.config.tool_panel_position == "right" else 0, "y": 0, "width": panel_width, "height": height},
                }
            else:
                panel_height = max(10, height // 3)
                main_height = height - panel_height - self.config.panel_spacing
                return {
                    "type": "horizontal_split",
                    "width": width, "height": height,
                    "main": {"x": 0, "y": 0, "width": width, "height": main_height},
                    "tool_panel": {"x": 0, "y": main_height + self.config.panel_spacing, "width": width, "height": panel_height},
                }
        else:
            return {
                "type": "fullscreen",
                "width": width, "height": height,
                "main": {"x": 0, "y": 0, "width": width, "height": height},
            }

    def check_min_size(self) -> tuple[bool, str]:
        self._update_terminal_size()
        warnings = []
        if self._current_width < self.config.min_width:
            warnings.append(f"宽度过小: {self._current_width} < {self.config.min_width}")
        if self._current_height < self.config.min_height:
            warnings.append(f"高度过小: {self._current_height} < {self.config.min_height}")
        if warnings:
            return False, "; ".join(warnings)
        return True, ""

    def update_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.debug(f"布局配置已更新: {key} = {value}")
            else:
                logger.warning(f"未知布局配置项: {key}")


class DynamicPanelManager:
    def __init__(self, layout_manager: LayoutManager):
        self.layout_manager = layout_manager
        self._panels: dict[str, dict[str, Any]] = {}

    def create_panel(self, panel_id: str, config: dict[str, Any]) -> None:
        self._panels[panel_id] = config
        logger.debug(f"面板已创建: {panel_id}")

    def destroy_panel(self, panel_id: str) -> None:
        if panel_id in self._panels:
            del self._panels[panel_id]
            logger.debug(f"面板已销毁: {panel_id}")

    def get_panel(self, panel_id: str) -> dict[str, Any] | None:
        return self._panels.get(panel_id)

    def list_panels(self) -> list[str]:
        return list(self._panels.keys())

    def rearrange_panels(self) -> None:
        layout = self.layout_manager.get_layout()
        logger.debug(f"面板已重排: {layout['type']}")
