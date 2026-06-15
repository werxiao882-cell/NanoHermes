## 修改需求

### 需求：技能系统集成 Curator 到运行时

系统应实例化并定期调用 `Curator` 管理技能生命周期。

#### 场景：TUI 启动时实例化 Curator
- **当** TUI 应用初始化
- **则** 系统使用配置的参数创建 `Curator` 实例
- **则** 系统将 Curator 实例存储在 `TUIApp.curator` 属性中
- **则** 系统在启动时调用一次 `curator.maybe_run()`

#### 场景：Curator 定期调用
- **当** 对话循环完成（LOOP_END 事件）
- **则** 系统检查距离上次 Curator 运行是否已过 7 天
- **则** 如果间隔已到，系统调用 `curator.maybe_run()`
- **则** Curator 评估技能使用情况并转换状态

#### 场景：Curator 遵守配置
- **当** `background_tasks.skill_review.curator_enabled` 设置为 `false`
- **则** 系统不实例化 Curator
- **则** 技能生命周期管理被禁用
- **则** 技能无限期保持当前状态

**理由**：此修改激活当前存在但从未实例化的 `Curator` 类。Curator 基于使用模式提供有价值的技能生命周期管理（active → stale → archived）。

**迁移**：无需迁移。Curator 是新的运行时组件，因此启用它不会影响现有技能。禁用它只是停止自动状态转换。

### 需求：技能系统修复 fork_agent 工具调用

系统应修复 `background_review.py` 中的 `fork_agent()` 函数，正确处理工具调用。

#### 场景：fork_agent 处理工具调用
- **当** fork 代理收到包含 `tool_calls` 的响应
- **则** 系统遍历工具调用
- **则** 系统根据 `REVIEW_TOOL_WHITELIST` 过滤工具
- **则** 系统通过 `tool_dispatch` 执行允许的工具
- **则** 系统将工具结果追加到消息
- **则** 系统继续迭代（最多 5 次）

#### 场景：fork_agent 遵守工具白名单
- **当** fork 代理尝试调用 `terminal`（不在白名单中）
- **则** 系统拒绝工具调用，返回错误："工具在 fork 代理中不允许使用"
- **则** 系统将错误追加到消息
- **则** 系统继续迭代

#### 场景：fork_agent 处理内容响应
- **当** fork 代理收到包含内容的响应（无 tool_calls）
- **则** 系统返回包含内容的最终结果
- **则** 系统在 DEBUG 级别记录完成

#### 场景：fork_agent 达到迭代限制
- **当** fork 代理完成 5 次迭代
- **则** 系统终止执行
- **则** 系统返回最后的响应（如果有）
- **则** 系统记录警告："fork_agent 达到迭代限制"

**理由**：当前的 `fork_agent()` 实现存在关键 bug，它在第一次收到内容响应时立即返回，不处理工具调用。这使得工具白名单机制无效，并阻止 fork 代理实际使用 `memory` 或 `skill_manage` 等工具。

**迁移**：无需迁移。这是一个 bug 修复，使 `fork_agent()` 按原始设计工作。调用 `fork_agent()` 的现有代码将受益于修复，无需更改。

### 需求：技能系统集成 BackgroundTaskScheduler

系统应将技能审查注册为调度器的后台任务。

#### 场景：技能审查任务注册
- **当** 技能系统模块加载
- **则** 系统向调度器注册任务：`scheduler.register_task("skill_review", handler, trigger)`
- **则** handler 是 `spawn_background_review`，`review_type="skill"`
- **则** trigger 是 `LOOP_END` 事件，带间隔检查

#### 场景：技能审查任务执行
- **当** 调度器触发技能审查任务
- **则** 系统生成后台线程
- **则** 系统调用 `spawn_background_review(messages, model_caller, tool_dispatch, "skill")`
- **则** 系统使用 `_SKILL_REVIEW_PROMPT` 模板
- **则** 系统在 INFO 级别记录提议

#### 场景：技能审查任务遵守配置
- **当** `background_tasks.skill_review.enabled` 设置为 `false`
- **则** 任务不注册到调度器
- **则** 技能审查永不触发

**理由**：此修改将技能审查集成到统一的后台任务系统，确保一致的并发控制、日志记录和配置管理。

**迁移**：无需迁移。技能审查是新的后台任务，因此启用它不会影响现有功能。禁用它只是停止自动技能提议。
