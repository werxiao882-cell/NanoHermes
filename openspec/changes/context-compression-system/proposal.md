## Why

NanoHermes 需要实现完整的上下文压缩系统，使 Agent 能够处理超出模型上下文窗口的长对话。业界成熟的自进化 AI Agent 系统使用辅助 LLM 模型自动压缩长对话的上下文，将中间轮次摘要化，同时保护头部和尾部上下文。

**为什么长对话是个工程问题：** LLM 上下文窗口有限（128K-200K tokens），30 次工具调用可能消耗 80K+ tokens，超限会返回 `context_length_exceeded` 错误。

初始实现后，需要增强压缩系统的生产级稳定性和可观测性：防止压缩循环、监控压缩效率、支持多种触发模式、验证压缩质量。

## What Changes

### 核心压缩能力
- 实现 ContextEngine 抽象基类（可插拔扩展点）
- 实现 ContextCompressor 分层压缩策略：Tool Output Pruning → Head/Tail 保护 → Middle 摘要 → Session Splitting
- 实现辅助 LLM 客户端用于结构化摘要生成
- 实现工具输出剪枝和参数截断（保持 JSON 有效性）
- 实现迭代摘要更新（保持多次压缩后的连贯性）
- 实现 `on_pre_compress` 钩子通知 Memory Provider 提取信息

### 生产级增强
- 新增熔断器模式（Circuit Breaker）防止压缩循环，连续失败后自动降级
- 新增动态预算追踪（Budget Tracker）监控压缩效率和 token 使用情况
- 新增多种压缩触发模式：Reactive（响应式）、Micro（微压缩）、Snip（裁剪）
- 新增压缩质量验证器（Validator）评估信息保留度和摘要质量

## Capabilities

### New Capabilities

- `context-engine-interface`: ContextEngine 抽象基类，定义可插拔上下文引擎接口。包含 3 个核心抽象方法（`update_from_response`, `should_compress`, `compress`）和可选工具接口。
- `context-compressor`: 上下文压缩引擎，实现分层压缩策略。检测上下文窗口使用率，使用辅助 LLM 生成结构化摘要，保护头部和尾部上下文。摘要预算按比例缩放（20%），最小 2000 token，最大 12000 token。
- `auxiliary-client`: 辅助 LLM 客户端，用于压缩等后台任务。支持自动提供商解析和连接错误处理。
- `tool-output-pruning`: 工具输出剪枝，在发送给 LLM 摘要器之前剪枝旧工具输出（>200 字符替换为占位符）、截断长工具调用参数（解析 JSON 后截断字符串叶子节点，保持 JSON 有效性）。
- `session-splitting`: 压缩触发时创建新 session，`parent_session_id` 指向旧 session（建立血缘链），摘要作为新 session 第一条消息，尾部保护消息搬到新 session。
- `on-pre-compress-hook`: 压缩前通知 Memory Provider 提取有价值信息，确保信息不丢失。
- `circuit-breaker`: 熔断器模式实现，防止压缩循环，支持 CLOSED/OPEN/HALF_OPEN 状态转换和冷却期机制。
- `budget-tracker`: 动态预算追踪，监控压缩前后 token 使用量、压缩效率和历史统计。
- `compression-modes`: 多种压缩触发模式，包括 Reactive（阈值触发）、Micro（频繁小压缩）、Snip（精准裁剪）。
- `compression-validator`: 压缩质量验证，评估信息保留度、摘要长度和关键信息完整性。

### Modified Capabilities

<!-- 无现有能力需要修改 -->

## Impact

- 新增 `src/compression/` 目录，包含 11 个文件（engine, compressor, auxiliary, pruning, feasibility, circuit_breaker, budget_tracker, modes, validator + ARCHITECTURE.md + __init__.py）
- 依赖辅助 LLM 提供商配置
- 压缩触发时会分割会话并轮换 session_id（通过 SessionDB 的 `parent_session_id` 建立血缘链）
- 无破坏性变更，从零开始构建
- 预留外部 ContextEngine 插件接口（LCM、自定义摘要引擎）
