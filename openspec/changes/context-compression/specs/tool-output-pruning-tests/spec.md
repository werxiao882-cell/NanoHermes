## ADDED Requirements

### Requirement: pruneToolOutputs 方法 SHALL 替换长输出
测试 SHALL 验证工具输出剪枝。

#### Scenario: 替换长工具输出
- **GIVEN** 消息包含 role='tool', content='A'.repeat(2000)
- **WHEN** 调用 pruneToolOutputs
- **THEN** content 被替换为 '[Old tool output cleared to save context space]'

#### Scenario: 保留短工具输出
- **GIVEN** 消息包含 role='tool', content='Short result'
- **WHEN** 调用 pruneToolOutputs
- **THEN** content 保持不变

#### Scenario: 非工具消息不变
- **GIVEN** 消息包含 role='user', content='A'.repeat(2000)
- **WHEN** 调用 pruneToolOutputs
- **THEN** 消息保持不变

### Requirement: truncateToolCallArgs 方法 SHALL 保持 JSON 有效
测试 SHALL 验证参数截断。

#### Scenario: 截断 JSON 字符串值
- **GIVEN** 参数 '{"path": "/very/long/path/...", "content": "A".repeat(500)}'
- **WHEN** 调用 truncateToolCallArgs
- **THEN** 返回有效 JSON，长字符串被截断

#### Scenario: 非 JSON 参数不变
- **GIVEN** 参数 'not valid json'
- **WHEN** 调用 truncateToolCallArgs
- **THEN** 返回 'not valid json'

#### Scenario: 嵌套对象字符串截断
- **GIVEN** 参数 '{"outer": {"inner": "A".repeat(500)}}'
- **WHEN** 调用 truncateToolCallArgs
- **THEN** 返回有效 JSON，内层字符串被截断

#### Scenario: 数组字符串截断
- **GIVEN** 参数 '["A".repeat(500), "B".repeat(500)]'
- **WHEN** 调用 truncateToolCallArgs
- **THEN** 返回有效 JSON，数组元素被截断
