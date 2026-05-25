## ADDED Requirements

### Requirement: 系统 SHALL 提供内置文件记忆提供者
系统 SHALL 提供 FileMemoryProvider，使用 MEMORY.md 和 USER.md 文件存储记忆。提供者 SHALL 始终可用。

#### Scenario: 初始化文件提供者
- **WHEN** FileMemoryProvider 初始化时
- **THEN** 确保 MEMORY.md 和 USER.md 文件存在

#### Scenario: 预取记忆上下文
- **WHEN** prefetch 被调用
- **THEN** 读取 MEMORY.md 和 USER.md 内容并返回

### Requirement: 文件提供者 SHALL 支持 add/replace/remove 操作
系统 SHALL 通过 memory 工具支持添加、替换、删除记忆条目。

#### Scenario: 添加记忆条目
- **WHEN** action='add' 被调用
- **THEN** 新条目追加到对应文件末尾

#### Scenario: 替换记忆条目
- **WHEN** action='replace' 被调用
- **THEN** 搜索匹配的条目并替换为新内容

#### Scenario: 删除记忆条目
- **WHEN** action='remove' 被调用
- **THEN** 从文件中删除匹配的条目

### Requirement: 文件提供者 SHALL 返回 memory 工具 schema
系统 SHALL 返回 memory 工具的 OpenAI 函数调用格式 schema，包含 action、target、content、search 参数。

#### Scenario: 返回工具 schema
- **WHEN** getToolSchemas 被调用
- **THEN** 返回包含 memory 工具定义的数组
