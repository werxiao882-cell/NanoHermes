## ADDED Requirements

### Requirement: 系统 SHALL 剪枝旧工具输出
在发送给摘要器之前，系统 SHALL 将超过 200 字符的旧工具输出替换为占位符文本。

**设计理由：** 工具结果通常是大块 JSON（文件内容、搜索结果），压缩比很高。这是最廉价的压缩步骤，不需要 LLM 调用。

#### Scenario: 替换长工具输出
- **WHEN** 工具输出超过 200 字符
- **THEN** 替换为 "[Tool result pruned — original too large]"

#### Scenario: 保留短工具输出
- **WHEN** 工具输出少于 200 字符
- **THEN** 内容保持不变

### Requirement: 系统 SHALL 截断工具调用参数保持 JSON 有效
系统 SHALL 解析工具调用参数 JSON，截断字符串叶子节点，重新序列化。如果参数不是有效 JSON，返回原始字符串。

**关键设计决策：** 工具调用参数截断必须保持 JSON 有效性。早期实现直接切片原始 JSON 字符串，导致未终止的字符串和缺失的闭合括号，使 MiniMax 等提供商返回 400 错误。新实现解析 JSON，截断字符串叶子节点，重新序列化。

#### Scenario: 截断 JSON 参数
- **WHEN** 工具调用参数包含长字符串值（>200 字符）
- **THEN** 字符串值被截断为前 200 字符 + "...[truncated]"，JSON 结构保持有效

#### Scenario: 非 JSON 参数
- **WHEN** 工具调用参数不是有效 JSON
- **THEN** 返回原始字符串不变

#### Scenario: 嵌套对象字符串截断
- **WHEN** 工具调用参数包含嵌套对象中的长字符串
- **THEN** 递归截断所有字符串叶子节点

#### Scenario: 数组字符串截断
- **WHEN** 工具调用参数包含数组中的长字符串
- **THEN** 数组中每个字符串都被截断
