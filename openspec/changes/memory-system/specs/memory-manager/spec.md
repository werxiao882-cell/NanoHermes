## ADDED Requirements

### Requirement: MemoryManager SHALL 编排记忆提供者
MemoryManager SHALL 管理提供者注册、生命周期调用和上下文注入。提供者 SHALL 通过 addProvider 方法注册。

#### Scenario: 注册提供者
- **WHEN** 提供者被添加到 MemoryManager
- **THEN** 提供者在后续生命周期调用中被包含

### Requirement: MemoryManager SHALL 强制执行单外部提供者限制
系统 SHALL 只允许 ONE 个外部提供者（非 builtin）。尝试注册第二个外部提供者 SHALL 被拒绝并记录警告。

#### Scenario: 拒绝第二个外部提供者
- **WHEN** 第二个外部提供者被注册
- **THEN** 系统记录警告并保持第一个提供者活跃

#### Scenario: 允许多个内置提供者
- **WHEN** 多个内置提供者被注册
- **THEN** 所有内置提供者都被接受

### Requirement: MemoryManager SHALL 在正确时机调用提供者钩子
MemoryManager SHALL 在系统提示组装时调用 buildSystemPrompt，在轮次前调用 prefetchAll，在轮次后调用 syncAll 和 queuePrefetchAll。

#### Scenario: 构建系统提示
- **WHEN** 系统提示组装时
- **THEN** 调用所有提供者的 systemPromptBlock 并拼接

#### Scenario: 轮次后同步
- **WHEN** 对话轮次完成
- **THEN** 调用所有提供者的 syncTurn 方法
