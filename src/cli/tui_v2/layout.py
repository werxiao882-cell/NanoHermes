"""TUI 布局系统。

实现响应式布局、动态面板管理和窗口调整处理。
"""

from __future__ import annotations

import logging
import signal
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

from src.cli.tui_v2.utils.ansi import get_terminal_size

logger = logging.getLogger(__name__)


@dataclass
class LayoutConfig:
    """布局配置。
    
    Attributes:
        show_tool_panel: 是否显示工具面板。
        tool_panel_position: 工具面板位置（left/right/bottom）。
        min_width: 最小宽度。
        min_height: 最小高度。
        panel_spacing: 面板间距。
    """
    show_tool_panel: bool = True
    tool_panel_position: str = "right"
    min_width: int = 80
    min_height: int = 24
    panel_spacing: int = 2


class LayoutManager:
    """布局管理器。
    
    管理 TUI 布局，支持响应式调整和动态面板管理。
    """
    
    def __init__(self, config: LayoutConfig | None = None):
        """初始化布局管理器。
        
        Args:
            config: 布局配置。
        """
        self.config = config or LayoutConfig()
        self._resize_handlers: list[Callable] = []
        self._current_width = 80
        self._current_height = 24
        
        # 注册窗口调整信号处理（仅 Unix）
        if sys.platform != "win32":
            try:
                signal.signal(signal.SIGWINCH, self._handle_resize)
            except Exception as e:
                logger.warning(f"无法注册 SIGWINCH 处理: {e}")
    
    def _handle_resize(self, signum: int, frame) -> None:
        """处理窗口调整事件。
        
        Args:
            signum: 信号编号。
            frame: 帧。
        """
        self._update_terminal_size()
        self._notify_resize_handlers()
    
    def _update_terminal_size(self) -> None:
        """更新终端尺寸。"""
        self._current_width, self._current_height = get_terminal_size()
        logger.debug(f"终端尺寸更新: {self._current_width}x{self._current_height}")
    
    def _notify_resize_handlers(self) -> None:
        """通知所有注册的处理函数。"""
        for handler in self._resize_handlers:
            try:
                handler(self._current_width, self._current_height)
            except Exception as e:
                logger.warning(f"调整处理函数异常: {e}")
    
    def register_resize_handler(self, handler: Callable) -> None:
        """注册调整大小处理函数。
        
        Args:
            handler: 处理函数，接受 (width, height) 参数。
        """
        self._resize_handlers.append(handler)
    
    def unregister_resize_handler(self, handler: Callable) -> None:
        """注销调整大小处理函数。
        
        Args:
            handler: 要注销的处理函数。
        """
        if handler in self._resize_handlers:
            self._resize_handlers.remove(handler)
    
    def get_layout(self) -> dict[str, Any]:
        """获取当前布局信息。
        
        Returns:
            布局信息字典。
        """
        self._update_terminal_size()
        
        width = self._current_width
        height = self._current_height
        
        # 检查最小尺寸
        if width < self.config.min_width:
            logger.warning(f"终端宽度过小: {width} < {self.config.min_width}")
        if height < self.config.min_height:
            logger.warning(f"终端高度过小: {height} < {self.config.min_height}")
        
        # 计算面板尺寸
        if self.config.show_tool_panel:
            if self.config.tool_panel_position in ("left", "right"):
                # 垂直分割
                panel_width = max(30, width // 3)
                main_width = width - panel_width - self.config.panel_spacing
                return {
                    "type": "vertical_split",
                    "width": width,
                    "height": height,
                    "main": {"x": 0 if self.config.tool_panel_position == "left" else panel_width + self.config.panel_spacing, "y": 0, "width": main_width, "height": height},
                    "tool_panel": {"x": 0 if self.config.tool_panel_position == "right" else 0, "y": 0, "width": panel_width, "height": height},
                }
            else:
                # 水平分割（底部）
                panel_height = max(10, height // 3)
                main_height = height - panel_height - self.config.panel_spacing
                return {
                    "type": "horizontal_split",
                    "width": width,
                    "height": height,
                    "main": {"x": 0, "y": 0, "width": width, "height": main_height},
                    "tool_panel": {"x": 0, "y": main_height + self.config.panel_spacing, "width": width, "height": panel_height},
                }
        else:
            # 无面板，全屏主区域
            return {
                "type": "fullscreen",
                "width": width,
                "height": height,
                "main": {"x": 0, "y": 0, "width": width, "height": height},
            }
    
    def check_min_size(self) -> tuple[bool, str]:
        """检查最小尺寸。
        
        Returns:
            (是否满足最小尺寸, 警告消息) 元组。
        """
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
        """更新布局配置。
        
        Args:
            **kwargs: 配置项。
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.debug(f"布局配置已更新: {key} = {value}")
            else:
                logger.warning(f"未知布局配置项: {key}")


class DynamicPanelManager:
    """动态面板管理器。
    
    管理面板的创建、销毁和重排。
    """
    
    def __init__(self, layout_manager: LayoutManager):
        """初始化动态面板管理器。
        
        Args:
            layout_manager: 布局管理器。
        """
        self.layout_manager = layout_manager
        self._panels: dict[str, dict[str, Any]] = {}
    
    def create_panel(self, panel_id: str, config: dict[str, Any]) -> None:
        """创建面板。
        
        Args:
            panel_id: 面板 ID。
            config: 面板配置。
        """
        self._panels[panel_id] = config
        logger.debug(f"面板已创建: {panel_id}")
    
    def destroy_panel(self, panel_id: str) -> None:
        """销毁面板。
        
        Args:
            panel_id: 面板 ID。
        """
        if panel_id in self._panels:
            del self._panels[panel_id]
            logger.debug(f"面板已销毁: {panel_id}")
    
    def get_panel(self, panel_id: str) -> dict[str, Any] | None:
        """获取面板配置。
        
        Args:
            panel_id: 面板 ID。
            
        Returns:
            面板配置，如果不存在则返回 None。
        """
        return self._panels.get(panel_id)
    
    def list_panels(self) -> list[str]:
        """列出所有面板 ID。
        
        Returns:
            面板 ID 列表。
        """
        return list(self._panels.keys())
    
    def rearrange_panels(self) -> None:
        """重排面板。
        
        根据当前终端尺寸重新排列面板。
        """
        layout = self.layout_manager.get_layout()
        logger.debug(f"面板已重排: {layout['type']}")
