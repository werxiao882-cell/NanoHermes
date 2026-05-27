# Tool Runtime Architecture

## Responsibility
统一的工具注册、发现、可用性检查、分发执行机制。支持自注册工具模型、工具集分组、
终端命令执行和危险命令审批。

## Components

```
──────────────────────────────────────────────────────────────┐
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
│  3. parse args (JSON string → dict)                          │
│  4. execute handler (sync or async via bridge)               │
│  5. wrap result as JSON string                               │
└───────────────────────────────────────────────┬──────────────┘
         │                                       │
         ▼                                       ▼
┌──────────────────┐              ──────────────────────────────┐
│  Sync Handler    │              │  Async Handler               │
│  direct call     │              │  async_bridge → event loop   │
└──────────────────┘              └──────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Tool Registry                              │
│                                                              │
│  register(name, toolset, schema, handler, check_fn)          │
│  get_tool(name) / get_all_tools()                            │
│  get_tool_schemas(toolset_filter)                            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Tool Categories                            │
│                                                              │
│  Core Tools:                                                 │
│  ├── registry.py         - 工具注册表（Map 存储）            │
│  ├── dispatcher.py       - 工具分发器                        │
│  ├── toolsets.py         - 工具集定义和解析                  │
│  ├── availability.py     - 可用性检查（缓存 + 去重）         │
│  └── async_bridge.py     - 异步桥接                          │
│                                                              │
│  Default Tools (每个类别独立文件):                           │
│  ├── terminal.py         - 终端工具（subprocess + 危险检测） │
│  ├── file_tools.py       - 文件工具（read/write/search/patch）│
│  ├── clarify_tools.py    - 澄清提问（预设选项 + 自定义输入） │
│  ├── code_execution_tools.py - 代码执行                      │
│  ├── cronjob_tools.py    - 定时任务管理                      │
│  ├── delegation_tools.py - 子 Agent 委托                     │
│  ├── memory_tools.py     - 持久记忆                          │
│  ├── session_search_tools.py - 历史会话搜索                  │
│  ├── skills_tools.py     - 技能管理（调用 SkillManager）     │
│  └── process_tools.py    - 后台进程管理                      │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 工具模块在 import 时调用 `register_tool()` 自动注册到全局注册表
2. `get_tool_schemas()` 根据 enabled/disabled toolsets 过滤，返回 OpenAI 格式的工具 schema
3. 对话循环调用 `dispatch(name, args)`
4. 分发器查找 ToolEntry，解析参数（JSON 字符串 → dict），执行 handler
5. 返回 JSON 字符串结果

## Design Decisions
- **Decision**: 使用 dict 作为注册表存储（Python 原生）
  - **Reason**: O(1) 查找，类型安全，易于迭代
- **Decision**: 工具 handler 返回字符串（JSON 格式）
  - **Reason**: LLM 期望字符串结果，统一返回类型简化处理
- **Decision**: 错误包装在分发器层完成
  - **Reason**: 确保 LLM 始终收到结构化结果
- **Decision**: 终端工具使用 subprocess.Popen
  - **Reason**: 支持流式输出、进程控制、超时
- **Decision**: 每个工具类别独立文件（`<category>_tools.py`）
  - **Reason**: 职责清晰，便于维护和扩展
- **Decision**: 技能管理核心逻辑在 SkillManager，工具层只负责注册和调用
  - **Reason**: 业务逻辑与工具注册分离，符合单一职责原则

## Dependencies
- Internal: src/skills/manager.py (技能管理)
- External: subprocess (stdlib), tempfile (stdlib)
