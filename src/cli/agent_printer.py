"""Agent 列表和 transcript 打印器。

所有输出通过 console.print() 追加到终端滚动缓冲区。
不清屏，不做 Live 刷新。

设计理由：
- 当前架构是命令式追加模型，不支持原地替换
- 用 Rule 分隔符标记视图切换点
- 增量打印：跟踪 last_printed_index，只显示新消息
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.rule import Rule
from rich.text import Text

if TYPE_CHECKING:
    from src.cli.agent_task import AgentTask, AgentTaskRegistry


class AgentPrinter:
    """Agent 列表和 transcript 的打印器。

    三种输出场景：
    1. print_agent_list() — /agents 命令 或 ↑↓ 键
    2. print_transcript() — /agent <id> 命令（增量模式）
    3. format_toolbar() — bottom_toolbar 实时状态
    """

    STATUS_ICONS = {
        "pending": "◻",
        "running": "▶",
        "completed": "✓",
        "failed": "✗",
        "timeout": "⏱",
    }

    STATUS_STYLES = {
        "pending": "dim",
        "running": "yellow",
        "completed": "green",
        "failed": "red",
        "timeout": "red",
    }

    def __init__(self, registry: AgentTaskRegistry, console: Console) -> None:
        self._registry = registry
        self._console = console

    def print_agent_list(self) -> None:
        """打印 Agent 列表到滚动缓冲区。"""
        tasks = self._registry.get_all()
        if not tasks:
            self._console.print("[dim]没有子 Agent[/]")
            return

        text = Text()
        text.append("\n")
        text.append("── Agents ──\n", style="bold yellow")

        # main 行
        text.append("  ○ main\n", style="bold")

        # 各 Agent 行
        for task in tasks:
            icon = self.STATUS_ICONS.get(task.status.value, "?")
            style = self.STATUS_STYLES.get(task.status.value, "dim")
            elapsed = task.format_duration()

            tokens = ""
            if task.progress.token_count > 0:
                tokens = f" · {task.progress.token_count / 1000:.1f}k tok"

            desc = task.progress.last_activity or task.description
            if len(desc) > 40:
                desc = desc[:37] + "..."

            text.append(f"  {icon} ", style=style)
            text.append(f"{task.id} ", style="bold")
            text.append(f"{task.name}: {desc}", style="")
            text.append(f" {icon} {elapsed}{tokens}\n", style="dim")

        text.append("[dim]  /agent <id> 查看 transcript[/]")
        self._console.print(text)

    def print_transcript(self, task_id_or_name: str) -> None:
        """打印 Agent transcript（增量模式）。

        首次查看：Rule 分隔符 + 全部消息
        再次查看："── N new messages ──" + 仅新增消息
        """
        # 查找任务（先精确 ID，再名称/前缀匹配）
        task = self._registry.get(task_id_or_name)
        if not task:
            task = self._registry.get_by_name(task_id_or_name)
        if not task:
            self._console.print(f"[red]Agent '{task_id_or_name}' 不存在[/]")
            return

        # 获取增量消息（原子操作，自动更新 last_printed_index）
        new_messages, new_count = self._registry.get_new_messages(task.id)

        # 首次查看：打印标题分隔符
        if task.last_printed_index == new_count:
            # last_printed_index 刚被 get_new_messages 更新为 len(messages)
            # 如果 new_count == len(messages)，说明是首次
            status_icon = self.STATUS_ICONS.get(task.status.value, "?")
            elapsed = task.format_duration()
            title = f" {status_icon} {task.name} ({task.id}) · {elapsed} "
            self._console.print(Rule(title=title, style="bold cyan"))

        # 无新消息
        if not new_messages:
            if task.last_printed_index > 0:
                self._console.print("[dim]  (无新消息)[/]")
            else:
                self._console.print("[dim]  (暂无消息)[/]")
                if task.is_terminal:
                    self._console.print(Rule(style="dim"))
            return

        # 再次查看时的增量分隔符
        if task.last_printed_index > new_count:
            self._console.print(
                f"[dim]── {new_count} new messages ──[/]"
            )

        # 打印消息
        self._print_messages(new_messages)

        # 如果 Agent 已完成且所有消息已打印，打印结束分隔符
        if task.is_terminal:
            self._console.print(Rule(style="dim"))

    def _print_messages(self, messages: list[dict]) -> None:
        """打印消息列表。"""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                self._console.print(f"  [cyan]> {content}[/]")
            elif role == "assistant":
                if content:
                    self._console.print(f"  {content}")
            elif role == "tool":
                metadata = msg.get("metadata", {})
                tool_name = metadata.get("tool_name", "")
                tool_status = metadata.get("status", "")
                if tool_status == "start":
                    self._console.print(f"  [yellow]🔧 {tool_name}(...)[/]")
                elif tool_status == "end":
                    self._console.print(f"  [green]✓ {tool_name}[/]")
            elif role == "system":
                self._console.print(f"  [dim italic]⚡ {content}[/]")

    def print_switch_view(self, selected_index: int) -> None:
        """打印 Agent 切换视图（↑↓ 键触发）。

        显示紧凑的 Agent 列表（高亮选中项）+ 选中 Agent 的增量 transcript。

        Args:
            selected_index: 选中的索引。0=main, 1..N=子 Agent。
        """
        tasks = self._registry.get_all()
        if not tasks:
            return

        # ── 打印紧凑 Agent 列表 ──
        text = Text()
        text.append("  ", style="dim")

        # main 行
        if selected_index == 0:
            text.append("[main]", style="bold reverse")
        else:
            text.append(" main ", style="dim")

        # 各 Agent 行
        for i, task in enumerate(tasks, 1):
            icon = self.STATUS_ICONS.get(task.status.value, "?")
            style = self.STATUS_STYLES.get(task.status.value, "dim")
            label = f"{task.name}({task.id})"

            if i == selected_index:
                text.append(f"  {icon} [{label}]", style=f"bold {style} reverse")
            else:
                text.append(f"  {icon} {label}", style=style)

        text.append("  ", style="dim")
        text.append("↑↓切换 Enter返回", style="dim italic")
        self._console.print(text)

        # ── 打印选中 Agent 的增量 transcript ──
        if selected_index == 0:
            # 选中 main：不做额外打印（主对话已在屏幕上）
            return

        if selected_index <= len(tasks):
            task = tasks[selected_index - 1]
            new_messages, new_count = self._registry.get_new_messages(task.id)

            if not new_messages:
                self._console.print(f"  [dim]({task.name}: 无新消息)[/]")
                return

            # 紧凑分隔符
            self._console.print(
                f"  [cyan]── {task.name}({task.id}) "
                f"{new_count} msgs ──[/]"
            )
            self._print_messages(new_messages)

    def format_toolbar(self) -> str:
        """生成 bottom_toolbar HTML（prompt_toolkit 格式）。

        每次 PromptSession 渲染输入框时自动调用。
        无运行中子 Agent 时返回空字符串（隐藏 toolbar）。
        """
        tasks = self._registry.get_all_running()
        if not tasks:
            return ""

        lines = []
        for task in tasks:
            icon = "▶" if task.is_running else "⏸"
            elapsed = task.format_duration()
            activity = task.progress.last_activity or task.description
            if len(activity) > 35:
                activity = activity[:32] + "..."
            tokens = ""
            if task.progress.token_count > 0:
                tokens = f" {task.progress.token_count / 1000:.1f}k"

            lines.append(
                f"  {icon} <b>{task.id}</b>: {activity}"
                f"  <i>{elapsed}{tokens}</i>"
            )

        return "\n".join(lines)
