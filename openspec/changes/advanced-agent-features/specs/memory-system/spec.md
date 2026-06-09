## MODIFIED Requirements

### Requirement: MemoryManager multi-layer orchestration
MemoryManager SHALL 扩展为支持多层 Memory Provider 编排。在现有 FileMemoryProvider 基础上，新增 SessionMemoryProvider、AgentMemoryProvider、TeamMemoryProvider。各层 Provider 独立开关、独立更新策略，Fan-out 容错设计保持不变。

#### Scenario: 多层 Memory 并行初始化
- **WHEN** 系统启动且 Session/Agent/Team Memory 均已启用
- **THEN** MemoryManager SHALL 并行初始化所有 Provider，单个 Provider 失败不影响其他

#### Scenario: 各层 Memory 独立开关
- **WHEN** Session Memory 被关闭但 Agent Memory 保持开启
- **THEN** MemoryManager SHALL 只跳过 SessionMemoryProvider 的初始化和钩子调用

### Requirement: Memory prefetch with relevant recall
MemoryManager 的 `prefetch_all` 方法 SHALL 扩展为支持 Relevant Memory Recall。在注入 MEMORY.md 索引内容后，额外调用 `findRelevantMemories()` 选择最多 5 个相关 topic 文件注入上下文。

#### Scenario: Prefetch 注入相关记忆
- **WHEN** 记忆目录包含多个 topic 文件
- **THEN** `prefetch_all` SHALL 先注入 MEMORY.md 索引，再调用 Relevant Recall 选择相关文件内容注入

### Requirement: Memory entrypoint truncation protection
FileMemoryProvider 的 `prefetch` 方法 SHALL 增加 MEMORY.md 硬截断保护：最多 200 行或 25KB。超出部分截断并附加警告标记。

#### Scenario: MEMORY.md 超过限制被截断
- **WHEN** MEMORY.md 包含 300 行内容
- **THEN** `prefetch` SHALL 只返回前 200 行内容，附加 `> WARNING: MEMORY.md is truncated...` 标记
