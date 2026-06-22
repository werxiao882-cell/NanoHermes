## 为什么

当前 NanoHermes 的 TUI 是单面板滚动终端（prompt_toolkit + Rich `console.print()`）。子 Agent 执行时阻塞父对话，所有 Agent 事件混在同一输出流中。

参考 Claude Code 的 `CoordinatorTaskPanel` 和视图切换机制，采用 **滚动 + 分隔符** 方案：
- 子 Agent 后台运行，不阻塞主对话
- 底部打印 Agent 列表（Rich Text）
- ↑↓ 键选择，Enter 打印分隔符 + transcript
- 终端滚动保留所有历史（不清屏）

**设计约束**：当前架构是命令式追加模型（`console.print()` 追加到滚动缓冲区），不支持原地替换。因此不做 re-render，而是用分隔符 + Panel 标记视图切换点。

## 变更内容

- 实现 AgentTask 状态模型和注册表
- 实现非阻塞委托（delegate_task 立即返回 task_id）
- 实现 bottom_toolbar 实时状态栏（显示运行中子 Agent 的动作）
- 实现 `/agents` 和 `/agent <id>` 斜杠命令
- 实现 ↑↓ 键打印 Agent 列表、Enter 打印 transcript 分隔符
- 实现 task-notification 回流

## 能力

### 新增能力

- `agent-task-state`: Agent 任务状态模型。每个子 Agent 对应一个 AgentTask，包含 status/progress/messages。AgentTaskRegistry 管理所有任务。

- `nonblocking-delegation`: delegate_task 默认 background=True，立即返回 task_id，子 Agent 在后台线程运行。

- `agent-status-toolbar`: 主视图中使用 prompt_toolkit 的 `bottom_toolbar` 实时显示运行中子 Agent 的状态（名称、当前动作、耗时、token 数）。始终可见，不影响滚动历史，无子 Agent 时自动隐藏。

- `agent-commands`: 两个新斜杠命令：
  - `/agents` — 打印所有 Agent 状态列表
  - `/agent <id|name>` — 打印分隔符 + 该 Agent 的完整 transcript

- `agent-list-print`: ↑↓ 键触发打印 Agent 列表（Rich Text 格式），Enter 键打印分隔符 + 选中 Agent 的 transcript。

- `task-notification`: 子 Agent 完成后，通过结构化 XML 消息将结果回流到主 Agent 上下文。

### 修改能力

- `delegate-api`: 新增 background 参数（默认 True），非阻塞时返回 task_id。

## 影响

- 新增 `src/cli/agent_task.py`（AgentTask + AgentTaskRegistry）
- 新增 `src/delegation/notification.py`（task-notification 格式化）
- 修改 `src/cli/tui.py`（集成 ↑↓ 键 + Agent 列表打印 + transcript 打印）
- 修改 `src/cli/event_handler.py`（监听 delegation 事件，更新 AgentTask）
- 修改 `src/delegation/manager.py`（非阻塞委托）
- 修改 `src/tools/impls/delegation_tool.py`（非阻塞 handler）
- 无破坏性变更：单子 Agent 时退化为现有行为
