## ADDED Requirements

### Requirement: createSession 方法 SHALL 正确创建会话
测试 SHALL 验证会话创建的幂等性和字段设置。

#### Scenario: 创建新会话
- **GIVEN** SessionDB 实例
- **WHEN** 调用 createSession('session-1', 'cli', { model: 'gpt-4' })
- **THEN** sessions 表包含新记录
- **AND** id='session-1', source='cli', model='gpt-4'
- **AND** started_at 为当前时间
- **AND** 其他字段为默认值

#### Scenario: 幂等创建
- **GIVEN** SessionDB 实例，已创建 session-1
- **WHEN** 再次调用 createSession('session-1', 'cli')
- **THEN** 不抛出错误
- **AND** sessions 表只有一条 session-1 记录

#### Scenario: 创建会话带完整参数
- **GIVEN** SessionDB 实例
- **WHEN** 调用 createSession 带 user_id、parent_session_id 等参数
- **THEN** 所有参数被正确存储

### Requirement: endSession 和 reopenSession 方法 SHALL 正确工作
测试 SHALL 验证会话结束和恢复的生命周期。

#### Scenario: 结束会话
- **GIVEN** SessionDB 实例，已创建 session-1
- **WHEN** 调用 endSession('session-1', 'user_exit')
- **THEN** ended_at 被设置为当前时间
- **AND** end_reason='user_exit'

#### Scenario: 已结束会话不重复结束
- **GIVEN** SessionDB 实例，session-1 已结束
- **WHEN** 调用 endSession('session-1', 'timeout')
- **THEN** ended_at 和 end_reason 保持不变（第一次的 end_reason 获胜）

#### Scenario: 恢复会话
- **GIVEN** SessionDB 实例，session-1 已结束
- **WHEN** 调用 reopenSession('session-1')
- **THEN** ended_at 被设置为 NULL
- **AND** end_reason 被设置为 NULL

### Requirement: parent_session_id lineage 追踪 SHALL 正确工作
测试 SHALL 验证会话 lineage 的创建和查询。

#### Scenario: 创建压缩延续会话
- **GIVEN** SessionDB 实例，session-1 已结束（end_reason='compression'）
- **WHEN** 创建 session-2，parent_session_id='session-1'
- **THEN** session-2 的 parent_session_id 指向 session-1

#### Scenario: 获取压缩延续 tip
- **GIVEN** SessionDB 实例，session-1 → session-2 → session-3 的压缩延续链
- **WHEN** 调用 getCompressionTip('session-1')
- **THEN** 返回 'session-3'（最新的延续）

#### Scenario: 排除委托子节点
- **GIVEN** SessionDB 实例，session-1 未结束，session-2 的 parent_session_id='session-1'
- **WHEN** 调用 getCompressionTip('session-1')
- **THEN** 返回 'session-1'（session-2 不是压缩延续）

### Requirement: updateTokenCounts 方法 SHALL 正确更新计数
测试 SHALL 验证增量和绝对模式的 token 计数更新。

#### Scenario: 增量更新 token 计数
- **GIVEN** SessionDB 实例，session-1 有 input_tokens=100
- **WHEN** 调用 updateTokenCounts('session-1', { inputTokens: 50 }, { absolute: false })
- **THEN** input_tokens 变为 150（100 + 50）

#### Scenario: 绝对更新 token 计数
- **GIVEN** SessionDB 实例，session-1 有 input_tokens=100
- **WHEN** 调用 updateTokenCounts('session-1', { inputTokens: 500 }, { absolute: true })
- **THEN** input_tokens 变为 500

#### Scenario: 更新模型信息
- **GIVEN** SessionDB 实例，session-1 无 model
- **WHEN** 调用 updateTokenCounts 带 model 参数
- **THEN** model 字段被设置为新值

### Requirement: getSession 方法 SHALL 返回正确会话
测试 SHALL 验证会话查询功能。

#### Scenario: 获取存在的会话
- **GIVEN** SessionDB 实例，已创建 session-1
- **WHEN** 调用 getSession('session-1')
- **THEN** 返回包含所有字段的会话对象

#### Scenario: 获取不存在的会话
- **GIVEN** SessionDB 实例
- **WHEN** 调用 getSession('non-existent')
- **THEN** 返回 null
