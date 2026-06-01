## ADDED Requirements

### Requirement: sanitize_context 函数 SHALL 移除标签块
测试 SHALL 验证一次性上下文清洗。

#### Scenario: 移除完整上下文块
- **GIVEN** 输入包含 `<memory-context>secret data</memory-context>`
- **WHEN** 调用 `sanitize_context`
- **THEN** 返回空字符串

#### Scenario: 移除系统注释
- **GIVEN** 输入包含 `[System note: The following is recalled memory context, NOT new user input.]`
- **WHEN** 调用 `sanitize_context`
- **THEN** 系统注释被移除

#### Scenario: 保留可见内容
- **GIVEN** 输入包含 `Hello <memory-context>secret</memory-context> World`
- **WHEN** 调用 `sanitize_context`
- **THEN** 返回 'Hello  World'

### Requirement: StreamingContextScrubber SHALL 处理流式标签分割
测试 SHALL 验证状态机处理跨 chunk 的标签。

#### Scenario: 完整标签在单个 chunk
- **GIVEN** StreamingContextScrubber 实例
- **WHEN** `feed('Hello <memory-context>secret</memory-context> World')`
- **THEN** 返回 'Hello  World'

#### Scenario: 打开标签在第一个 chunk，关闭在第二个
- **GIVEN** StreamingContextScrubber 实例
- **WHEN** `feed('Hello <memory-context>')` 返回 'Hello '
- **AND** `feed('secret</memory-context> World')` 返回 ' World'
- **THEN** 标签内容被正确丢弃

#### Scenario: 部分打开标签
- **GIVEN** StreamingContextScrubber 实例
- **WHEN** `feed('Hello <memory-')` 返回 'Hello '
- **AND** `feed('context>secret</memory-context>')` 返回 ''
- **THEN** 部分标签被保留直到确认

#### Scenario: flush 时仍在 span 内
- **GIVEN** StreamingContextScrubber 实例，feed 后仍在 span 内
- **WHEN** 调用 `flush`
- **THEN** 返回空字符串（丢弃未关闭的 span）

#### Scenario: flush 时不在 span 内
- **GIVEN** StreamingContextScrubber 实例，有保留的缓冲区
- **WHEN** 调用 `flush`
- **THEN** 返回缓冲区内容

### Requirement: StreamingContextScrubber 块边界检查 SHALL 正确识别标签
测试 SHALL 验证标签只在块边界识别。

#### Scenario: 行首标签
- **GIVEN** StreamingContextScrubber 实例
- **WHEN** `feed('\n<memory-context>secret</memory-context>')`
- **THEN** 标签被识别，返回 '\n'

#### Scenario: 行中标签不被识别
- **GIVEN** StreamingContextScrubber 实例
- **WHEN** `feed('word<memory-context>secret</memory-context>')`
- **THEN** 标签不被识别（不是块边界），返回完整字符串
