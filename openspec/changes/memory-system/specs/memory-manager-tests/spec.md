## ADDED Requirements

### Requirement: add_provider 方法 SHALL 管理提供者注册
测试 SHALL 验证提供者注册和单外部提供者限制。

#### Scenario: 注册内置提供者
- **GIVEN** MemoryManager 实例
- **WHEN** 添加 `name='builtin'` 的提供者
- **THEN** 提供者被添加到 providers 列表

#### Scenario: 注册第一个外部提供者
- **GIVEN** MemoryManager 实例
- **WHEN** 添加 `name='honcho'` 的提供者
- **THEN** 提供者被添加到 providers 列表
- **AND** `_external_provider_count` 变为 1

#### Scenario: 拒绝第二个外部提供者
- **GIVEN** MemoryManager 实例，已有一个外部提供者
- **WHEN** 添加 `name='mem0'` 的提供者
- **THEN** 提供者不被添加
- **AND** 记录警告日志

### Requirement: build_system_prompt 方法 SHALL 拼接提供者提示
测试 SHALL 验证系统提示构建。

#### Scenario: 单个提供者提示
- **GIVEN** MemoryManager 实例，有一个提供者返回 "Memory block"
- **WHEN** 调用 `build_system_prompt`
- **THEN** 返回 "Memory block"

#### Scenario: 多个提供者提示
- **GIVEN** MemoryManager 实例，有两个提供者分别返回 "Block 1" 和 "Block 2"
- **WHEN** 调用 `build_system_prompt`
- **THEN** 返回 "Block 1\n\nBlock 2"

#### Scenario: 空提示被跳过
- **GIVEN** MemoryManager 实例，有提供者返回空字符串
- **WHEN** 调用 `build_system_prompt`
- **THEN** 空字符串不被包含

### Requirement: prefetch_all 方法 SHALL 包裹上下文
测试 SHALL 验证预取上下文包裹。

#### Scenario: 包裹记忆上下文
- **GIVEN** MemoryManager 实例，提供者返回 "User prefers concise responses"
- **WHEN** 调用 `prefetch_all('Hello')`
- **THEN** 返回 `<memory-context provider="builtin">...User prefers concise responses...</memory-context>`

### Requirement: sync_all 方法 SHALL 实现 Fan-out 容错
测试 SHALL 验证一个 provider 失败不影响其他 provider。

#### Scenario: 单个提供者同步失败
- **GIVEN** MemoryManager 实例，有两个提供者
- **WHEN** 第一个提供者的 `sync_turn` 抛出异常
- **THEN** 第二个提供者仍被调用
- **AND** 记录警告日志

#### Scenario: 所有提供者同步成功
- **GIVEN** MemoryManager 实例，有两个提供者
- **WHEN** 调用 `sync_all('user', 'assistant')`
- **THEN** 两个提供者的 `sync_turn` 都被调用
