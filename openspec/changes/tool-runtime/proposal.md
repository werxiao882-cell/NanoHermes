## Why

NanoHermes 的 Agent 需要调用各种工具（终端、文件操作、搜索等），工具需要统一的注册、发现、可用性检查和分发机制。Tool Runtime 层提供自注册工具模型、工具集分组、分发执行和错误包装，使对话循环无需关心工具实现细节。

## What Changes

- 实现工具注册表，支持模块级自注册（import 时自动注册）
- 实现工具集定义和解析，支持启用/禁用过滤
- 实现工具可用性检查（check_fn），基于环境变量和服务状态
- 实现工具分发器，支持同步/异步处理、JSON 参数解析、错误包装
- 重构工具文件命名：每个类别一个独立的 `_tools.py` 文件
- 实现终端工具（terminal_tools.py），包含命令执行和危险命令审批
- 实现文件工具（file_tools.py），包含 read_file、write_file、search_files、patch
- 实现默认工具集，每个工具独立文件：
  - clarify_tools.py：澄清提问（预设选项 + 自定义输入）
  - code_execution_tools.py：代码执行
  - cronjob_tools.py：定时任务管理
  - delegation_tools.py：子 Agent 委托
  - memory_tools.py：持久记忆
  - session_search_tools.py：历史会话搜索
  - skills_tools.py：技能管理（调用 SkillManager）
  - process_tools.py：后台进程管理
  - todo_tools.py：任务计划和管理（TodoStore，支持大模型制定计划）
- 实现异步桥接（async_bridge.py），在同步调用链中执行异步工具

## Capabilities

### New Capabilities

- `tool-registry`: 工具注册表，模块 import 时调用 registry.register() 自动注册。支持工具名唯一性检查、schema 收集、按名称分发。
- `toolset-resolution`: 工具集解析，支持 enabled/disabled 列表过滤。工具集是命名的工具分组，平台可选择不同的工具集组合。
- `availability-check`: 工具可用性检查，每个工具可选 check_fn 返回是否可用。检查结果按调用缓存，异常视为不可用。
- `tool-dispatch`: 工具分发器，按名称查找 handler 并执行。同步 handler 直接调用，异步 handler 通过事件循环桥接。所有执行结果包装为 JSON 字符串。
- `terminal-tool`: 终端工具基础实现，支持本地命令执行、工作目录设置、后台进程管理。包含危险命令模式检测和审批流。
- `file-tools`: 文件工具集，包含 read_file（分页读取）、write_file（安全写入）、search_files（模式搜索）、patch（查找替换）。
- `default-tools`: 默认工具集，包含 clarify（向用户提问，支持预设选项和自定义输入）、execute_code（运行 Python 脚本）、cronjob（定时任务）、delegate_task（子 Agent 委托）、memory（持久记忆）、session_search（历史会话搜索）、skills（技能管理）、process（后台进程管理）、todo（任务计划和管理）。
- `todo-tool`: todo 工具，支持大模型自己制定计划、跟踪任务进度。包含 TodoStore 类（内存任务列表）、todo_tool 函数（读写任务）、任务状态管理（pending/in_progress/completed/cancelled）、任务合并和替换逻辑。参考 Hermes Agent 实现。
- `async-bridge`: 异步桥接，在无运行中事件循环的同步上下文中执行异步工具 handler。复用持久事件循环保持异步客户端存活。

### Modified Capabilities

<!-- 无现有能力需要修改 -->

## Impact

- 新增 `src/tools/` 目录，包含注册表、分发器、工具集定义
- 新增 `src/tools/environments/` 目录，包含终端环境抽象
- conversation-loop 的 dispatchTool() 依赖此层
- 依赖 child_process 模块用于终端执行
- 无破坏性变更，从零开始构建
