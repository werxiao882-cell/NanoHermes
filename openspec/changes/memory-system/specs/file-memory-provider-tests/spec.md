## ADDED Requirements

### Requirement: FileMemoryProvider 初始化 SHALL 创建文件
测试 SHALL 验证文件创建和存在性检查。

#### Scenario: 创建 MEMORY.md 和 USER.md
- **GIVEN** 空的 hermesHome 目录
- **WHEN** 调用 initialize
- **THEN** MEMORY.md 文件被创建，内容为 '# Memory\n\n'
- **AND** USER.md 文件被创建，内容为 '# User Profile\n\n'

#### Scenario: 不覆盖已存在的文件
- **GIVEN** hermesHome 目录已有 MEMORY.md
- **WHEN** 调用 initialize
- **THEN** MEMORY.md 内容保持不变

### Requirement: prefetch 方法 SHALL 返回文件内容
测试 SHALL 验证记忆内容读取。

#### Scenario: 返回完整记忆内容
- **GIVEN** MEMORY.md 包含 '- User prefers TypeScript\n'
- **WHEN** 调用 prefetch
- **THEN** 返回包含 '## Memory\n\n- User prefers TypeScript' 的字符串

#### Scenario: 空文件返回空字符串
- **GIVEN** MEMORY.md 和 USER.md 都为空
- **WHEN** 调用 prefetch
- **THEN** 返回空字符串

### Requirement: handleMemoryAction 方法 SHALL 处理 add/replace/remove
测试 SHALL 验证记忆操作。

#### Scenario: 添加记忆条目
- **GIVEN** MEMORY.md 包含 '# Memory\n\n'
- **WHEN** 调用 handleMemoryAction({ action: 'add', target: 'memory', content: 'New fact' })
- **THEN** MEMORY.md 追加 '\n- New fact\n'

#### Scenario: 替换记忆条目
- **GIVEN** MEMORY.md 包含 '- Old fact\n'
- **WHEN** 调用 handleMemoryAction({ action: 'replace', target: 'memory', content: 'New fact', search: 'Old fact' })
- **THEN** '- Old fact\n' 被替换为 '- New fact\n'

#### Scenario: 删除记忆条目
- **GIVEN** MEMORY.md 包含 '- Fact to remove\n- Keep this\n'
- **WHEN** 调用 handleMemoryAction({ action: 'remove', target: 'memory', content: 'Fact to remove' })
- **THEN** MEMORY.md 包含 '- Keep this\n'
