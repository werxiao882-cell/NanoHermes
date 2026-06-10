## ADDED Requirements

### Requirement: Session Memory provider
系统 SHALL 实现 SessionMemoryProvider，在当前会话达到 token 阈值时自动创建会话摘要文件。摘要由后台 subagent 生成，只允许 FileEdit 工具操作精确路径。

#### Scenario: 会话达到 token 阈值触发摘要
- **WHEN** 当前会话 token 数超过 10000 且距上次摘要增长超过 5000 token 且有 3 次以上工具调用
- **THEN** 系统 SHALL 触发后台 subagent 生成会话摘要

#### Scenario: 自然断点检测
- **WHEN** 最近一轮 assistant 消息包含 tool_use
- **THEN** 系统 SHALL 推迟摘要生成，等待自然断点（无 tool_use 的轮次）

#### Scenario: Session Memory 文件安全创建
- **WHEN** 创建 Session Memory 文件
- **THEN** 目录权限 SHALL 为 0o700，文件权限 SHALL 为 0o600，使用 `wx` flag 防止覆盖

### Requirement: Agent Memory provider
系统 SHALL 实现 AgentMemoryProvider，支持 user/project/local 三种 scope。每种 scope 对应独立的记忆目录，使用 MEMORY.md 索引 + topic 文件的 memdir 结构。声明 memory 的 agent SHALL 自动获得 FileRead/FileWrite/FileEdit 工具。

#### Scenario: User scope 记忆跨项目共享
- **WHEN** agent 定义 memory scope 为 user
- **THEN** 记忆目录 SHALL 位于 `~/.nanohermes/agent-memory/<agent-type>/`

#### Scenario: Project scope 记忆在项目内共享
- **WHEN** agent 定义 memory scope 为 project
- **THEN** 记忆目录 SHALL 位于 `<cwd>/.nanohermes/agent-memory/<agent-type>/`

#### Scenario: Agent 自动获得文件操作工具
- **WHEN** agent 定义包含 memory 字段且 auto memory 启用
- **THEN** 系统 SHALL 自动将 FileRead/FileWrite/FileEdit 工具注入 agent 工具列表

### Requirement: Agent Memory Snapshot
系统 SHALL 支持 Agent Memory Snapshot 机制，允许将预置记忆打包分发。Snapshot 支持三种状态：none（无需处理）、initialize（首次初始化）、prompt-update（有新版可更新）。

#### Scenario: 首次初始化从 Snapshot 复制记忆
- **WHEN** 本地 agent memory 目录为空且存在 snapshot
- **THEN** 系统 SHALL 将 snapshot 文件复制到本地 agent memory 目录

### Requirement: Team Memory sync
系统 SHALL 实现 TeamMemoryProvider，支持按 repo 识别团队记忆命名空间，自动 pull/push 团队记忆。上传前 SHALL 执行密钥扫描。

#### Scenario: 团队记忆上传前密钥扫描
- **WHEN** 团队记忆内容包含匹配的密钥模式（如 AWS Access Key、GitHub PAT）
- **THEN** 系统 SHALL 将密钥替换为 `[REDACTED]` 后再上传

### Requirement: Relevant Memory Recall
系统 SHALL 实现 Relevant Memory Recall，在每轮对话前扫描记忆目录，通过轻量模型选择最多 5 个相关记忆文件注入上下文。已展示过的记忆 SHALL 被过滤避免重复。

#### Scenario: 选择相关记忆注入上下文
- **WHEN** 记忆目录包含 10 个 topic 文件
- **THEN** 系统 SHALL 生成文件名+描述清单，调用轻量模型选择最多 5 个最相关的文件路径注入上下文

#### Scenario: 过滤已展示的记忆
- **WHEN** 上一轮已注入 memory_a.md 和 memory_b.md
- **THEN** 本轮 Relevant Recall SHALL 跳过这两个文件，从剩余文件中选择

### Requirement: Memory entrypoint truncation
MEMORY.md 入口文件 SHALL 有硬截断保护：最多 200 行或 25KB。超出部分 SHALL 被截断并附加警告标记。

#### Scenario: MEMORY.md 超过 200 行被截断
- **WHEN** MEMORY.md 包含 300 行内容
- **THEN** 系统 SHALL 只取前 200 行，并附加 `> WARNING: MEMORY.md is truncated...` 标记
