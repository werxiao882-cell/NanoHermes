## ADDED Requirements

### Requirement: 系统 SHALL 定义 MemoryProvider 抽象基类
系统 SHALL 提供 MemoryProvider 抽象基类（ABC），定义标准生命周期钩子。核心方法 SHALL 为抽象方法：`name`（属性）、`is_available`、`initialize`、`system_prompt_block`。可选方法 SHALL 有默认空实现。

**设计理由：** 17 个方法中只有 4 个是 abstract——其余 13 个有默认空实现，让 provider 只需实现自己关心的部分。这确保向后兼容，降低实现门槛。

#### Scenario: 实现核心方法
- **WHEN** 创建新的记忆提供者
- **THEN** 必须实现 `name` 属性、`is_available`、`initialize`、`system_prompt_block` 方法

#### Scenario: 覆盖可选钩子
- **WHEN** 提供者需要会话结束处理
- **THEN** 覆盖 `on_session_end` 方法

### Requirement: MemoryProvider SHALL 支持标准生命周期钩子
提供者 SHALL 实现：`initialize`（会话初始化）、`system_prompt_block`（系统提示块）、`prefetch`（背景回忆）、`sync_turn`（同步轮次）、`shutdown`（清理关闭）。

**方法分类：**
- **核心生命周期（4 个 @abstractmethod）**：`name`, `is_available`, `initialize`, `system_prompt_block`
- **数据流方法（默认空实现）**：`prefetch`, `queue_prefetch`, `sync_turn`, `shutdown`
- **事件钩子（可选）**：`on_turn_start`, `on_session_end`, `on_pre_compress`, `on_delegation`, `on_memory_write`
- **工具接口**：`get_tool_schemas`, `handle_tool_call`
- **配置**：`get_config_schema`, `save_config`

#### Scenario: 初始化会话
- **WHEN** Agent 启动时
- **THEN** MemoryManager 调用所有提供者的 `initialize` 方法

#### Scenario: 背景预取
- **WHEN** 新轮次开始前
- **THEN** MemoryManager 调用 `prefetch` 获取相关上下文

### Requirement: MemoryProvider SHALL 支持可选钩子
提供者 SHALL 可选择实现：`on_turn_start`、`on_session_end`、`on_pre_compress`、`on_delegation`、`on_memory_write`。

#### Scenario: 压缩前提取信息
- **WHEN** 上下文压缩触发前
- **THEN** 调用 `on_pre_compress` 在消息被丢弃前提取关键信息

#### Scenario: 委托观察
- **WHEN** 子 agent 完成任务
- **THEN** 调用父 agent 提供者的 `on_delegation` 方法

#### Scenario: 镜像内置记忆写入
- **WHEN** Agent 通过内置 `memory` 工具修改 MEMORY.md
- **THEN** 外部 provider 收到 `on_memory_write` 通知，可将变更纳入自己的用户模型

### Requirement: MemoryProvider SHALL 支持工具接口
提供者 SHALL 可选择实现 `get_tool_schemas` 和 `handle_tool_call` 方法，用于扩展 Agent 工具能力。

#### Scenario: 返回工具 schema
- **WHEN** Agent 构建工具列表时
- **THEN** 调用 `get_tool_schemas` 获取提供者定义的工具

#### Scenario: 处理工具调用
- **WHEN** Agent 调用提供者定义的工具
- **THEN** 调用 `handle_tool_call` 处理并返回结果
