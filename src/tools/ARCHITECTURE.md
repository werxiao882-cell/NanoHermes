# Tool Runtime Architecture

## Responsibility
统一的工具注册、发现、可用性检查、分发执行机制。支持自注册工具模型、工具集分组、
延迟加载（Lazy Loading）、按需搜索发现（Tool Search）、DFX 运维能力（重试/并发/预算/追踪）。

## 目录结构

```
src/tools/
├── __init__.py          # 模块入口，re-export 核心 API
├── core/                # 核心运行时
│   ├── registry.py      - 工具注册表（ToolEntry + ToolRegistry）
│   ├── dispatcher.py    - 工具分发器（同步/异步桥接 + DFX 集成）
│   ├── availability.py  - 可用性检查（缓存 + 去重）
│   └── search_tool.py   - BM25 + Regex 搜索引擎 + search_tools 内置工具
├── dfx/                 # Design for Excellence（运维能力）
│   ├── retry_classifier.py    - 错误分类器（参考 Claude Code withRetry.ts）
│   ├── retry_manager.py       - 重试管理器（指数退避 + 恢复动作）
│   ├── concurrency_limiter.py - 并发限流器（信号量 + 分组调度）
│   ├── execution_tracker.py   - 执行状态追踪（防重入 + 超时清理）
│   ├── result_budget.py       - 结果预算管理（头尾保留截断）
│   └── context_modifier.py    - 上下文修改器（延迟应用 + 去重）
└── impls/               # 具体工具实现
    ├── terminal.py, file_tool.py, memory_tool.py, ...
    └── web_search_tool.py (新增)
```

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
│  4. execution tracking (mark_start / mark_complete)          │
│  5. execute handler (sync or async via bridge)               │
│     ├── retry: 只读工具自动重试 + 指数退避                   │
│     └── result budget: 大型结果头尾保留截断                  │
│  6. wrap result as JSON string                               │
└───────────────────────────────────────────────┬──────────────┘
         │                                       │
         ▼                                       ▼
┌──────────────────┐              ──────────────────────────────┐
│  Sync Handler    │              │  Async Handler               │
│  direct call     │              │  async_bridge → event loop   │
└──────────────────┘              └──────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Tool Registry (core/)                      │
│                                                              │
│  ToolEntry:                                                  │
│    name, toolset, schema, handler, check_fn, is_async,       │
│    description, defer_loading                                │
│    ─── DFX 扩展字段 ───                                      │
│    retryable, max_retries, max_concurrent_instances,         │
│    is_concurrency_safe, max_result_tokens                    │
│                                                              │
│  register(entry) / get_tool(name) / get_all_tools()          │
│  get_tool_schemas(toolset_filter, exclude_deferred)          │
│  get_deferred_tools() / get_tool_categories_with_info()      │
│  init_all_tools() / discover_tools() (AST 自动发现)          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    DFX 子系统 (dfx/)                          │
│                                                              │
│  ToolErrorClassifier:                                        │
│    - 分类: transient_capacity / stale_connection / auth /    │
│            rate_limit / fail                                 │
│    - 恢复动作: reconnect / backoff / refresh_credentials     │
│                                                              │
│  ToolRetryManager:                                           │
│    - 白名单: 只读工具可重试（read_file, search_files 等）    │
│    - 指数退避 + jitter                                       │
│                                                              │
│  ToolConcurrencyLimiter:                                     │
│    - 全局信号量 + 每工具信号量                               │
│    - partition_tool_calls(): 并发安全组 vs 串行组            │
│    - execute_batch_sync(): 分组调度                          │
│                                                              │
│  ToolExecutionTracker:                                       │
│    - 防重入: mark_start / mark_complete / mark_failed        │
│    - 超时自动清理 + 历史记录限制                             │
│                                                              │
│  Result Budget:                                              │
│    - 默认 8000 tokens，terminal 4000 tokens                  │
│    - 头尾保留截断策略                                        │
│                                                              │
│  ContextModifier:                                            │
│    - 延迟应用: register() 记录, apply_all() 统一生效         │
│    - 去重: 同类型只保留最后一次                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Tool Search Engine (core/)                 │
│                                                              │
│  ToolSearch:                                                 │
│    - BM25 倒排索引（自然语言搜索）                            │
│    - Regex 匹配（精确模式搜索，支持 select:<name> 语法）     │
│    - Auto 模式（自动检测查询类型）                            │
│                                                              │
│  search(query, mode="auto", top_k=5) → list[schema]          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Tool Categories                            │
│                                                              │
│  Always-Loaded Tools (defer_loading=False, 6 个):            │
│  ├── terminal            - 终端工具（subprocess + 危险检测） │
│  ├── read_file           - 读取文件                          │
│  ├── write_file          - 写入文件                          │
│  ├── search_files        - 搜索文件                          │
│  ├── patch               - 文件编辑                          │
│  └── search_tools        - 搜索可用工具                      │
│                                                              │
│  Deferred Tools (defer_loading=True, 12 个):                 │
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
│  ├── cronjob             - 定时任务管理                      │
│  └── web_search          - 网页搜索（DuckDuckGo）            │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 工具模块在 import 时调用 `register_tool()` 自动注册到全局注册表
2. `get_tool_schemas(exclude_deferred=True)` 仅返回核心工具（6 个）
3. `get_deferred_tools()` 返回所有延迟加载的工具（12 个）
4. ToolSearch 对延迟工具构建 BM25 倒排索引
5. 对话循环每轮合并 `_always_loaded_schemas` + `_discovered_tools` 传递给模型
6. 模型调用 `search_tools` 发现新工具，结果自动加入 `_discovered_tools`
7. `dispatch()` 内部集成：执行追踪 → 重试逻辑 → 结果预算
8. `dispatch_batch()` 通过 `ToolConcurrencyLimiter` 分组调度（并发安全 vs 串行）

## Design Decisions
- **Decision**: 三层子目录 core/dfx/impls 分离
  - **Reason**: core 是运行时基础设施，dfx 是运维能力，impls 是具体工具实现，职责边界清晰
- **Decision**: 使用 dict 作为注册表存储（Python 原生）
  - **Reason**: O(1) 查找，类型安全，易于迭代
- **Decision**: 工具 handler 返回字符串（JSON 格式）
  - **Reason**: LLM 期望字符串结果，统一返回类型简化处理
- **Decision**: DFX 集成在 dispatcher 层而非工具层
  - **Reason**: 工具实现无需关心重试/预算/追踪，横切关注点集中管理
- **Decision**: 只读工具可重试，写操作工具不可重试
  - **Reason**: 重试写操作可能产生副作用（重复写入），只读操作天然幂等
- **Decision**: 结果预算使用头尾保留截断策略
  - **Reason**: 错误信息通常在输出末尾，头部包含命令/路径上下文
- **Decision**: BM25 使用 `log(1 + (N-df+0.5)/(df+0.5))` 而非标准 IDF 公式
  - **Reason**: 标准公式在 df > N/2 时产生负 IDF，加 1 确保始终 >= 0
- **Decision**: 6 个核心工具始终加载，其余 12 个延迟加载
  - **Reason**: 核心 I/O 循环覆盖 90%+ 使用场景，减少初始上下文占用 ~80%

## Dependencies
- Internal: src/skills/manager.py (技能管理), src/config/ (配置模块)
- External: subprocess (stdlib), tempfile (stdlib), math (stdlib), re (stdlib), asyncio (stdlib)
