## ADDED Requirements

### Requirement: 系统 SHALL 定义 ContextEngine 抽象基类
系统 SHALL 提供 ContextEngine 抽象基类（ABC），定义可插拔上下文引擎接口。核心方法 SHALL 为抽象方法：`update_from_response`、`should_compress`、`compress`。可选方法 SHALL 有默认空实现：`get_tool_schemas`、`handle_tool_call`。

**设计理由：** 第三方引擎（如 LCM、自定义摘要引擎）可替换内置压缩器，只需在配置中指定 `context.engine`。内置的 `ContextCompressor` 完整实现这个 ABC。

#### Scenario: 实现核心方法
- **WHEN** 创建新的上下文引擎
- **THEN** 必须实现 `update_from_response`、`should_compress`、`compress` 方法

#### Scenario: 覆盖可选工具接口
- **WHEN** 引擎需要向 Agent 注入额外工具（如 recall_context）
- **THEN** 覆盖 `get_tool_schemas` 和 `handle_tool_call` 方法

### Requirement: 系统 SHALL 在上下文窗口满时压缩
系统 SHALL 自动检测上下文窗口使用率，当 token 数量接近模型上下文窗口限制时压缩对话上下文。中间轮次 SHALL 被摘要化，头部和尾部上下文 SHALL 被保护。

**触发时机：**
1. **预飞行**：进入主循环前，估算 token 数，如超阈值立即压缩
2. **响应后**：API 返回 `context_length_exceeded` 或 `usage.prompt_tokens` 超阈值时压缩

#### Scenario: 预飞行压缩触发
- **WHEN** 进入主循环前估算 token 数超过阈值
- **THEN** 系统立即压缩中间轮次为摘要

#### Scenario: 响应后压缩触发
- **WHEN** API 返回 context_length_exceeded 错误
- **THEN** 系统压缩中间轮次为摘要

#### Scenario: 保护头部和尾部
- **WHEN** 压缩运行时
- **THEN** 前 3 条消息（头部）和最后 20 条消息（尾部）保持不变

### Requirement: 压缩 SHALL 使用辅助 LLM 模型
系统 SHALL 使用配置的辅助（便宜/快速）LLM 模型进行摘要生成。辅助模型的上下文窗口 SHALL 在启动时验证。

#### Scenario: 验证辅助模型可行性
- **WHEN** Agent 启动且压缩启用时
- **THEN** 如果辅助模型上下文窗口太小，系统发出警告

### Requirement: 摘要 SHALL 遵循结构化模板
摘要 SHALL 包含：目标（Goal）、进展（Progress）、关键决策（Key Decisions）、修改文件（Modified Files）、下一步（Next Steps）。摘要 SHALL 带有 CONTEXT COMPACTION 前缀，指示它是参考数据而非活动指令。

#### Scenario: 结构化摘要格式
- **WHEN** 摘要生成时
- **THEN** 包含目标、进展、关键决策、修改文件、下一步部分

### Requirement: 系统 SHALL 支持迭代摘要更新
当压缩在同一会话中多次运行时，系统 SHALL 更新现有摘要而非创建新摘要。前次摘要内容 SHALL 被保留并与新信息合并。

**设计理由：** 这让多次压缩后的摘要仍然保持连贯——不会丢失早期的重要信息。

#### Scenario: 迭代摘要更新
- **WHEN** 压缩在同一会话中第二次运行
- **THEN** 现有摘要用新信息更新，同时保留前次内容

#### Scenario: 首次摘要生成
- **WHEN** 压缩首次运行
- **THEN** 从零开始生成摘要，无前次内容

### Requirement: 工具输出 SHALL 在摘要前剪枝
在发送给 LLM 摘要器之前，系统 SHALL 剪枝旧工具输出（>200 字符替换为占位符）、截断长工具调用参数同时保持 JSON 有效性。

#### Scenario: 剪枝旧工具结果
- **WHEN** 准备摘要内容时
- **THEN** 超过 200 字符的旧工具输出被替换为 "[Tool result pruned — original too large]"

#### Scenario: 截断工具调用参数
- **WHEN** 工具调用有长字符串参数
- **THEN** 字符串值被截断，同时保持 JSON 结构有效（解析 JSON 后截断字符串叶子节点，重新序列化）

### Requirement: 摘要预算 SHALL 按内容大小缩放
摘要 token 预算 SHALL 与压缩内容成比例（20% 比例），最小 2000 token，最大 12000 token。系统 SHALL 使用粗略的 char-to-token 估算进行预算。

#### Scenario: 缩放摘要预算
- **WHEN** 压缩 50000 字符内容
- **THEN** 摘要预算为 10000 token（20% 比例，在最小/最大范围内）

### Requirement: 压缩 SHALL 分割会话并轮换 ID
压缩完成后，系统 SHALL 创建新会话作为延续（parent_session_id）并轮换 session_id。原始会话 SHALL 标记为 end_reason='compression'。

**Session Splitting 流程：**
1. 新 session 的 `parent_session_id` 指向旧 session（建立血缘链）
2. 摘要作为新 session 的第一条消息
3. 尾部保护的消息搬到新 session
4. 新 session 获得新的 IterationBudget

#### Scenario: 压缩后会话分割
- **WHEN** 压缩完成
- **THEN** 创建新会话，parent_session_id 指向原始会话

#### Scenario: 摘要作为新 session 第一条消息
- **WHEN** 新 session 创建
- **THEN** 第一条消息包含压缩摘要文本

#### Scenario: 尾部消息迁移
- **WHEN** 新 session 创建
- **THEN** 尾部保护的消息被搬到新 session

### Requirement: 系统 SHALL 在压缩前通知 Memory Provider
压缩发生前，系统 SHALL 调用 `on_pre_compress` 钩子通知所有 Memory Provider。Provider 可以在消息被压缩丢弃前提取有价值的信息。

**设计理由：** 比如 Honcho 可以从即将被压缩的对话中提取用户偏好变更，确保信息不会在压缩中丢失。

#### Scenario: on_pre_compress 钩子调用
- **WHEN** 压缩即将开始
- **THEN** 调用所有 Memory Provider 的 on_pre_compress 方法

#### Scenario: Provider 提取信息
- **WHEN** on_pre_compress 被调用
- **THEN** Provider 可以从即将被压缩的消息中提取用户偏好等信息

### Requirement: 压缩对 Prompt Cache 的影响 SHALL 可接受
压缩触发 session splitting 后，system prompt 需要重建（因为新 session 的 system prompt 需要包含摘要）。这意味着 Anthropic 的 prompt cache 会 miss 一次。

**设计理由：** 这是可接受的代价——压缩本身就意味着对话已经很长（消耗了 50%+ 上下文窗口），此时一次 cache miss 的成本远小于 `context_length_exceeded` 错误导致的对话中断。

#### Scenario: 压缩后 prompt cache miss
- **WHEN** 压缩触发 session splitting
- **THEN** system prompt 重建，prompt cache miss 一次
