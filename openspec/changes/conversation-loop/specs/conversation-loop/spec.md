## ADDED Requirements

### Requirement: 系统 SHALL 实现核心对话循环
系统 SHALL 实现对话循环，包含模型调用、工具分发、迭代预算、中断检查、后轮次钩子。循环 SHALL 在达到 max_iterations 或 iteration_budget 耗尽时退出。

#### Scenario: 模型调用和工具分发
- **WHEN** 模型返回工具调用
- **THEN** 系统分发工具调用并追加结果到消息列表

#### Scenario: 达到迭代限制
- **WHEN** api_call_count 达到 max_iterations
- **THEN** 循环退出，返回最终响应

### Requirement: 系统 SHALL 分类 API 错误并提供恢复策略
系统 SHALL 提供错误分类器，将 API 错误分类为：auth、billing、rate_limit、context_overflow、format_error 等。分类结果 SHALL 包含恢复策略提示（retryable、shouldCompress、shouldRotateCredential、shouldFallback）。

#### Scenario: 分类认证错误
- **WHEN** API 返回 401 错误
- **THEN** 分类为 auth，shouldRotateCredential=true

#### Scenario: 分类上下文溢出错误
- **WHEN** API 返回上下文溢出错误
- **THEN** 分类为 context_overflow，shouldCompress=true

### Requirement: 系统 SHALL 支持后台记忆/技能审查
系统 SHALL 在每轮对话后 spawn 后台审查线程。审查线程 SHALL fork Agent，使用工具白名单（memory、skill_manage），评估对话并决定是否保存记忆或更新技能。

#### Scenario: 审查记忆
- **WHEN** 用户揭示了关于自己的信息
- **THEN** 审查线程使用 memory 工具保存

#### Scenario: 审查技能
- **WHEN** 对话中出现了新技术或工作流
- **THEN** 审查线程使用 skill_manage 更新技能

### Requirement: 系统 SHALL 支持 /sessions 命令查看历史会话
系统 SHALL 在对话循环中处理 `/sessions` 命令，列出所有历史会话（会话 ID 和标题）。

#### Scenario: 列出全部历史会话
- **WHEN** 用户输入 `/sessions`
- **THEN** 系统显示所有历史会话的 ID 和标题列表

#### Scenario: 无历史会话时
- **WHEN** 用户输入 `/sessions` 且无历史会话
- **THEN** 系统提示"暂无历史会话"

### Requirement: 系统 SHALL 支持 /resume 命令恢复历史会话
系统 SHALL 在对话循环中处理 `/resume` 命令，支持通过会话 ID 或标题恢复历史会话。

#### Scenario: 通过会话 ID 恢复
- **WHEN** 用户输入 `/resume <session_id>`
- **THEN** 系统加载该会话的历史消息并继续对话

#### Scenario: 通过标题恢复
- **WHEN** 用户输入 `/resume <标题关键词>`
- **THEN** 系统匹配标题并恢复对应会话

#### Scenario: 会话不存在时
- **WHEN** 用户输入 `/resume` 但会话不存在
- **THEN** 系统提示"会话不存在，请检查 ID 或标题"
