# Tool Runtime Architecture

## Responsibility
统一的工具注册、发现、可用性检查、分发执行机制。支持自注册工具模型、工具集分组、
终端命令执行和危险命令审批。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    Conversation Loop                          │
│                  dispatch_tool(name, args)                    │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                      Tool Dispatch                            │
│                                                              │
│  1. lookup tool by name → ToolEntry                          │
│  2. check availability (cached check_fn)                     │
│  3. execute handler (sync or async via bridge)               │
│  4. wrap result as JSON string                               │
└────────┬───────────────────────────────────────┬──────────────┘
         │                                       │
         ▼                                       ▼
┌──────────────────┐              ┌──────────────────────────────┐
│  Sync Handler    │              │  Async Handler               │
│  direct call     │              │  async_bridge → event loop   │
└──────────────────┘              └──────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Tool Registry                              │
│                                                              │
│  discover_tools() → scan directory → AST check → import      │
│  register(name, toolset, schema, handler, check_fn)          │
│  get_tool_schemas(enabled_toolsets, disabled_toolsets)       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Terminal Tool                              │
│                                                              │
│  execute(command, cwd, timeout)                              │
│    → detect_dangerous_patterns()                             │
│    → if dangerous: return approval request                   │
│    → else: spawn process → collect output                    │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 工具模块在 import 时调用 registry.register() 自动注册
2. discover_tools() 扫描目录，AST 检测，动态 import 所有工具模块
3. get_tool_schemas() 根据 enabled/disabled toolsets 过滤，运行 check_fn
4. 对话循环调用 dispatch(name, args)
5. 分发器查找 ToolEntry，执行 handler，返回 JSON 结果

## Design Decisions
- **Decision**: 使用 dict 作为注册表存储（Python 原生）
  - **Reason**: O(1) 查找，类型安全，易于迭代
- **Decision**: 工具 handler 返回字符串（JSON 格式）
  - **Reason**: LLM 期望字符串结果，统一返回类型简化处理
- **Decision**: 错误包装在分发器层完成
  - **Reason**: 确保 LLM 始终收到结构化结果
- **Decision**: 终端工具使用 subprocess.Popen
  - **Reason**: 支持流式输出、进程控制、超时

## Dependencies
- Internal: None (基础层)
- External: subprocess (stdlib)
