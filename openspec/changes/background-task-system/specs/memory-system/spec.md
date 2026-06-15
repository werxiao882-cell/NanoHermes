## 修改需求

### 需求：记忆提供者实现 on_session_end 钩子

系统应在 `FileMemoryProvider` 中实现 `on_session_end()` 方法，支持自动记忆提取。

#### 场景：会话结束触发记忆提取
- **当** `MemoryManager.on_session_end()` 被调用
- **则** 系统调用 `FileMemoryProvider.on_session_end(messages)`
- **则** 提供者检查 `background_tasks.memory_flush.enabled` 是否为 true
- **则** 如果启用，提供者触发后台记忆提取

#### 场景：记忆提取使用最近消息
- **当** `on_session_end()` 被调用，传入完整消息历史
- **则** 提供者提取最近 20 条消息（10 轮）
- **则** 提供者将每条消息截断到 500 字符
- **则** 提供者格式化消息供 LLM 审查

#### 场景：记忆提取调用 LLM
- **当** 提供者准备提取请求
- **则** 提供者调用 `model_caller(messages, tools=None)`
- **则** 提供者使用 `_MEMORY_REVIEW_PROMPT` 模板
- **则** 提供者设置 `max_tokens=1000` 限制响应

#### 场景：记忆提取写入文件
- **当** LLM 返回提取结果
- **则** 提供者解析结果中的记忆条目
- **则** 提供者对每个条目调用 `memory` 工具，`action=add`
- **则** 提供者根据类型写入 MEMORY.md 或 USER.md

**理由**：此修改激活当前空的 `on_session_end()` 钩子，启用自动记忆提取，无需用户显式命令。

**迁移**：无需迁移。该钩子当前什么都不做（`pass`），因此添加实现是向后兼容的。如果用户偏好手动记忆管理，可以通过配置禁用。

### 需求：记忆管理器协调会话结束

系统应在会话结束时协调所有提供者的记忆提取。

#### 场景：会话结束协调
- **当** TUI 检测到会话结束（用户退出、超时等）
- **则** TUI 调用 `MemoryManager.on_session_end(messages)`
- **则** 管理器遍历所有注册的提供者
- **则** 管理器调用每个提供者的 `on_session_end()` 方法

#### 场景：提供者失败隔离
- **当** 某个提供者的 `on_session_end()` 抛出异常
- **则** 管理器在 WARNING 级别记录错误
- **则** 管理器继续处理下一个提供者
- **则** 管理器不崩溃或影响其他提供者

#### 场景：没有注册的提供者
- **当** `MemoryManager` 没有注册的提供者
- **则** `on_session_end()` 立即返回
- **则** 系统记录调试消息："没有注册的记忆提供者"

**理由**：此修改确保所有记忆提供者（不仅仅是 `FileMemoryProvider`）都有机会处理会话结束事件。协调逻辑已存在于其他钩子（`sync_turn`、`on_delegation`），因此这是扩展该模式。

**迁移**：无需迁移。未实现 `on_session_end()` 的现有提供者将使用基类默认实现（无操作）。
