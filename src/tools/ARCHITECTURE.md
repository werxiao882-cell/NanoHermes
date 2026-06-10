# Tool Runtime Architecture

## Responsibility
统一的工具注册、发现、可用性检查、分发执行机制。支持自注册工具模型、工具集分组、
延迟加载（Lazy Loading）、按需搜索发现（Tool Search）、终端命令执行和危险命令审批。

## Components

```
──────────────────────────────────────────────────────────────┐
│                    Conversation Loop                          │
│                                                              │
│  _always_loaded_schemas  ← 启动时加载的核心工具               │
│  _discovered_tools       ← 通过 search_tools 动态发现的工具   │
│  _get_current_tools()    ← 每轮合并两者传递给模型             │
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
│  ToolEntry:                                                  │
│    name, toolset, schema, handler, check_fn, is_async,       │
│    description, defer_loading ← 新增字段                     │
│                                                              │
│  register(entry)                                             │
│  get_tool(name) / get_all_tools()                            │
│  get_tool_schemas(toolset_filter, exclude_deferred)          │
│  get_deferred_tools()  ← 新方法                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Tool Search Engine                         │
│                                                              │
│  ToolSearch:                                                 │
│    - BM25 倒排索引（自然语言搜索）                            │
│    - Regex 匹配（精确模式搜索）                               │
│    - Auto 模式（自动检测查询类型）                            │
│                                                              │
│  search(query, mode="auto", top_k=5) → list[schema]          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    search_tools (Built-in Tool)               │
│                                                              │
│  始终可见（defer_loading=False），是 Tool Search 的入口点     │
│  模型通过此工具按需发现延迟加载的工具                         │
│  直接从 ToolRegistry.get_deferred_tools() 构建搜索引擎        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Tool Categories                            │
│                                                              │
│  Core Tools:                                                 │
│  ├── registry.py         - 工具注册表（Map 存储）            │
│  ├── dispatcher.py       - 工具分发器                        │
│  ├── toolsets.py         - 工具集定义和解析                  │
│  ├── availability.py     - 可用性检查（缓存 + 去重）         │
│  ├── async_bridge.py     - 异步桥接                          │
│  ├── search_tool.py      - BM25 + Regex 搜索引擎 + search_tools 内置工具 │
│                                                              │
│  Always-Loaded Tools (defer_loading=False):                  │
│  ├── terminal            - 终端工具（subprocess + 危险检测） │
│  ├── read_file           - 读取文件                          │
│  ├── write_file          - 写入文件                          │
│  ├── search_files        - 搜索文件                          │
│  ├── patch               - 文件编辑                          │
│  └── search_tools        - 搜索可用工具                      │
│                                                              │
│  Deferred Tools (defer_loading=True):                        │
│  ├── execute_code        - 代码执行                          │
│  ├── process             - 后台进程管理                      │
│  ├── todo                - 任务计划                          │
│  ├── memory              - 持久记忆                          │
│  ├── session_search      - 历史会话搜索                      │
│  ├── clarify             - 澄清提问                          │
│  ├── skill_view          - 查看技能                          │
│  ├── skills_list         - 列出技能                          │
│  ├── skill_manage        - 技能管理                          │
│  ├── delegate_task       - 子 Agent 委托                     │
│  └── cronjob             - 定时任务管理                      │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 工具模块在 import 时调用 `register_tool()` 自动注册到全局注册表
2. `get_tool_schemas(exclude_deferred=True)` 仅返回核心工具（6 个）
3. `get_deferred_tools()` 返回所有延迟加载的工具（11 个）
4. ToolSearch 对延迟工具构建 BM25 倒排索引
5. 对话循环每轮合并 `_always_loaded_schemas` + `_discovered_tools` 传递给模型
6. 模型调用 `search_tools` 发现新工具，结果自动加入 `_discovered_tools`
7. 下一轮模型可以调用新发现的工具

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
- **Decision**: `search_tools` 直接从 ToolRegistry 读取延迟工具，不依赖全局单例
  - **Reason**: 低耦合，无需 main.py 初始化顺序，工具自包含
- **Decision**: BM25 使用 `log(1 + (N-df+0.5)/(df+0.5))` 而非标准 IDF 公式
  - **Reason**: 标准公式在 df > N/2 时产生负 IDF，加 1 确保始终 >= 0
- **Decision**: 5 个核心工具 + search_tools 始终加载，其余 11 个延迟加载
  - **Reason**: 核心 I/O 循环覆盖 90%+ 使用场景，减少初始上下文占用 ~80%

## Dependencies
- Internal: src/skills/manager.py (技能管理), src/config/ (配置模块)
- External: subprocess (stdlib), tempfile (stdlib), math (stdlib), re (stdlib)
