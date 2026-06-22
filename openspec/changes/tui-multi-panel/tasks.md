## 1. AgentTask 状态模型

- [x] 1.1 创建 `src/cli/agent_task.py`
  - [x] 1.1.1 实现 `AgentTaskStatus` 枚举（PENDING/RUNNING/COMPLETED/FAILED/TIMEOUT）
  - [x] 1.1.2 实现 `AgentTaskProgress` 数据类（token_count/tool_calls/last_activity）
  - [x] 1.1.3 实现 `AgentTask` 数据类（id/name/status/progress/messages/abort_event/last_printed_index）
  - [x] 1.1.4 实现 `AgentTaskRegistry` 类（register/get/get_by_name/get_all/get_all_running/update_status/update_progress/append_message/get_new_messages/has_running_tasks）
- [x] 1.2 编写单元测试（25 测试）
  - [x] 1.2.1 测试 register + get
  - [x] 1.2.2 测试 get_by_name 部分匹配
  - [x] 1.2.3 测试线程安全并发写入

## 2. Agent 打印机

- [x] 2.1 创建 `src/cli/agent_printer.py`
  - [x] 2.1.1 实现 `AgentPrinter` 类
  - [x] 2.1.2 实现 `print_agent_list()` 方法（Rich Text 格式输出）
  - [x] 2.1.3 实现 `print_transcript()` 方法（Rule 分隔符 + 增量消息列表）
  - [x] 2.1.4 实现状态图标映射（▶/⏸/✓/✗/⏱）
  - [x] 2.1.5 transcript 消息着色（user=cyan, tool=yellow/green, system=dim）
  - [x] 2.1.6 实现 `format_toolbar()` 方法（bottom_toolbar HTML 格式）
- [x] 2.2 编写单元测试（14 测试）
  - [x] 2.2.1 测试空列表输出
  - [x] 2.2.2 测试多 Agent 列表格式
  - [x] 2.2.3 测试 transcript 输出格式

## 3. task-notification

- [x] 3.1 创建 `src/delegation/notification.py`
  - [x] 3.1.1 实现 `format_task_notification()` 函数（XML 格式）
- [x] 3.2 编写单元测试（4 测试）
  - [x] 3.2.1 测试 XML 格式正确性

## 4. 非阻塞委托

- [x] 4.1 修改 `src/delegation/manager.py`
  - [x] 4.1.1 新增 `delegate_background()` 方法（立即返回 task_id，后台线程运行）
  - [x] 4.1.2 新增 `_run_background_agent()` 方法（后台线程入口，更新状态 + 发射事件）
  - [x] 4.1.3 新增 `_subscribe_child_message_to_task()` 方法（转发 MESSAGE_APPEND 到父 EventBus）
  - [x] 4.1.4 新增 `_emit_background_complete()` / `_emit_background_fail()` 方法
- [x] 4.2 修改 `src/tools/impls/delegation_tool.py`
  - [x] 4.2.1 Schema 新增 `background` 参数（默认 True）
  - [x] 4.2.2 Schema 新增 `name` 参数（任务名称）
  - [x] 4.2.3 handler: background=True 时调用 `delegate_background()`
  - [x] 4.2.4 handler: background=False 时保留原有阻塞行为
- [ ] 4.3 编写单元测试
  - [ ] 4.3.1 测试 delegate_background 立即返回 task_id
  - [ ] 4.3.2 测试后台 Agent 完成后状态更新
  - [ ] 4.3.3 测试阻塞模式兼容性

## 5. TUI 集成

- [x] 5.1 修改 `src/cli/tui.py`
  - [x] 5.1.1 初始化 `AgentTaskRegistry` + `AgentPrinter`
  - [x] 5.1.2 实现 `_get_agent_toolbar()` 方法（生成 bottom_toolbar HTML）
  - [x] 5.1.3 `PromptSession` 添加 `bottom_toolbar=self._get_agent_toolbar`
  - [x] 5.1.4 新增 `/agents` 斜杠命令（调用 `print_agent_list()`）
  - [x] 5.1.5 新增 `/agent <id>` 斜杠命令（调用 `print_transcript()`）
  - [x] 5.1.6 添加 ↑↓ 键绑定（有子 Agent 时打印列表，无子 Agent 时保持默认）
  - [x] 5.1.7 注入 `task_registry` 到 `ConversationEventHandler`
- [x] 5.2 修改 `src/cli/event_handler.py`
  - [x] 5.2.1 监听 `DELEGATION_START` → 注册 AgentTask + 打印通知
  - [x] 5.2.2 监听 `DELEGATION_COMPLETE` → 更新状态(COMPLETED) + 打印通知
  - [x] 5.2.3 监听 `DELEGATION_FAIL` → 更新状态(FAILED) + 打印通知
  - [x] 5.2.4 子 Agent 的 `TOOL_START/TOOL_END` → 更新 AgentTask progress + append_message
  - [x] 5.2.5 子 Agent 的 `MESSAGE_APPEND` → append_message 到 AgentTask

## 6. 集成测试

- [ ] 6.1 端到端测试
  - [ ] 6.1.1 无子 Agent 时 /agents 输出"没有运行中的子 Agent"
  - [ ] 6.1.2 委托后 /agents 显示 Agent 列表
  - [ ] 6.1.3 /agent <id> 打印 transcript（含分隔符）
  - [ ] 6.1.4 子 Agent 完成后 task-notification 回流
  - [ ] 6.1.5 background=False 兼容旧行为
