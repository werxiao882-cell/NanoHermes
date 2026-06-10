# Proposal: Claude Code 能力差距补充

## Why

通过深入分析 Claude Code 的 TypeScript 源码（`claude-code-analysis/`），发现 NanoHermes 即使在 `advanced-agent-features` 中规划的 18 个子系统之外，仍然缺失 6 个关键能力。这些能力不是锦上添花，而是直接影响系统稳定性、安全性和可扩展性的核心机制。

## What Changes

- **工具并发分组** — `partition_tool_calls()` 按 `is_concurrency_safe` 决定并发/串行执行
- **工具结果预算** — `apply_tool_result_budget()` 管理大型工具结果，防止上下文爆炸
- **Context Modifier** — 工具执行后可修改全局 `ToolUseContext`，批次完成后统一应用
- **Headless/SDK Mode** — `QueryEngine` 直接实例化，无 UI 运行
- **CLAUDE.md 分级信任** — 四层信任 + `@include` 深度限制
- **MCP 工程细节** — 超时控制、重连、认证雪崩防护

## Impact

- **新增 spec**: 6 个新 spec 到 `advanced-agent-features`
- **修改 spec**: 0 个（全部为新增）
- **已有 spec 不受影响**
