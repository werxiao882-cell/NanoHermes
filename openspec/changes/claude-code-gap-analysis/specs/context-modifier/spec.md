## ADDED Requirements

### Requirement: Context modifier registry

系统 SHALL 实现 `ContextModifier` 类，允许工具在执行后注册对全局 `ToolUseContext` 的修改。修改在批次完成后统一应用，避免中间状态不一致。

#### Scenario: 文件编辑后更新文件附件列表

- **WHEN** `write_file` 或 `patch` 工具成功执行
- **THEN** 工具注册 `ContextModifier` 修改：将编辑过的文件加入文件附件列表
- **AND** 修改在整批工具完成后统一应用

#### Scenario: 工作目录变更后更新上下文

- **WHEN** `terminal` 工具执行了 `cd /some/path`
- **THEN** 工具注册 `ContextModifier` 修改：更新当前工作目录为 `/some/path`
- **AND** 后续工具调用使用新的工作目录

#### Scenario: 批次完成后统一应用

- **WHEN** 一批 3 个工具同时执行，其中 2 个注册了 context 修改
- **THEN** 3 个工具全部完成后，2 个修改按注册顺序应用
- **AND** 如果修改冲突（如两个工具同时改工作目录），后注册的覆盖先注册的

### Requirement: Context modifier types

`ContextModifier` SHALL 支持以下修改类型：

| 类型 | 说明 |
|------|------|
| `file_attachment_update` | 文件编辑后加入附件列表 |
| `working_directory_change` | 更新当前工作目录 |
| `available_tools_change` | 动态可用工具集变更 |
| `environment_variable_set` | 设置环境变量 |

#### Scenario: 修改类型被正确分类

- **WHEN** 工具注册 `working_directory_change` 修改
- **THEN** 修改被归类到对应类型
- **AND** 同一类型的多个修改按策略合并或覆盖

### Requirement: Context modifier logging

所有 context 修改 SHALL 被记录到日志，便于调试和审计。

#### Scenario: 修改被记录

- **WHEN** context modifier 被应用
- **THEN** 日志记录：工具名、修改类型、修改内容
- **AND** 格式: `[context-modifier] {tool_name}: {modifier_type} → {new_value}`
