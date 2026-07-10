# src/tools — 工具运行时架构

## 模块概述

统一的工具注册、发现、可用性检查、分发执行机制。支持自注册工具模型、延迟加载（Lazy Loading）、
按需搜索发现（Tool Search）、DFX 运维能力（重试/并发/预算/追踪/上下文修改）。

## 文件职责

### 根目录
- `__init__.py` — 模块入口，re-export 核心 API（ToolRegistry、dispatch、TerminalEnvironment 等）

### core/ — 核心运行时
- `__init__.py` — re-export core 子模块 API
- `registry.py` — 工具注册表（ToolEntry 数据类 + ToolRegistry 单例 + AST 自动发现）
- `dispatcher.py` — 工具分发器（同步/异步桥接 + 重试 + 结果预算 + 执行追踪集成）
- `availability.py` — 可用性检查（按 check_fn id 缓存 + 去重，异常视为不可用）
- `search_tool.py` — BM25 + Regex 双引擎搜索 + `search_tool` 内置工具注册

### dfx/ — Design for Excellence（运维能力）
- `__init__.py` — re-export DFX API
- `retry_classifier.py` — 错误分类器（连接/认证/限流/不可重试 → 恢复动作）
- `retry_manager.py` — 异步重试管理器（白名单 + 指数退避 + 恢复动作执行）
- `concurrency_limiter.py` — 并发限流器（全局+每工具信号量 + 安全/串行分组）
- `execution_tracker.py` — 执行状态追踪（防重入 + 超时清理 + 历史记录）
- `result_budget.py` — 结果预算管理（头尾保留截断，默认 8000 tokens）
- `context_modifier.py` — 上下文修改器（延迟应用 + 同类型去重 + cd 检测）

### impls/ — 具体工具实现
- `terminal.py` — 终端工具（subprocess + 危险命令检测 + 后台委托 process_tool）
- `file_tool.py` — 文件工具（read_file, write_file, search_files, patch）
- `code_execution_tool.py` — 代码执行（execute_code，临时文件 + 安全检查）
- `process_tool.py` — 后台进程管理（list/poll/log/wait/kill/write/submit/close）
- `memory_tool.py` — 持久记忆（委托 MemoryStore，add/replace/remove/view）
- `session_search_tool.py` — 历史会话搜索（FTS5/LIKE，discovery/scroll/browse 三模式）
- `skills_tool.py` — 技能管理（skill_manage, skill_view, skills_list，委托 SkillManager）
- `delegation_tool.py` — 子 Agent 委托（delegate_task，单任务/批量 + 后台/阻塞模式）
- `todo_tool.py` — 任务计划（todo，TodoStore 内存存储 + 合并/替换逻辑）
- `clarify_tool.py` — 澄清提问（clarify，预设选项 + 自定义输入）
- `cronjob_tool.py` — 定时任务管理（cronjob，JSON 文件存储 + 多种调度格式）
- `web_search_tool.py` — 网络搜索（web_search，DuckDuckGo ddgs/旧版双兼容）
- `mcp_client_tool.py` — MCP 客户端接口（call_mcp_tool, list_mcp_tools, register_mcp_service）

## 核心数据流

```
工具模块 import
    │ register_tool()
    ▼
ToolRegistry._tools (全局字典)
    │
    ├─── get_tool_schemas(exclude_deferred=True) ──→ 始终加载工具 schema (9 个)
    │         │                                           │
    │         │                              对话循环每轮合并传递给 LLM
    │         │                                           │
    ├─── get_deferred_tools() ──→ ToolSearch 构建 BM25 索引
    │                                    │
    │                           LLM 调用 search_tool(query)
    │                                    │
    │                           返回匹配 schema → 加入 _discovered_tools
    │
    ▼
LLM 返回 tool_use(name, arguments)
    │
    ▼
dispatch(name, args)
    │
    ├── 1. ToolRegistry.get_tool(name) → ToolEntry
    ├── 2. check_tool_availability(check_fn) → 快速失败
    ├── 3. _parse_args(JSON str → dict)
    ├── 4. ToolExecutionTracker.mark_start() → 防重入
    ├── 5. 重试循环 (仅 DEFAULT_RETRYABLE_TOOLS):
    │       handler(**args) 或 _async_bridge(handler, args)
    │       ├── 成功 → apply_budget_to_dispatch_result() → mark_complete()
    │       └── 失败 → ToolErrorClassifier.classify() → 退避重试
    └── 6. 返回结果字符串 (JSON)

dispatch_batch(tool_calls)
    │
    ├── ToolConcurrencyLimiter.register_tool() (每个工具)
    ├── partition_tool_calls() → 并发安全组 / 串行组
    └── execute_batch_sync() → 逐组调用 dispatch()
```

## 关键设计决策

- **三层子目录 core/dfx/impls 分离** — core 是运行时基础设施，dfx 是横切运维能力，impls 是具体工具，职责正交
- **工具 handler 返回 JSON 字符串** — LLM API 期望字符串结果，统一格式简化下游处理
- **DFX 集成在 dispatcher 层而非工具层** — 工具实现无需关心重试/预算/追踪，横切关注点集中管理
- **只读工具可重试，写操作工具不可重试** — 重试写操作可能产生副作用（重复写入），只读操作天然幂等
- **结果预算使用头尾保留截断** — 错误信息通常在输出末尾，头部包含命令/路径上下文
- **BM25 使用 `log(1 + ...)` IDF 变体** — 标准公式在 df > N/2 时产生负 IDF，加 1 确保始终 >= 0
- **9 个核心工具始终加载，8 个延迟加载** — 核心 I/O + 技能覆盖高频场景，减少初始上下文占用约 47%
- **异步桥接双策略** — 有运行中事件循环时新建线程（策略 A），无循环时复用持久事件循环（策略 B），300 秒超时保护
- **AST 自动发现工具模块** — 解析 .py 文件检测顶层 `register_tool()` 调用，新增工具无需修改注册表代码

## 对外接口

其他模块使用的公共 API：

```python
# 注册表
from src.tools import ToolRegistry, register_tool, get_tool, get_all_tools, get_tool_schemas, discover_tools
# 分发
from src.tools import dispatch
from src.tools.core.dispatcher import dispatch_batch
# 可用性
from src.tools import check_tool_availability
# 终端环境
from src.tools import TerminalEnvironment, LocalEnvironment
# DFX
from src.tools.dfx import ToolConcurrencyLimiter, ToolExecutionTracker, ContextModifier
from src.tools.dfx import apply_tool_result_budget, get_result_budget
# Todo
from src.tools.impls.todo_tool import get_todo_store, TodoStore
# Memory
from src.tools.impls.memory_tool import set_memory_store
# Process
from src.tools.impls.process_tool import _start_process  # terminal background 模式调用
```

## 依赖关系

```
src/tools/
├── src.skills.manager          (skills_tool.py → SkillManager)
├── src.skills.security         (skills_tool.py → is_background_review, SkillProvenance)
├── src.skills.preprocessing    (skills_tool.py → preprocess_skill_content)
├── src.memory.memory_store     (memory_tool.py → MemoryStore 延迟初始化)
├── src.session.session_db      (session_search_tool.py → SessionDB)
├── src.delegation              (delegation_tool.py → get_manager)
├── src.mcp.client              (mcp_client_tool.py → McpClientManager)
└── src.conversation.events     (retry_manager.py → EventBus CREDENTIAL_EXPIRED)
```

外部依赖：subprocess, tempfile, asyncio, threading, json, re, math, ast, os, time (均为 stdlib)；
可选依赖 ddgs/duckduckgo_search (web_search_tool.py)。
