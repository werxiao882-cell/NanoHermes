## 上下文

当前 NanoHermes TUI 使用 `prompt_toolkit.PromptSession` 处理输入 + `rich.Console.print()` 处理输出。这是**命令式追加模型**：内容追加到终端滚动缓冲区，已打印的内容无法原地替换。

Claude Code 使用 Ink（React for CLI），是声明式渲染模型，可以 re-render 特定区域。NanoHermes 无法直接复制这个模式。

因此采用 **滚动 + 分隔符** 方案：
- 所有输出通过 `console.print()` 追加
- 视图切换 = 打印分隔符 + 新内容
- 终端滚动保留完整历史

## 目标 / 非目标

**目标：**
- 子 Agent 后台运行，主对话不阻塞
- `/agents` 命令打印 Agent 列表
- `/agent <id>` 命令打印该 Agent 的 transcript
- ↑↓ 键打印 Agent 列表摘要，Enter 打印 transcript
- task-notification 回流结果到主 Agent

**非目标：**
- 不做清屏重绘（丢失历史）
- 不做 Rich Live 实时更新（与 prompt_toolkit 冲突风险高）
- 不做多面板分割布局

## 技术方案

### 0. 实时状态栏（bottom_toolbar）

在主视图中，使用 prompt_toolkit 的 `bottom_toolbar` 始终显示子 Agent 状态。
这是唯一既不影响滚动历史、又能实时更新的内置机制。

```python
# src/cli/tui.py - 修改 PromptSession

from prompt_toolkit.formatted_text import HTML

def _get_agent_toolbar(self) -> str:
    """生成 bottom_toolbar 内容（每次渲染 prompt 时自动调用）。"""
    tasks = self._task_registry.get_all_running()
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

    return HTML("\n".join(lines))


# 在 PromptSession 中使用
self.session = PromptSession(
    bottom_toolbar=lambda: self._get_agent_toolbar(),
    ...
)
```

**效果**：当有运行中的子 Agent 时，输入框上方始终显示实时状态条。
无子 Agent 时自动隐藏。prompt_toolkit 每次渲染输入框时自动刷新 toolbar。

### 1. AgentTask 状态模型 (`src/cli/agent_task.py`)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time
import threading


class AgentTaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AgentTaskProgress:
    token_count: int = 0
    tool_calls: int = 0
    last_activity: str = ""
    last_activity_time: float = 0.0


@dataclass
class AgentTask:
    """单个子 Agent 的任务状态。"""
    id: str
    name: str
    description: str
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    progress: AgentTaskProgress = field(default_factory=AgentTaskProgress)
    messages: list[dict[str, Any]] = field(default_factory=list)
    abort_event: threading.Event = field(default_factory=threading.Event)
    # 增量打印：记录上次打印到的位置
    last_printed_index: int = 0

    @property
    def is_running(self) -> bool:
        return self.status == AgentTaskStatus.RUNNING

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            AgentTaskStatus.COMPLETED,
            AgentTaskStatus.FAILED,
            AgentTaskStatus.TIMEOUT,
        )

    def format_duration(self) -> str:
        end = self.end_time or time.time()
        seconds = int(max(0, end - self.start_time))
        if seconds < 60:
            return f"{seconds}s"
        return f"{seconds // 60}m{seconds % 60}s"


class AgentTaskRegistry:
    """线程安全的 Agent 任务注册表。"""

    def __init__(self):
        self._tasks: dict[str, AgentTask] = {}
        self._lock = threading.Lock()

    def register(self, task_id: str, name: str, description: str) -> AgentTask:
        task = AgentTask(
            id=task_id, name=name,
            description=description[:80],
            status=AgentTaskStatus.RUNNING,
        )
        with self._lock:
            self._tasks[task_id] = task
        return task

    def get(self, task_id: str) -> AgentTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def get_by_name(self, name: str) -> AgentTask | None:
        """按名称查找任务（支持部分匹配）。"""
        with self._lock:
            for task in self._tasks.values():
                if task.name == name or task.id.startswith(name):
                    return task
        return None

    def get_all(self) -> list[AgentTask]:
        with self._lock:
            return list(self._tasks.values())

    def update_status(self, task_id: str, status: AgentTaskStatus) -> None:
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = status
                if status in (AgentTaskStatus.COMPLETED,
                              AgentTaskStatus.FAILED,
                              AgentTaskStatus.TIMEOUT):
                    self._tasks[task_id].end_time = time.time()

    def update_progress(self, task_id: str, **kwargs) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                for key, value in kwargs.items():
                    if hasattr(task.progress, key):
                        setattr(task.progress, key, value)
                task.progress.last_activity_time = time.time()

    def append_message(self, task_id: str, message: dict[str, Any]) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.messages.append(message)
