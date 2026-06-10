# Tasks: 工具调用 DFX 能力补充

## 1. 工具调用重试 (tool-retry)

- [x] 1.1 实现 `ToolErrorClassifier` 类（错误分类 + 退避策略）
- [x] 1.2 定义可重试工具白名单（只读工具自动加入）
- [x] 1.3 实现 `ToolRetryManager` 类（重试循环 + 指数退避 + 抖动）
- [x] 1.4 连接错误检测（ECONNRESET/EPIPE/Timeout）
- [x] 1.5 限流错误检测（429/529/Retry-After）
- [x] 1.6 认证错误检测（401/token expired）+ 凭证刷新钩子
- [x] 1.7 不可重试错误分类（ValueError/TypeError/权限错误）
- [x] 1.8 修改 `dispatcher.py` 集成执行追踪和结果预算
- [x] 1.9 编写错误分类器单元测试
- [ ] 1.10 编写重试管理器集成测试

## 2. 工具并发限流 (tool-concurrency-limiter)

- [x] 2.1 实现 `ToolConcurrencyLimiter`（asyncio.Semaphore 封装）
- [ ] 2.2 配置项 `max_tool_concurrency` 加入 schema
- [x] 2.3 环境变量 `NANOHERMES_MAX_TOOL_CONCURRENCY` 支持
- [x] 2.4 每工具 `max_concurrent_instances` 覆盖支持（ToolEntry 字段）
- [x] 2.5 排队超时保护（120s）
- [ ] 2.6 修改 `dispatch_batch()` 使用限流器
- [x] 2.7 编写并发限流单元测试

## 3. 工具结果预算 (tool-result-budget)

- [x] 3.1 实现 `apply_tool_result_budget()` 截断函数
- [ ] 3.2 配置项 `tool_result_budget` 加入 schema
- [x] 3.3 环境变量 `NANOHERMES_TOOL_RESULT_BUDGET` 支持
- [x] 3.4 `ToolEntry` 新增 `max_result_tokens` 可选覆盖
- [x] 3.5 在 `dispatch()` 中应用预算
- [ ] 3.6 在 `dispatch_batch()` 中逐个应用预算
- [x] 3.7 编写截断逻辑单元测试

## 4. 工具执行状态追踪 (tool-execution-tracking)

- [x] 4.1 实现 `ToolExecutionTracker` 单例
- [x] 4.2 定义 `ToolExecutionState` 数据类（id, tool, status, timestamps）
- [x] 4.3 `in_progress_tool_ids: set[str]` 防重入
- [x] 4.4 工具开始/完成/失败时更新状态
- [x] 4.5 超时自动终止 + 状态更新
- [x] 4.6 在 `dispatch()` 中集成追踪
- [x] 4.7 编写状态追踪单元测试
