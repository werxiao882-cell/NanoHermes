## ADDED Requirements

### Requirement: FTS5 虚拟表 SHALL 正确创建
测试 SHALL 验证 messages_fts 和 messages_fts_trigram 虚拟表在初始化时被创建。

#### Scenario: 创建标准 FTS5 表
- **GIVEN** SessionDB 实例
- **WHEN** 初始化完成
- **THEN** messages_fts 虚拟表存在
- **AND** 使用 unicode61 分词器

#### Scenario: 创建 trigram FTS5 表
- **GIVEN** SessionDB 实例
- **WHEN** 初始化完成
- **THEN** messages_fts_trigram 虚拟表存在
- **AND** 使用 trigram 分词器

### Requirement: FTS 触发器 SHALL 保持索引同步
测试 SHALL 验证 INSERT、DELETE、UPDATE 触发器正确同步 FTS 索引。

#### Scenario: 插入消息同步到 FTS
- **GIVEN** SessionDB 实例
- **WHEN** 插入一条新消息到 messages 表
- **THEN** messages_fts 表包含该消息的 content
- **AND** messages_fts_trigram 表包含该消息的 content

#### Scenario: 删除消息同步到 FTS
- **GIVEN** SessionDB 实例，已有一条消息
- **WHEN** 从 messages 表删除该消息
- **THEN** messages_fts 表不再包含该消息
- **AND** messages_fts_trigram 表不再包含该消息

#### Scenario: 更新消息同步到 FTS
- **GIVEN** SessionDB 实例，已有一条消息
- **WHEN** 更新 messages 表的 content 字段
- **THEN** messages_fts 表包含更新后的 content
- **AND** messages_fts_trigram 表包含更新后的 content

### Requirement: 跨会话搜索 SHALL 返回正确结果
测试 SHALL 验证搜索功能返回所有会话中匹配的消息。

#### Scenario: 搜索所有会话
- **GIVEN** SessionDB 实例，包含 3 个会话的消息
- **WHEN** 搜索关键词 "bug"
- **THEN** 返回所有包含 "bug" 的消息，跨所有会话
- **AND** 结果包含 session_id、role、content、timestamp

#### Scenario: 按会话过滤搜索
- **GIVEN** SessionDB 实例，包含多个会话
- **WHEN** 搜索关键词 "error" 并指定 session_id
- **THEN** 只返回该会话中匹配的消息

#### Scenario: 搜索无结果
- **GIVEN** SessionDB 实例
- **WHEN** 搜索不存在的关键词
- **THEN** 返回空数组

### Requirement: CJK 子串搜索 SHALL 正常工作
测试 SHALL 验证 trigram 分词器支持中文字符串搜索。

#### Scenario: 中文子串搜索
- **GIVEN** SessionDB 实例，包含中文消息 "这是一个测试消息"
- **WHEN** 搜索 "测试"
- **THEN** 返回包含该子串的消息

#### Scenario: 日文子串搜索
- **GIVEN** SessionDB 实例，包含日文消息 "これはテストメッセージです"
- **WHEN** 搜索 "テスト"
- **THEN** 返回包含该子串的消息

#### Scenario: 混合语言搜索
- **GIVEN** SessionDB 实例，包含混合语言消息 "bug 修复完成，测试通过"
- **WHEN** 搜索 "修复"
- **THEN** 返回包含该子串的消息

### Requirement: FTS 索引 SHALL 包含 tool_name 和 tool_calls
测试 SHALL 验证 FTS 索引包含 tool_name 和 tool_calls 字段。

#### Scenario: 搜索工具名称
- **GIVEN** SessionDB 实例，包含 tool_name="read_file" 的消息
- **WHEN** 搜索 "read_file"
- **THEN** 返回该消息

#### Scenario: 搜索工具调用参数
- **GIVEN** SessionDB 实例，包含 tool_calls='{"path": "/test/file.ts"}' 的消息
- **WHEN** 搜索 "file.ts"
- **THEN** 返回该消息
