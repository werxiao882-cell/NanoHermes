## ADDED Requirements

### Requirement: 系统 SHALL 剪枝旧工具输出
在发送给摘要器之前，系统 SHALL 将超过阈值（1000 字符）的工具输出替换为占位符文本。

#### Scenario: 替换长工具输出
- **WHEN** 工具输出超过 1000 字符
- **THEN** 替换为 "[Old tool output cleared to save context space]"

### Requirement: 系统 SHALL 截断工具调用参数保持 JSON 有效
系统 SHALL 解析工具调用参数 JSON，截断字符串叶子节点，重新序列化。如果参数不是有效 JSON，返回原始字符串。

#### Scenario: 截断 JSON 参数
- **WHEN** 工具调用参数包含长字符串值
- **THEN** 字符串值被截断，JSON 结构保持有效

#### Scenario: 非 JSON 参数
- **WHEN** 工具调用参数不是有效 JSON
- **THEN** 返回原始字符串不变
