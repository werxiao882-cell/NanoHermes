## ADDED Requirements

### Requirement: setSessionTitle 方法 SHALL 正确设置标题
测试 SHALL 验证标题设置、唯一性检查和清理。

#### Scenario: 设置新标题
- **GIVEN** SessionDB 实例，session-1 无标题
- **WHEN** 调用 setSessionTitle('session-1', 'My Session')
- **THEN** title 字段被设置为 'My Session'

#### Scenario: 标题唯一性检查
- **GIVEN** SessionDB 实例，session-1 和 session-2 都存在
- **WHEN** session-1 标题为 'My Session'，尝试设置 session-2 标题为 'My Session'
- **THEN** 抛出错误 "Title 'My Session' is already in use by session session-1"

#### Scenario: 更新自己的标题
- **GIVEN** SessionDB 实例，session-1 标题为 'Old Title'
- **WHEN** 调用 setSessionTitle('session-1', 'New Title')
- **THEN** 标题被更新为 'New Title'

### Requirement: sanitizeTitle 方法 SHALL 正确清理标题
测试 SHALL 验证控制字符剥离、空白折叠和长度限制。

#### Scenario: 剥离控制字符
- **WHEN** sanitizeTitle('Hello\u200bWorld')
- **THEN** 返回 'HelloWorld'

#### Scenario: 折叠空白
- **WHEN** sanitizeTitle('  Hello   World  ')
- **THEN** 返回 'Hello World'

#### Scenario: 标题过长
- **WHEN** sanitizeTitle('A'.repeat(101))
- **THEN** 抛出 ValueError "Title too long (101 chars, max 100)"

#### Scenario: 空标题
- **WHEN** sanitizeTitle('   ')
- **THEN** 返回 null

### Requirement: resolveSessionByTitle 方法 SHALL 解析标题到会话 ID
测试 SHALL 验证精确匹配、编号变体匹配和 lineage 解析。

#### Scenario: 精确标题匹配
- **GIVEN** SessionDB 实例，session-1 标题为 'My Session'
- **WHEN** 调用 resolveSessionByTitle('My Session')
- **THEN** 返回 'session-1'

#### Scenario: 编号变体匹配
- **GIVEN** SessionDB 实例，session-1 标题为 'My Session'，session-2 标题为 'My Session #2'
- **WHEN** 调用 resolveSessionByTitle('My Session')
- **THEN** 返回 'session-2'（最新的编号变体）

#### Scenario: 标题不存在
- **GIVEN** SessionDB 实例
- **WHEN** 调用 resolveSessionByTitle('Non-existent')
- **THEN** 返回 null

### Requirement: getNextTitleInLineage 方法 SHALL 生成下一个标题
测试 SHALL 验证 lineage 中的下一个编号标题生成。

#### Scenario: 生成第一个编号标题
- **GIVEN** SessionDB 实例，session-1 标题为 'My Session'
- **WHEN** 调用 getNextTitleInLineage('My Session')
- **THEN** 返回 'My Session #2'

#### Scenario: 生成后续编号标题
- **GIVEN** SessionDB 实例，已有 'My Session'、'My Session #2'、'My Session #3'
- **WHEN** 调用 getNextTitleInLineage('My Session')
- **THEN** 返回 'My Session #4'

#### Scenario: 剥离现有编号后缀
- **GIVEN** SessionDB 实例，已有 'My Session'、'My Session #2'
- **WHEN** 调用 getNextTitleInLineage('My Session #2')
- **THEN** 返回 'My Session #3'
