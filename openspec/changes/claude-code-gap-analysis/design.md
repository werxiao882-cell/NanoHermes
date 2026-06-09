# Design: Claude Code 能力差距补充

## 分析范围

对比 Claude Code 2.1.69 源码与 NanoHermes 现有架构 + `advanced-agent-features` 规划的 18 个子系统。

## 发现的方法论

1. 阅读 `claude-code-analysis/FEATURE_REPORT.md`（12 大类、347 行提炼）
2. 扫描 `advanced-agent-features/specs/` 下 18 个已有 spec
3. 正则扫描 `src/` 目录验证实际实现状态
4. 交叉对比：Claude Code 有 → advanced-agent-features 无 → src/ 无 = **真正缺失**

## 缺失能力清单

### 1. 工具并发分组 (Tool Concurrency Partitioning)

**Claude Code 实现**: `partitionToolCalls()` in `toolOrchestration.ts`
- 按 `isConcurrencySafe()` 将工具调用分为并发组/串行组
- 并发组 `Promise.all()` 并行执行，串行组逐个执行
- 减少总延迟：3 个并发读操作 1s vs 3s

**NanoHermes 现状**: 工具调用全部串行执行，无并发优化

**设计决策**: 
- `ToolEntry` 新增 `is_concurrency_safe: bool` 字段（默认 False，fail-closed）
- `dispatch_batch()` 函数实现分组逻辑
- 与 `streaming-tool-execution` spec 协同：流式执行 + 并发分组

### 2. 工具结果预算 (Tool Result Budget)

**Claude Code 实现**: `applyToolResultBudget()` 
- 每个工具结果有 token 预算上限
- 超出时截断并标记 `[output truncated, N more bytes]`
- 防止单个工具结果占满上下文窗口

**NanoHermes 现状**: 工具结果无大小限制，长输出直接注入上下文

**设计决策**:
- 配置项 `tool_result_budget: int`（默认 8000 tokens）
- 截断策略：保留头部 + 尾部，中间用 `...` 替换
- 与 `context-compression` 协同：预算在压缩前应用

### 3. Context Modifier

**Claude Code 实现**: `ContextModifier` in `toolOrchestration.ts`
- 工具执行后可注册对全局 `ToolUseContext` 的修改
- 批次完成后统一应用（避免中间状态不一致）
- 典型用途：文件编辑后更新文件附件列表

**NanoHermes 现状**: 工具执行后无上下文更新机制

**设计决策**:
- `ContextModifier` 类：`register(modification)` + `apply_all()`
- 与 `hooks-system` 的 `PostSampling` 钩子协同
- 修改类型：文件附件更新、可用工具变更、工作目录变更

### 4. Headless/SDK Mode

**Claude Code 实现**: `QueryEngine` 可独立实例化，无需 UI
- Headless 模式：直接传入 message，返回 response
- SDK 模式：Python/Node 库可嵌入

**NanoHermes 现状**: 只能通过 TUI (`python -m src.main`) 交互

**设计决策**:
- `NanoHermesSDK` 类：`chat(message) -> str` + `run_conversation(messages) -> dict`
- 自动初始化所有依赖（SessionDB, ToolRegistry, Provider 等）
- 与 `provider-runtime` 复用同一套客户端

### 5. CLAUDE.md 分级信任

**Claude Code 实现**: 4 层信任模型
- `Managed` > `User` > `Project` > `Local`
- `@include` 指令深度上限 5，防循环引用
- 低信任层不能覆盖高信任层指令

**NanoHermes 现状**: 只有 `AGENTS.md` 单文件，无信任分级

**设计决策**:
- `CLAUDE.md` / `AGENTS.md` / `.nanohermes.md` 按位置自动分级
- `@include` 解析器：深度追踪 + 循环检测
- 注入系统提示时按信任级别排序

### 6. MCP 工程细节

**Claude Code 实现**: 丰富的 MCP 工程化处理
- 超时控制：`setTimeout` 而非 `AbortSignal.timeout()`（规避 Bun 内存泄漏）
- 描述截断：`MAX_MCP_DESCRIPTION_LENGTH = 2048`
- 并发控制：本地 3 / 远程 20
- 认证雪崩防护：15 分钟 Auth Cache
- Session 重连：检测 HTTP 404 + JSON-RPC -32001 自动重连

**NanoHermes 现状**: `add-mcp-server-support` 已实现基础 MCP，缺少工程细节

**设计决策**:
- 复用 `add-mcp-server-support` 的基础设施
- 新增 `MCPClientManager` 封装超时/重连/并发逻辑
- 与 `mcp/` 模块共存，不破坏已有实现
