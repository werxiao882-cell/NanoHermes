"""TUIEventHandler - TUI 事件处理系统。

处理用户输入、系统消息和工具调用事件。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.cli.tui_v2.state import TUIState

logger = logging.getLogger(__name__)


class TUIEventHandler:
    """TUI 事件处理器。
    
    处理所有 TUI 事件，包括用户输入、系统消息和工具调用。
    
    Attributes:
        state: TUI 状态管理器。
        pending_clarification: 待处理的澄清问题。
    """
    
    def __init__(self, state: TUIState):
        """初始化事件处理器。
        
        Args:
            state: TUI 状态管理器。
        """
        self.state = state
        self.pending_clarification: dict[str, Any] | None = None
    
    async def handle_user_input(self, user_input: str) -> None:
        """处理用户输入事件。
        
        Args:
            user_input: 用户输入的文本。
        """
        # 添加到历史记录
        self.state.input_history.append(user_input)
        
        # 检查是否是命令
        if user_input.startswith("/"):
            await self._handle_command(user_input)
            return
        
        # 检查是否有待处理的澄清
        if self.pending_clarification:
            await self._handle_clarification_response(user_input)
            return
        
        # 普通消息：发送到对话引擎
        await self._send_message(user_input)
    
    async def _handle_command(self, command: str) -> None:
        """处理斜杠命令。
        
        Args:
            command: 命令字符串（如 /help）。
        """
        parts = command.split()
        cmd = parts[0].lower()
        
        commands = {
            "/help": self._cmd_help,
            "/clear": self._cmd_clear,
            "/quit": self._cmd_quit,
            "/resume": self._cmd_resume,
            "/status": self._cmd_status,
            "/tools": self._cmd_tools,
        }
        
        handler = commands.get(cmd)
        if handler:
            await handler(parts[1:])
        else:
            print(f"未知命令: {cmd}。输入 /help 查看可用命令。")
    
    async def _cmd_help(self, args: list[str]) -> None:
        """显示帮助信息。"""
        print("""
可用命令：
  /help          - 显示此帮助信息
  /clear         - 清空屏幕
  /quit          - 退出 TUI
  /resume [id]   - 恢复会话
  /status        - 显示当前状态
  /tools         - 显示工具调用历史

快捷键：
  Enter          - 发送消息
  Ctrl+D         - 退出
  Ctrl+C         - 中断
  Ctrl+U         - 清空输入
  Shift+Enter    - 换行
""")
    
    async def _cmd_clear(self, args: list[str]) -> None:
        """清空屏幕。"""
        # ANSI 清屏码
        print("\033[2J\033[H", end="")
    
    async def _cmd_quit(self, args: list[str]) -> None:
        """退出 TUI。"""
        self.state.running = False
    
    async def _cmd_resume(self, args: list[str]) -> None:
        """恢复会话。"""
        if args:
            session_id = args[0]
            self.state.session_id = session_id
            print(f"已恢复到会话 {session_id}")
        else:
            print("用法: /resume <session_id>")
    
    async def _cmd_status(self, args: list[str]) -> None:
        """显示当前状态。"""
        print(f"会话 ID: {self.state.session_id or '无'}")
        print(f"加载状态: {'加载中...' if self.state.loading else '就绪'}")
        print(f"工具调用次数: {len(self.state.tool_calls)}")
        print(f"输入历史: {len(self.state.input_history)} 条")
    
    async def _cmd_tools(self, args: list[str]) -> None:
        """显示工具调用历史。"""
        if not self.state.tool_calls:
            print("暂无工具调用记录。")
            return
        
        print("\n工具调用历史:")
        for i, tc in enumerate(self.state.tool_calls[-10:], 1):  # 最近 10 条
            status_icon = {"start": "⏳", "running": "🔄", "success": "✅", "error": "❌"}.get(tc.status, "❓")
            print(f"  {i}. {status_icon} {tc.tool_name} ({tc.status})")
            if tc.result:
                print(f"     结果: {tc.result[:100]}...")
        print()
    
    async def _handle_clarification_response(self, response: str) -> None:
        """处理澄清问题的回复。
        
        Args:
            response: 用户回复。
        """
        if self.pending_clarification:
            question_id = self.pending_clarification.get("id")
            logger.info(f"澄清问题 {question_id} 已回复: {response}")
            self.pending_clarification = None
    
    async def _send_message(self, message: str) -> None:
        """发送消息到对话引擎。
        
        Args:
            message: 消息内容。
        """
        self.state.loading = True
        logger.info(f"发送消息: {message[:50]}...")
        
        # 这里会集成到实际的对话引擎
        # 当前只是模拟
        print(f"\n🤔 思考中: {message[:80]}...\n")
        
        # 模拟处理延迟
        import asyncio
        await asyncio.sleep(0.5)
        
        self.state.loading = False
        print("✅ 响应就绪（模拟）\n")
    
    def handle_interrupt(self) -> None:
        """处理中断事件（Ctrl+C）。"""
        logger.info("用户中断当前操作")
        self.state.loading = False
        print("\n⚠️  已中断操作\n")
    
    def handle_tool_call_start(self, tool_name: str, args: dict[str, Any]) -> int:
        """处理工具调用开始事件。
        
        Args:
            tool_name: 工具名称。
            args: 工具参数。
            
        Returns:
            工具调用记录索引。
        """
        index = len(self.state.tool_calls)
        self.state.add_tool_call(tool_name, args)
        logger.info(f"工具调用开始: {tool_name}")
        return index
    
    def handle_tool_call_complete(self, index: int, success: bool, result: str) -> None:
        """处理工具调用完成事件。
        
        Args:
            index: 工具调用记录索引。
            success: 是否成功。
            result: 工具结果。
        """
        status = "success" if success else "error"
        self.state.update_tool_call(index, status, result)
        logger.info(f"工具调用完成: {self.state.tool_calls[index].tool_name} ({status})")
    
    def cleanup(self) -> None:
        """清理事件处理器资源。"""
        self.pending_clarification = None
        logger.info("事件处理器已清理")
