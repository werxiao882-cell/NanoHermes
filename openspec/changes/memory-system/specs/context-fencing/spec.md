## ADDED Requirements

### Requirement: 记忆上下文 SHALL 使用标签隔离
注入到系统提示的记忆上下文 SHALL 包裹在 `<memory-context>` 标签内。标签 SHALL 包含提供者名称属性。系统注释 SHALL 指示这是参考数据而非新用户输入。

#### Scenario: 包裹记忆上下文
- **WHEN** 记忆上下文被注入
- **THEN** 使用 `<memory-context provider="builtin">...</memory-context>` 包裹

#### Scenario: 包含系统注释
- **WHEN** 记忆上下文被包裹
- **THEN** 包含 "[System note: ... NOT new user input ...]" 注释

### Requirement: 系统 SHALL 提供 sanitize_context 函数
系统 SHALL 提供 sanitize_context 函数，使用正则表达式移除 `<memory-context>` 标签块、系统注释和孤立的标签。

#### Scenario: 移除上下文块
- **WHEN** sanitize_context 被调用
- **THEN** 所有 `<memory-context>...</memory-context>` 块被移除

#### Scenario: 移除系统注释
- **WHEN** sanitize_context 被调用
- **THEN** 所有 "[System note: ...]" 注释被移除

### Requirement: 系统 SHALL 提供 StreamingContextScrubber 类
StreamingContextScrubber SHALL 处理可能被分割跨 chunk 的标签。它 SHALL 使用状态机保留部分标签并丢弃 span 内的内容。

#### Scenario: 处理标签分割
- **WHEN** `<memory-context` 出现在一个 chunk，`>` 出现在下一个 chunk
- **THEN** 清洗器保留部分标签并正确识别 span 边界

#### Scenario: 丢弃未关闭的 span
- **WHEN** flush 时仍在 span 内
- **THEN** 丢弃剩余内容（比泄露部分记忆上下文更安全）
