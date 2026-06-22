"""AgentPrinter 单元测试。

测试覆盖：
- print_agent_list() 空列表 / 多 Agent 列表
- print_transcript() 首次 / 增量 / 无新消息
- format_toolbar() 无任务 / 有任务
"""

import io
import time

from rich.console import Console

from src.cli.agent_printer import AgentPrinter
from src.cli.agent_task import AgentTaskRegistry, AgentTaskStatus


def _make_console() -> Console:
    """创建内存 Console 用于测试。"""
    return Console(file=io.StringIO(), force_terminal=True, width=120)


def _get_output(console: Console) -> str:
    """获取 Console 输出内容。"""
    console.file.seek(0)
    return console.file.read()


# ============================================================================
# print_agent_list 测试
# ============================================================================

class TestPrintAgentList:
    def test_empty_list(self):
        registry = AgentTaskRegistry()
        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_agent_list()
        output = _get_output(console)
        assert "没有子 Agent" in output

    def test_single_agent(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth module")
        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_agent_list()
        output = _get_output(console)
        assert "Agents" in output
        assert "main" in output
        assert "a1b2" in output
        assert "auth-refactor" in output

    def test_multiple_agents(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth module")
        registry.register("c3d4", "test-gen", "Generate tests")
        registry.update_status("c3d4", AgentTaskStatus.COMPLETED)
        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_agent_list()
        output = _get_output(console)
        assert "a1b2" in output
        assert "c3d4" in output
        assert "/agent <id>" in output


# ============================================================================
# print_transcript 测试
# ============================================================================

class TestPrintTranscript:
    def test_nonexistent_agent(self):
        registry = AgentTaskRegistry()
        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_transcript("nonexistent")
        output = _get_output(console)
        assert "不存在" in output

    def test_first_view_with_messages(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        registry.append_message("a1b2", {"role": "user", "content": "refactor auth"})
        registry.append_message("a1b2", {"role": "assistant", "content": "Working on it"})

        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_transcript("a1b2")
        output = _get_output(console)
        assert "auth-refactor" in output
        assert "refactor auth" in output
        assert "Working on it" in output

    def test_first_view_empty(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")

        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_transcript("a1b2")
        output = _get_output(console)
        assert "暂无消息" in output

    def test_incremental_view(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        registry.append_message("a1b2", {"role": "user", "content": "msg1"})
        registry.append_message("a1b2", {"role": "assistant", "content": "msg2"})

        console = _make_console()
        printer = AgentPrinter(registry, console)

        # 首次查看
        printer.print_transcript("a1b2")
        output1 = _get_output(console)
        assert "msg1" in output1
        assert "msg2" in output1

        # 追加新消息
        registry.append_message("a1b2", {"role": "tool", "content": "", "metadata": {"tool_name": "read_file", "status": "start"}})
        registry.append_message("a1b2", {"role": "assistant", "content": "msg4"})

        # 再次查看（清掉之前的输出）
        console2 = _make_console()
        printer2 = AgentPrinter(registry, console2)
        printer2.print_transcript("a1b2")
        output2 = _get_output(console2)
        assert "new messages" in output2
        assert "msg4" in output2

    def test_no_new_messages(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        registry.append_message("a1b2", {"role": "user", "content": "msg1"})

        console = _make_console()
        printer = AgentPrinter(registry, console)

        # 首次查看
        printer.print_transcript("a1b2")

        # 再次查看（无新消息）
        console2 = _make_console()
        printer2 = AgentPrinter(registry, console2)
        printer2.print_transcript("a1b2")
        output2 = _get_output(console2)
        assert "无新消息" in output2

    def test_completed_agent_shows_end_rule(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        registry.update_status("a1b2", AgentTaskStatus.COMPLETED)
        registry.append_message("a1b2", {"role": "assistant", "content": "Done"})

        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_transcript("a1b2")
        output = _get_output(console)
        assert "Done" in output


# ============================================================================
# format_toolbar 测试
# ============================================================================

class TestFormatToolbar:
    def test_no_tasks(self):
        registry = AgentTaskRegistry()
        console = _make_console()
        printer = AgentPrinter(registry, console)

        result = printer.format_toolbar()
        assert result == ""

    def test_no_running_tasks(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        registry.update_status("a1b2", AgentTaskStatus.COMPLETED)
        console = _make_console()
        printer = AgentPrinter(registry, console)

        result = printer.format_toolbar()
        assert result == ""

    def test_with_running_tasks(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        registry.update_progress("a1b2", last_activity="patching auth.py", token_count=5200)

        console = _make_console()
        printer = AgentPrinter(registry, console)

        result = printer.format_toolbar()
        assert "a1b2" in result
        assert "patching auth.py" in result
        assert "5.2k" in result

    def test_multiple_running_tasks(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        registry.register("c3d4", "test-gen", "Generate tests")

        console = _make_console()
        printer = AgentPrinter(registry, console)

        result = printer.format_toolbar()
        assert "a1b2" in result
        assert "c3d4" in result

    def test_long_activity_truncated(self):
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "A" * 100)

        console = _make_console()
        printer = AgentPrinter(registry, console)

        result = printer.format_toolbar()
        assert "..." in result


# ============================================================================
# print_switch_view 测试
# ============================================================================

class TestPrintSwitchView:
    def test_no_tasks(self):
        """无子 Agent 时不输出。"""
        registry = AgentTaskRegistry()
        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_switch_view(0)
        output = _get_output(console)
        assert output == ""

    def test_select_main(self):
        """选中 main（index 0）。"""
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_switch_view(0)
        output = _get_output(console)
        assert "[main]" in output
        assert "auth-refactor" in output
        assert "↑↓切换" in output

    def test_select_child_agent(self):
        """选中子 Agent（index 1）。"""
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        registry.append_message("a1b2", {"role": "assistant", "content": "Working on it"})
        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_switch_view(1)
        output = _get_output(console)
        assert "auth-refactor" in output
        assert "msgs" in output
        assert "Working on it" in output

    def test_select_child_no_new_messages(self):
        """选中子 Agent 但无新消息。"""
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        console = _make_console()
        printer = AgentPrinter(registry, console)

        printer.print_switch_view(1)
        output = _get_output(console)
        assert "无新消息" in output

    def test_cycle_through_agents(self):
        """循环切换多个 Agent。"""
        registry = AgentTaskRegistry()
        registry.register("a1b2", "auth-refactor", "Refactor auth")
        registry.register("c3d4", "test-gen", "Generate tests")
        registry.append_message("a1b2", {"role": "assistant", "content": "auth msg"})
        registry.append_message("c3d4", {"role": "assistant", "content": "test msg"})

        console1 = _make_console()
        printer1 = AgentPrinter(registry, console1)
        printer1.print_switch_view(1)
        output1 = _get_output(console1)
        assert "auth msg" in output1

        console2 = _make_console()
        printer2 = AgentPrinter(registry, console2)
        printer2.print_switch_view(2)
        output2 = _get_output(console2)
        assert "test msg" in output2
