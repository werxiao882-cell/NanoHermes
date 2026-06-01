## ADDED Requirements

### Requirement: MemoryManager SHALL 编排记忆提供者
MemoryManager SHALL 管理提供者注册、生命周期调用和上下文注入。提供者 SHALL 通过 `add_provider` 方法注册。

#### Scenario: 注册提供者
- **WHEN** 提供者被添加到 MemoryManager
- **THEN** 提供者在后续生命周期调用中被包含

### Requirement: MemoryManager SHALL 强制执行单外部提供者限制
系统 SHALL 只允许 ONE 个外部提供者（非 builtin）。尝试注册第二个外部提供者 SHALL 被拒绝并记录警告。

**设计理由：** 多个外部 provider 的 prefetch 结果可能冲突，tool schema 可能重名，成本也会线性增长。Hermes 的现实取舍不是"堆多个后端"，而是"保留一套内置记忆，再允许用户额外接一个最想要的外部记忆后端"。

#### Scenario: 拒绝第二个外部提供者
- **WHEN** 第二个外部提供者被注册
- **THEN** 系统记录警告并保持第一个提供者活跃

#### Scenario: 允许多个内置提供者
- **WHEN** 多个内置提供者被注册
- **THEN** 所有内置提供者都被接受

### Requirement: MemoryManager SHALL 在正确时机调用提供者钩子
MemoryManager SHALL 在系统提示组装时调用 `build_system_prompt`，在轮次前调用 `prefetch_all`，在轮次后调用 `sync_all` 和 `queue_prefetch_all`。

#### Scenario: 构建系统提示
- **WHEN** 系统提示组装时
- **THEN** 调用所有提供者的 `system_prompt_block` 并拼接

#### Scenario: 轮次后同步
- **WHEN** 对话轮次完成
- **THEN** 调用所有提供者的 `sync_turn` 方法

### Requirement: MemoryManager SHALL 实现 Fan-out 容错
所有 fan-out 方法 SHALL 对每个 provider 独立 try/except。一个 provider 失败 SHALL 不影响其他 provider，也不影响主对话流程。

**设计理由：** 这是 graceful degradation 原则的直接应用。当前主路径通常只挂一个外部 provider，但 manager 的接口已经按多 provider 容错来设计。

#### Scenario: 单个提供者预取失败
- **WHEN** 某个提供者的 `prefetch` 抛出异常
- **THEN** 记录警告并继续调用其他提供者

#### Scenario: 单个提供者同步失败
- **WHEN** 某个提供者的 `sync_turn` 抛出异常
- **THEN** 记录警告并继续同步其他提供者

### Requirement: MemoryManager SHALL 支持双轨接线通知
系统 SHALL 支持 `on_memory_write` 钩子，当内置 `memory` 工具修改 MEMORY.md / USER.md 时，通知外部 provider。

**设计理由：** 当前处于"双轨接线"中间形态，内置记忆仍由 MemoryStore 直接加载。通过 `on_memory_write` 钩子，外部 provider（如 Honcho）可以将内置记忆的变更纳入自己的用户模型，保持两套系统同步。

#### Scenario: 内置记忆写入通知
- **WHEN** Agent 调用 `memory` 工具添加/替换/删除记忆条目
- **THEN** 调用所有外部 provider 的 `on_memory_write` 方法

### Requirement: 记忆上下文注入 SHALL 遵守字符数限制
注入到系统提示的记忆上下文 SHALL 遵守以下字符数上限：
- `memory_char_limit=2200`：MEMORY.md 最大字符数
- `user_char_limit=1375`：USER.md 最大字符数

#### Scenario: 截断过长记忆
- **WHEN** 记忆内容超过字符数限制
- **THEN** 截断到限制长度后再注入系统提示
