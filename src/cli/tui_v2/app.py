"""TUIApp - TUI 主类。

封装 prompt_toolkit 应用会话，管理 TUI 生命周期。
"""

from __future__ import annotations

import logging
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from src.cli.tui_v2.state import TUIState
from src.cli.tui_v2.event_handler import TUIEventHandler
from src.cli.tui_v2.layout import LayoutManager, LayoutConfig
from src.cli.tui_v2.completers import ContextAwareCompleter
from src.cli.tui_v2.history import TUIHistory

logger = logging.getLogger(__name__)


class TUIApp:
    """TUI 主应用类。
    
    封装 prompt_toolkit 应用会话，管理 TUI 生命周期。
    
    Attributes:
        state: TUI 状态管理器。
        event_handler: 事件处理器。
        session: prompt_toolkit 会话。
        application: prompt_toolkit 应用。
        key_bindings: 键盘绑定。
        style: TUI 样式。
    """
    
    def __init__(self, config: dict[str, Any] | None = None):
        """初始化 TUI 应用。
        
        Args:
            config: TUI 配置选项。
        """
        self.config = config or {}
        self.state = TUIState()
        self.event_handler = TUIEventHandler(self.state)
        
        # 初始化布局管理器
        layout_config = LayoutConfig(
            show_tool_panel=self.config.get("show_tool_panel", True),
            tool_panel_position=self.config.get("tool_panel_position", "right"),
        )
        self.layout_manager = LayoutManager(layout_config)
        
        # 初始化 prompt_toolkit 组件
        self.key_bindings = self._create_key_bindings()
        self.style = self._create_style()
        self.completer = ContextAwareCompleter()
        self.history = TUIHistory()
        self.session = PromptSession(
            key_bindings=self.key_bindings,
            style=self.style,
            completer=self.completer,
            history=self.history,
        )
        self.application: Application | None = None
        
        logger.info("TUIApp 初始化完成")
    
    def _create_key_bindings(self) -> KeyBindings:
        """创建键盘绑定。
        
        Returns:
            KeyBindings 实例。
        """
        bindings = KeyBindings()
        
        # Ctrl+D: 退出
        @bindings.add("c-d")
        def _(event):
            """退出 TUI。"""
            self.state.running = False
            event.app.exit()
        
        # Ctrl+C: 中断当前操作并退出
        @bindings.add("c-c")
        def _(event):
            """中断当前操作并退出 TUI。"""
            self.event_handler.handle_interrupt()
            self.state.running = False
            event.app.exit()
        
        return bindings
    
    def _create_style(self) -> Style:
        """创建 TUI 样式。
        
        Returns:
            Style 实例。
        """
        return Style.from_dict({
            # 输入框
            "input": "#00ff00",
            "input.placeholder": "#006600",
            
            # 消息
            "user.message": "#00aaff",
            "assistant.message": "#ffffff",
            "system.message": "#888888",
            
            # 工具
            "tool.start": "#ffaa00",
            "tool.running": "#ffaa00",
            "tool.success": "#00ff00",
            "tool.error": "#ff0000",
            
            # 状态
            "status.loading": "#ffaa00",
            "status.ready": "#00ff00",
            
            # 面板
            "panel.border": "#444444",
            "panel.title": "#00aaff",
        })
    
    async def run(self) -> None:
        """运行 TUI 主循环。
        
        进入主循环，监听用户输入和系统事件。
        """
        self.state.running = True
        logger.info("TUI 主循环启动")
        
        try:
            while self.state.running:
                # 显示欢迎消息
                if not self.state.welcomed:
                    self._show_welcome_message()
                    self.state.welcomed = True
                
                # 获取用户输入
                try:
                    user_input = await self.session.prompt_async()
                except EOFError:
                    # Ctrl+D 触发
                    self.state.running = False
                    break
                except KeyboardInterrupt:
                    # Ctrl+C 触发
                    continue
                
                # 处理用户输入
                if user_input:
                    await self.event_handler.handle_user_input(user_input.strip())
                
        except Exception as e:
            logger.error(f"TUI 主循环异常: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()
    
    def _show_welcome_message(self) -> None:
        """显示欢迎消息。"""
        print("\n🤖 NanoHermes TUI v2 - 现代化终端界面")
        print("输入 /help 查看可用命令，Ctrl+D 退出\n")
    
    async def shutdown(self) -> None:
        """优雅退出 TUI。
        
        保存会话状态，清理资源。
        """
        logger.info("TUI 正在关闭...")
        self.state.running = False
        
        # 保存状态
        self.state.save()
        
        # 清理资源
        self.event_handler.cleanup()
        
        logger.info("TUI 已关闭")
