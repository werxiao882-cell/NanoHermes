## Why

NanoHermes 的 Agent 需要调用各种工具（终端、文件操作、搜索等），工具需要统一的注册、发现、可用性检查和分发机制。Tool Runtime 层提供自注册工具模型、工具集分组、分发执行和错误包装，使对话循环无需关心工具实现细节。

## What Changes

- 实现工具注册表，支持模块级自注册（import 时自动注册）
- 实现工具集定义和解析，支持启用/禁用过滤
- 实现工具可用性检查（check_fn），基于环境变量和服务状态
- 实现工具分发器，支持同步/异步处理、JSON 参数解析、错误包装
- 实现终端工具基础（terminal），包含命令执行和危险命令审批
- 实现文件工具（read_file、write_file、search_files），支持分页读取、安全写入、模式搜索
- 实现异步桥接，在同步调用链中执行异步工具

## Capabilities

### New Capabilities

- `tool-registry`: 工具注册表，模块 import 时调用 registry.register() 自动注册。支持工具名唯一性检查、schema 收集、按名称分发。
- `toolset-resolution`: 工具集解析，支持 enabled/disabled 列表过滤。工具集是命名的工具分组，平台可选择不同的工具集组合。
- `availability-check`: 工具可用性检查，每个工具可选 check_fn 返回是否可用。检查结果按调用缓存，异常视为不可用。
- `tool-dispatch`: 工具分发器，按名称查找 handler 并执行。同步 handler 直接调用，异步 handler 通过事件循环桥接。所有执行结果包装为 JSON 字符串。
- `terminal-tool`: 终端工具基础实现，支持本地命令执行、工作目录设置、后台进程管理。包含危险命令模式检测和审批流。
- `async-bridge`: 异步桥接，在无运行中事件循环的同步上下文中执行异步工具 handler。复用持久事件循环保持异步客户端存活。

### Modified Capabilities

<!-- 无现有能力需要修改 -->

## Impact

- 新增 `src/tools/` 目录，包含注册表、分发器、工具集定义
- 新增 `src/tools/environments/` 目录，包含终端环境抽象
- conversation-loop 的 dispatchTool() 依赖此层
- 依赖 child_process 模块用于终端执行
- 无破坏性变更，从零开始构建
