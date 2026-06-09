# Proposal: 工具调用 DFX 能力补充

## Why

Claude Code 的 `withRetry.ts`（822 行）和 `toolOrchestration.ts` 展示了完整的工具调用 DFX（Design for Excellence）体系，包括错误分类重试、并发限流、上下文修改器、结果预算等。NanoHermes 现有的 `dispatcher.py` 只实现了基础的 try/catch 错误包装，缺少生产级可靠性设计。

## What Changes

- **工具调用重试** — 按错误类型分类（429/529/连接/认证）+ 指数退避 + 快速模式降级
- **工具并发限流** — 环境变量控制最大并发数，Semaphore 限流
- **Context Modifier** — 工具执行后注册上下文修改，批次完成后统一应用
- **工具结果预算** — token 级截断，防止单工具输出占满上下文
- **错误分类器** — 区分可重试/不可重试错误，采取不同恢复策略
- **工具执行状态追踪** — 记录工具执行中/完成状态

## Impact

- **新增 spec**: 4 个新 spec 到 `advanced-agent-features`
- **修改 spec**: `streaming-tool-execution`（与并发限流协同）
- **已有代码不变**: `dispatcher.py` 扩展，不破坏现有接口
