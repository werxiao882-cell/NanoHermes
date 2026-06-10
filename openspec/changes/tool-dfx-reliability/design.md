# Design: 工具调用 DFX 能力补充

## 分析范围

对比 Claude Code 的 `withRetry.ts`（822 行，29KB）和 `toolOrchestration.ts`（188 行，5.7KB）
与 NanoHermes 现有的 `dispatcher.py`（399 行，16.9KB）。

## Claude Code 的 DFX 体系

### 1. 错误分类与重试（withRetry.ts）

```typescript
// 错误分类
isTransientCapacityError()   → 429/529 → 重试
isStaleConnectionError()     → ECONNRESET/EPIPE → 重连
isOAuthTokenRevokedError()   → 403 → 刷新 token
isBedrockAuthError()         → Bedrock 认证 → 刷新凭证
isFastModeCooldown()         → 限流 → 降级到 standard mode

// 重试策略
DEFAULT_MAX_RETRIES = 10           // 最大重试次数
BASE_DELAY_MS = 500                // 基础退避延迟
MAX_529_RETRIES = 3                // 529 错误最多 3 次
PERSISTENT_MAX_BACKOFF_MS = 5min   // 持久模式最大退避
HEARTBEAT_INTERVAL_MS = 30s        // 心跳保活间隔
```

### 2. 工具编排（toolOrchestration.ts）

```typescript
// 并发分组
partitionToolCalls() → 按 isConcurrencySafe 分为并发组/串行组
getMaxToolUseConcurrency() → 环境变量 CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY (默认 10)

// Context Modifier
工具返回 contextModifier → 批次完成后统一应用 → 更新 ToolUseContext

// 执行状态追踪
setInProgressToolUseIDs() / markToolUseAsComplete() → 防重入
```

## NanoHermes 现状

```python
# dispatcher.py 现有能力
✅ try/catch 错误包装 → JSON 错误返回
✅ 超时保护 300s → 两个异步桥接路径都有
✅ 可用性检查 → check_fn 快速失败
✅ 异步桥接 → 3 种策略
❌ 错误分类 → 所有错误同等处理
❌ 重试机制 → 无
❌ 并发限流 → 无上限
❌ Context Modifier → 无
❌ 结果预算 → 仅个别工具有 limit
❌ 执行状态追踪 → 无
```

## 设计决策

### 工具调用重试

**为什么不在 dispatcher.py 中直接加重试？**
- dispatcher 是底层执行器，不应包含业务逻辑的重试策略
- 重试应由上层的 `conversation/loop.py` 或新的 `ToolRetryManager` 控制
- 不同工具的重试策略不同（terminal 不重试，read_file 可重试）

**设计方案**: `ToolRetryManager` 类
- 维护可重试工具白名单（只读工具）
- 按错误类型分类：`RetryableError` / `NonRetryableError`
- 指数退避：`min(base_delay * 2^attempt, max_delay)`
- 与 `fallback-chain` 协同：工具重试失败后可能触发模型回退

### 工具并发限流

**为什么需要限流？**
- 无限制并发可能打满系统资源（文件描述符、内存、CPU）
- 某些工具（如 terminal）并发执行可能导致竞态条件
- Claude Code 默认 10 个并发，可通过环境变量调整

**设计方案**: `asyncio.Semaphore` 控制
- 配置项 `max_tool_concurrency: int`（默认 10）
- 环境变量 `NANOHERMES_MAX_TOOL_CONCURRENCY` 覆盖
- 与 `tool-concurrency-partitioning` 协同：并发组内仍受限流器控制

### Context Modifier

**为什么需要 Context Modifier？**
- `cd /path` 后后续工具需要使用新路径
- `write_file` 后需要更新文件附件列表
- 批次工具执行后统一应用，避免中间状态不一致

**设计方案**: `ContextModifier` 类
- 工具返回 `{"result": "...", "context_modifier": {...}}` 格式
- `dispatch_batch()` 收集所有 modifier，按顺序应用
- 修改类型：`working_directory`, `file_attachments`, `env_vars`

### 错误分类器

**为什么需要错误分类？**
- 连接错误（ECONNRESET）→ 重连即可重试
- 认证错误（401）→ 刷新凭证后重试
- 限流错误（429/529）→ 退避后重试
- 工具内部错误 → 不可重试，直接返回

**设计方案**: `ToolErrorClassifier` 类
- 正则/字符串匹配分类错误
- 返回 `(is_retryable, delay, action)` 三元组
- 与 `error-classifier`（API 错误分类器）保持一致的分类体系
