## ADDED Requirements

### Requirement: 系统 SHALL 在上下文窗口满时压缩
系统 SHALL 自动检测上下文窗口使用率，当 token 数量接近模型上下文窗口限制时压缩对话上下文。中间轮次 SHALL 被摘要化，头部和尾部上下文 SHALL 被保护。

#### Scenario: 触发压缩
- **WHEN** 对话 token 数量超过压缩阈值
- **THEN** 系统压缩中间轮次为摘要

#### Scenario: 保护头部和尾部
- **WHEN** 压缩运行时
- **THEN** 前 N 条消息（头部）和最后 M 个 token（尾部）保持不变

### Requirement: 压缩 SHALL 使用辅助 LLM 模型
系统 SHALL 使用配置的辅助（便宜/快速）LLM 模型进行摘要生成。辅助模型的上下文窗口 SHALL 在启动时验证。

#### Scenario: 验证辅助模型可行性
- **WHEN** Agent 启动且压缩启用时
- **THEN** 如果辅助模型上下文窗口太小，系统发出警告

### Requirement: 摘要 SHALL 遵循结构化模板
摘要 SHALL 包含：已解决问题、待解决问题、剩余工作、关键决策、当前状态。摘要 SHALL 带有 CONTEXT COMPACTION 前缀，指示它是参考数据而非活动指令。

#### Scenario: 结构化摘要格式
- **WHEN** 摘要生成时
- **THEN** 包含已解决项、待解决项、剩余工作和当前状态部分

### Requirement: 系统 SHALL 支持迭代摘要更新
当压缩在同一会话中多次运行时，系统 SHALL 更新现有摘要而非创建新摘要。前次摘要内容 SHALL 被保留并与新信息合并。

#### Scenario: 迭代摘要更新
- **WHEN** 压缩在同一会话中第二次运行
- **THEN** 现有摘要用新信息更新，同时保留前次内容

### Requirement: 工具输出 SHALL 在摘要前剪枝
在发送给 LLM 摘要器之前，系统 SHALL 剪枝旧工具输出、用文本占位符替换图像、截断长工具调用参数同时保持 JSON 有效性。

#### Scenario: 剪枝旧工具结果
- **WHEN** 准备摘要内容时
- **THEN** 旧工具输出被替换为 "[Old tool output cleared to save context space]"

#### Scenario: 截断工具调用参数
- **WHEN** 工具调用有长字符串参数
- **THEN** 字符串值被截断，同时保持 JSON 结构有效

### Requirement: 摘要预算 SHALL 按内容大小缩放
摘要 token 预算 SHALL 与压缩内容成比例（20% 比例），最小 2000 token，最大 12000 token。系统 SHALL 使用粗略的 char-to-token 估算进行预算。

#### Scenario: 缩放摘要预算
- **WHEN** 压缩 50000 字符内容
- **THEN** 摘要预算为 10000 token（20% 比例，在最小/最大范围内）

### Requirement: 压缩 SHALL 分割会话并轮换 ID
压缩完成后，系统 SHALL 创建新会话作为延续（parent_session_id）并轮换 session_id。原始会话 SHALL 标记为 end_reason='compression'。

#### Scenario: 压缩后会话分割
- **WHEN** 压缩完成
- **THEN** 创建新会话，parent_session_id 指向原始会话