```

### 2. Agent 列表和 Transcript 打印 (`src/cli/agent_printer.py`)

所有输出通过 `console.print()` 追加到终端滚动缓冲区。

```python
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule


class AgentPrinter:
    """Agent 列表和 transcript 的打印器。

    所有输出通过 console.print() 追加，不清屏。
    """

    STATUS_ICONS = {
        "pending": "◻",
        "running": "▶",
        "completed": "✓",
        "failed": "✗",
        "timeout": "⏱",
    }

    def __init__(self, registry: AgentTaskRegistry, console: Console):
        self._registry = registry
        self._console = console

    def print_agent_list(self) -> None:
        """打印 Agent 列表（/agents 命令 或 ↑↓ 键触发）。"""
        tasks = self._registry.get_all()
        if not tasks:
            self._console.print("[dim]没有运行中的子 Agent[/]")
            return

        text = Text()
        text.append("\n")
        text.append("── Agents ──\n", style="bold yellow")

        # main 行
        text.append("  ○ main\n", style="bold")

        # 各 Agent 行
        for task in tasks:
            icon = self.STATUS_ICONS.get(task.status.value, "?")
            elapsed = task.format_duration()
            tokens = ""
            if task.progress.token_count > 0:
                tokens = f" · {task.progress.token_count / 1000:.1f}k tok"
            desc = task.progress.last_activity or task.description
            if len(desc) > 40:
                desc = desc[:37] + "..."

            style = "green" if task.status.value == "completed" else \
                    "red" if task.status.value == "failed" else \
                    "yellow" if task.status.value == "running" else "dim"

            text.append(f"  {icon} {task.id} ", style=style)
            text.append(f"{task.name}: {desc}", style="")
            text.append(f" {icon} {elapsed}{tokens}\n", style="dim")

        text.append("[dim]  /agent <id> 查看 transcript[/]")
        self._console.print(text)

    def print_transcript(self, task_id_or_name: str) -> None:
        """打印 Agent transcript（增量模式）。

        首次查看：打印 Rule 分隔符 + 全部消息
        再次查看：打印 "── N new messages ──" + 仅新增消息
        """
        # 查找任务
        task = self._registry.get(task_id_or_name)
        if not task:
            task = self._registry.get_by_name(task_id_or_name)
        if not task:
            self._console.print(f"[red]Agent '{task_id_or_name}' 不存在[/]")
            return

        # 获取当前消息数和上次打印位置
        with self._registry._lock:
            current_count = len(task.messages)
            last_printed = task.last_printed_index

        # 首次查看：打印标题分隔符
        if last_printed == 0:
            status_icon = self.STATUS_ICONS.get(task.status.value, "?")
            elapsed = task.format_duration()
            title = f" {status_icon} {task.name} ({task.id}) · {elapsed} "
            self._console.print(Rule(title=title, style="bold cyan"))

        # 增量：只打印新消息
        new_messages = task.messages[last_printed:current_count]

        if not new_messages and last_printed > 0:
            self._console.print("[dim]  (无新消息)[/]")
            return

        if last_printed > 0 and new_messages:
            # 再次查看时的分隔符
            self._console.print(
                f"[dim]── {len(new_messages)} new messages ──[/]"
            )

        # 打印消息
        for msg in new_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                self._console.print(f"  [cyan]> {content}[/]")
            elif role == "assistant":
                self._console.print(f"  {content}")
            elif role == "tool":
                tool_name = msg.get("metadata", {}).get("tool_name", "")
                tool_status = msg.get("metadata", {}).get("status", "")
                if tool_status == "start":
                    self._console.print(f"  [yellow]🔧 {tool_name}(...)[/]")
                elif tool_status == "end":
                    self._console.print(f"  [green]✓ {tool_name}[/]")
            elif role == "system":
                self._console.print(f"  [dim italic]⚡ {content}[/]")

        # 更新打印位置
        with self._registry._lock:
            task.last_printed_index = current_count

        # 如果 Agent 已完成，打印结束分隔符
        if task.is_terminal and current_count == len(task.messages):
            self._console.print(Rule(style="dim"))
