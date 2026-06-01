## ADDED Requirements

### Requirement: set_session_title 方法 SHALL 正确设置标题

测试 SHALL 验证设置会话标题并检查唯一性。

#### Scenario: 设置新标题
- **GIVEN** SessionDB 实例，包含 session-1
- **WHEN** 调用 set_session_title('session-1', 'My Session')
- **THEN** title 字段更新为 'My Session'

#### Scenario: 标题唯一性检查
- **GIVEN** SessionDB 实例，session-1 和 session-2 已存在
- **WHEN** 调用 set_session_title('session-2', 'My Session')
- **THEN** 抛出唯一性约束错误

#### Scenario: 更新自己的标题
- **GIVEN** SessionDB 实例，session-1 标题为 'My Session'
- **WHEN** 调用 set_session_title('session-1', 'New Title')
- **THEN** 标题更新成功

### Requirement: sanitize_title 方法 SHALL 正确清理标题

测试 SHALL 验证剥离控制字符、折叠空白、限制长度。

#### Scenario: 剥离控制字符
- **GIVEN** SessionDB 实例
- **WHEN** sanitize_title('Hello\u200bWorld')
- **THEN** 返回 'HelloWorld'

#### Scenario: 折叠空白
- **WHEN** sanitize_title('  Hello   World  ')
- **THEN** 返回 'Hello World'

#### Scenario: 标题过长
- **WHEN** sanitize_title('A' * 101)
- **THEN** 抛出 ValueError "Title too long (101 chars, max 100)"

#### Scenario: 空标题
- **WHEN** sanitize_title('   ')
- **THEN** 抛出 ValueError

### Requirement: resolve_session_by_title 方法 SHALL 解析标题到会话 ID

测试 SHALL 验证精确匹配和编号变体匹配。

#### Scenario: 精确标题匹配
- **GIVEN** SessionDB 实例，包含标题 'My Session'
- **WHEN** 调用 resolve_session_by_title('My Session')
- **THEN** 返回该会话的 ID

#### Scenario: 编号变体匹配
- **GIVEN** SessionDB 实例，包含标题 'My Session #2'、'My Session #3'
- **WHEN** 调用 resolve_session_by_title('My Session')
- **THEN** 返回最新的编号变体的会话 ID

#### Scenario: 标题不存在
- **WHEN** 调用 resolve_session_by_title('Non-existent')
- **THEN** 返回 None

### Requirement: get_next_title_in_lineage 方法 SHALL 生成下一个标题

测试 SHALL 验证生成 lineage 中的下一个编号标题。

#### Scenario: 生成第一个编号标题
- **GIVEN** SessionDB 实例，包含标题 'My Session'
- **WHEN** 调用 get_next_title_in_lineage('My Session')
- **THEN** 返回 'My Session #2'

#### Scenario: 生成后续编号标题
- **GIVEN** SessionDB 实例，包含标题 'My Session'、'My Session #2'
- **WHEN** 调用 get_next_title_in_lineage('My Session')
- **THEN** 返回 'My Session #3'

#### Scenario: 处理现有编号后缀
- **WHEN** 调用 get_next_title_in_lineage('My Session #2')
- **THEN** 返回 'My Session #3'
