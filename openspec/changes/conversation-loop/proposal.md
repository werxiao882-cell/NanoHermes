## 为什么

业界成熟的自进化 AI Agent 系统的对话循环 (~4300 LOC) 是核心引擎，包含模型调用、工具分发、错误分类、重试、回退、压缩触发、后轮次钩子、后台记忆/技能审查。NanoHermes 需要实现相同的对话循环架构。

## 变更内容

- 实现核心对话循环（模型调用 → 工具分发 → 重试 → 后处理）
- 实现 API 错误分类器，支持智能故障转移和恢复
- 实现后台记忆/技能审查线程
- 实现轨迹保存
- 实现 debug 模式，输出发送到模型的完整请求和模型返回的完整响应

## 能力

### New Capabilities

- `conversation-loop`: 核心对话循环，包含模型调用、工具分发、迭代预算、中断检查、后轮次钩子。
- `error-classifier`: API 错误分类器，包含错误分类学（auth、billing、rate_limit、context_overflow、format_error 等），提供恢复策略提示。
- `background-review`: 后台审查线程，fork Agent 评估对话，决定是否保存记忆或更新技能。使用工具白名单，不影响主对话。
- `debug-mode`: Debug 模式，输出发送到大模型的完整请求体（JSON）、模型返回的完整响应体（JSON）、模型的思考内容（reasoning），以及工具执行结果。通过 `--debug` 命令行参数开启。

### Modified Capabilities

<!-- 无现有能力需要修改 -->

## Impact

- 新增 `src/conversation/` 目录
- 依赖所有其他功能模块
- 无破坏性变更，从零开始构建