```

### 3. 非阻塞委托

```python
# src/delegation/manager.py - 新增方法

def delegate_background(self, goal, role, toolsets, context, name="") -> str:
    """后台委托：立即返回 task_id。"""
    task_id = str(uuid.uuid4())[:8]
    task_name = name or goal[:30].replace(" ", "-").lower()

    task = self._task_registry.register(task_id, task_name, goal)

    thread = threading.Thread(
        target=self._run_background_agent,
        args=(task_id, goal, role, toolsets, context, task),
        daemon=True,
        name=f"bg-agent-{task_id}",
    )
    thread.start()
    return task_id


def _run_background_agent(self, task_id, goal, role, toolsets, context, task):
    """后台线程入口。"""
    try:
        if self._parent_event_bus:
            self._parent_event_bus.emit(EventType.DELEGATION_START, {
                "child_task_id": task_id, "goal": goal,
            })

        # 创建子 ConversationLoop，事件转发到父 EventBus
        child_loop = self._create_child_loop(task_id, goal, role, toolsets, context)
        result = child_loop.run(...)

        self._task_registry.update_status(task_id, AgentTaskStatus.COMPLETED)
        summary = result.get("summary", "")

        if self._parent_event_bus:
            self._parent_event_bus.emit(EventType.DELEGATION_COMPLETE, {
                "child_task_id": task_id,
                "summary": summary,
                "tool_calls": result.get("tool_calls", 0),
            })

    except Exception as e:
        self._task_registry.update_status(task_id, AgentTaskStatus.FAILED)
        if self._parent_event_bus:
            self._parent_event_bus.emit(EventType.DELEGATION_FAIL, {
                "child_task_id": task_id, "error": str(e),
            })
```

```python
# src/tools/impls/delegation_tool.py - 修改

def delegate_task(goal="", tasks=None, role="leaf", toolsets=None,
                  context="", background=True, name="", task_id=None, **kwargs):
    """委托任务给子 Agent。

    background=True（默认）：立即返回 task_id，子 Agent 后台运行。
    使用 /agents 查看状态，/agent <id> 查看 transcript。
    """
    mgr = get_manager()
    if background:
        if tasks:
            task_ids = []
            for i, t in enumerate(tasks[:3]):
                tid = mgr.delegate_background(
                    goal=t.get("goal", ""), role=role,
                    toolsets=toolsets, context=t.get("context", context),
                    name=t.get("name", f"task-{i+1}"),
                )
                task_ids.append(tid)
            return json.dumps({
                "status": "dispatched", "task_ids": task_ids,
                "message": f"Dispatched {len(task_ids)} agents. /agents to view."
            })
        else:
            tid = mgr.delegate_background(goal, role, toolsets, context, name)
            return json.dumps({
                "status": "dispatched", "task_id": tid,
                "message": f"Agent {tid} started. /agents to view."
            })
    else:
        # 阻塞模式（兼容）
        ...
```

### 4. task-notification 回流 (`src/delegation/notification.py`)

```python
def format_task_notification(task_id, status, summary, tool_calls=0, duration_s=0) -> str:
    """格式化 task-notification XML。"""
    return (
        f"<task-notification>\n"
        f"<task-id>{task_id}</task-id>\n"
        f"<status>{status}</status>\n"
        f"<summary>{summary}</summary>\n"
        f"<tool-calls>{tool_calls}</tool-calls>\n"
        f"<duration>{duration_s:.1f}s</duration>\n"
        f"</task-notification>"
    )
```

### 5. TUI 集成

```python
# src/cli/tui.py - 新增

class TUIApp:
    def __init__(self, ...):
        # 新增组件
        self._task_registry = AgentTaskRegistry()
        self._agent_printer = AgentPrinter(self._task_registry, self.console)

    # 新增斜杠命令处理
    async def _handle_command(self, command: str):
        if command == "/agents":
            self._agent_printer.print_agent_list()
            return
        if command.startswith("/agent "):
            agent_id = command[7:].strip()
            self._agent_printer.print_transcript(agent_id)
            return
        # ... 原有命令 ...

    # ↑↓ 键绑定
    def _create_key_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add("up")
        def _(event):
            """↑ 键：打印 Agent 列表摘要。"""
            tasks = self._task_registry.get_all()
            if tasks:
                self._agent_printer.print_agent_list()

        @bindings.add("down")
        def _(event):
            """↓ 键：打印 Agent 列表摘要。"""
            tasks = self._task_registry.get_all()
            if tasks:
                self._agent_printer.print_agent_list()

        return bindings
