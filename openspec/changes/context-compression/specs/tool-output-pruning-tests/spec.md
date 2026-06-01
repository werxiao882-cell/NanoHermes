## ADDED Requirements

### Requirement: prune_tool_outputs 方法 SHALL 替换长工具输出
测试 SHALL 验证工具输出剪枝。

#### Scenario: 替换长工具输出
- **GIVEN** 消息列表包含超过 200 字符的 tool 消息
- **WHEN** 调用 prune_tool_outputs
- **THEN** 长工具输出被替换为 "[Tool result pruned — original too large]"

#### Scenario: 保留短工具输出
- **GIVEN** 消息列表包含少于 200 字符的 tool 消息
- **WHEN** 调用 prune_tool_outputs
- **THEN** 短工具输出保持不变

#### Scenario: 非工具消息不变
- **GIVEN** 消息列表包含 user/assistant 消息
- **WHEN** 调用 prune_tool_outputs
- **THEN** 非工具消息保持不变

### Requirement: truncate_tool_call_args 方法 SHALL 保持 JSON 有效性
测试 SHALL 验证 JSON 参数截断。

#### Scenario: 截断 JSON 字符串值
- **GIVEN** 工具调用参数包含长字符串值（>200 字符）
- **WHEN** 调用 truncate_tool_call_args
- **THEN** 字符串值被截断，JSON 结构保持有效

#### Scenario: 非 JSON 参数不变
- **GIVEN** 工具调用参数不是有效 JSON
- **WHEN** 调用 truncate_tool_call_args
- **THEN** 返回原始字符串不变

#### Scenario: 嵌套对象字符串截断
- **GIVEN** 工具调用参数包含嵌套对象中的长字符串
- **WHEN** 调用 truncate_tool_call_args
- **THEN** 递归截断所有字符串叶子节点

#### Scenario: 数组字符串截断
- **GIVEN** 工具调用参数包含数组中的长字符串
- **WHEN** 调用 truncate_tool_call_args
- **THEN** 数组中每个字符串都被截断