```

### 6. 事件处理

```python
# src/cli/event_handler.py - 新增事件监听

class ConversationEventHandler:
    def __init__(self, ..., task_registry: AgentTaskRegistry):
        self._task_registry = task_registry

    def _on_delegation_start(self, data: dict):
        task_id = data.get("child_task_id", "")
        goal = data.get("goal", "")
        # 打印启动通知
        self._console.print(
            f"  [dim][bg] Agent {task_id} started: {goal[:50]}[/]"
        )

    def _on_delegation_complete(self, data: dict):
        task_id = data.get("child_task_id", "")
        summary = data.get("summary", "")
        task = self._task_registry.get(task_id)
        # 打印完成通知
        elapsed = task.format_duration() if task else "?"
        self._console.print(
            f"  [green][bg] Agent {task_id} done ({elapsed}): "
            f"{summary[:60]}[/]"
        )

    def _on_tool_start(self, data: dict):
        child_id = data.get("child_task_id")
        if child_id:
            # 子 Agent 的工具调用 → 更新 progress
            self._task_registry.update_progress(
                child_id,
                last_activity=f"calling {data.get('tool_name', '')}",
                tool_calls=...,
            )
            self._task_registry.append_message(child_id, {
                "role": "tool",
                "content": "",
                "metadata": {
                    "tool_name": data.get("tool_name"),
                    "status": "start",
                },
            })
        # ... 原有逻辑 ...

    def _on_message_append(self, data: dict):
        child_id = data.get("child_task_id")
        if child_id:
            self._task_registry.append_message(child_id, {
                "role": data.get("role", ""),
                "content": data.get("content", ""),
            })
        # ... 原有逻辑 ...
```

## 用户交互流程

```
用户: 帮我重构 auth 模块，同时生成测试

assistant: 好的，我将启动两个子 Agent 并行工作。
  [bg] Agent a1b2 started: refactor auth module
  [bg] Agent c3d4 started: generate auth tests
  Dispatched 2 agents. /agents to view.

用户: /agents

── Agents ──
  ○ main
  ▶ a1b2 auth-refactor: patching auth.py ▶ 1m20s · 5.2k tok
  ▶ c3d4 test-gen: reading test_auth.py  ▶ 1m20s · 3.1k tok
  /agent <id> 查看 transcript

用户: /agent a1b2                          ← 首次查看，打印全部

══ auth-refactor (a1b2) · 1m20s ══════════════════
  > refactor the auth module to use JWT tokens
  🔧 read_file(...)
  ✓ read_file
  🔧 patch(...)
  ✓ patch
  Refactored login flow to use JWT tokens...

用户: (继续与主 Agent 对话)
用户: auth 重构进展如何？
assistant: 让我查看一下子 Agent 的状态...

用户: /agent a1b2                          ← 再次查看，只打印新增

── 3 new messages ──
  🔧 write_file(auth_jwt.py)
  ✓ write_file
  Created new JWT authentication handler...

用户: /agent c3d4                          ← 首次查看另一个

══ test-gen (c3d4) · 2m45s ════════════════════════
  > generate tests for the auth module
  🔧 read_file(...)
  ✓ read_file
  🔧 write_file(...)
  ✓ write_file
  Generated 12 test cases for auth module...

  [green][bg] Agent c3d4 done (2m45s): Generated 12 tests[/]

用户: /agent a1b2                          ← 第三次查看

── 2 new messages ──
  🔧 terminal("pytest tests/auth/")
  ✓ terminal (exit 0)
──────────────────────────────────────────────────

  [green][bg] Agent a1b2 done (4m10s): All tests passing[/]
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| ↑↓ 键与终端滚动冲突 | 仅在有子 Agent 时拦截 ↑↓，无子 Agent 时保持终端原生滚动 |
| 大量消息导致 transcript 打印过慢 | 限制 transcript 最多显示最近 100 条消息 |
| 子 Agent 长时间运行 | 保留 child_timeout_seconds，超时自动终止 |
| 事件线程与 TUI 线程并发写入 console | Rich Console 本身是线程安全的（内部有锁） |
