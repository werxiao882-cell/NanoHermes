## P0 核心任务（必须完成）

### 1. 修复 `fork_agent()` 工具调用 bug

**目标**：使 `fork_agent()` 能够真正调用工具，而非收到内容就返回

- [x] 1.1 分析当前 `fork_agent()` 实现，定位工具调用逻辑 bug
- [x] 1.2 参考 `ConversationLoop.run()` 的工具调用循环，重写 `fork_agent()` 的工具处理逻辑
- [x] 1.3 实现工具白名单过滤（`REVIEW_TOOL_WHITELIST`）
- [x] 1.4 添加工具执行和结果追加逻辑
- [x] 1.5 添加最大迭代限制（5 轮）和超时保护
- [x] 1.6 编写单元测试，验证工具调用功能

**验收标准**：
- `fork_agent()` 能够调用 `memory` 工具并写入 MEMORY.md
- 工具调用结果能够正确追加到消息历史
- 超过 5 轮迭代后自动终止

### 2. 实现后台任务调度器

**目标**：创建统一的 `BackgroundTaskScheduler` 管理所有后台任务

- [x] 2.1 创建 `src/background/scheduler.py` 模块
- [x] 2.2 实现 `BackgroundTaskScheduler` 类，包含信号量并发控制（max_concurrent=2）
- [x] 2.3 实现任务注册 API：`register_task(name, handler, trigger_condition)`
- [x] 2.4 实现 `on_loop_end(messages, iteration)` 方法，供 `ConversationLoop` 调用
- [x] 2.5 实现后台线程执行和异常处理
- [x] 2.6 实现任务状态查询 API：`get_running_tasks()`, `get_task_history()`
- [x] 2.7 实现优雅关闭：等待运行中的任务完成（10s 超时）
- [x] 2.8 编写单元测试

**验收标准**：
- 调度器能够注册和触发后台任务
- 并发控制生效，最多 2 个任务同时运行
- 任务失败不影响主对话

### 3. 激活记忆刷写

**目标**：对话结束时自动提取关键信息写入 MEMORY.md/USER.md

- [x] 3.1 实现 `FileMemoryProvider.on_session_end(messages)` 方法
- [x] 3.2 实现消息截断逻辑（最近 20 条，每条 500 字符）
- [x] 3.3 调用 `fork_agent()` 进行记忆审查，使用 `_MEMORY_REVIEW_PROMPT`
- [x] 3.4 解析 LLM 响应，提取记忆条目
- [x] 3.5 调用 `memory` 工具写入 MEMORY.md/USER.md
- [x] 3.6 在 `MemoryManager.on_session_end()` 中协调所有 provider
- [x] 3.7 注册记忆刷写任务到调度器，触发条件：`LOOP_END` 且消息数 >= 10
- [x] 3.8 编写单元测试和集成测试

**验收标准**：
- 对话结束时自动触发记忆审查
- 关键信息（用户偏好、项目上下文）被提取并写入
- 重复信息不会重复写入

### 4. 激活技能审查

**目标**：定期评估对话模式，自动提议创建或更新技能

- [x] 4.1 实现技能审查触发逻辑（每 10 轮或 30 分钟）
- [x] 4.2 调用 `spawn_background_review(..., "skill")` 进行技能审查
- [x] 4.3 在 TUI 初始化时实例化 `Curator`
- [x] 4.4 在 `LOOP_END` 事件中定期调用 `curator.maybe_run()`
- [x] 4.5 注册技能审查任务到调度器
- [x] 4.6 编写单元测试

**验收标准**：
- 技能审查定期触发
- `Curator` 能够管理技能生命周期（active → stale → archived）
- 技能提议记录到日志

### 5. 集成到对话循环和 TUI

**目标**：将后台任务系统连接到主对话循环和 TUI

- [x] 5.1 在 `ConversationLoop` 中添加 `_background_scheduler` 属性
- [x] 5.2 在 `LOOP_END` 事件后调用 `scheduler.on_loop_end(messages, iteration)`
- [x] 5.3 在 `TUIApp.__init__()` 中实例化 `BackgroundTaskScheduler`
- [x] 5.4 注册记忆刷写和技能审查任务
- [x] 5.5 在 `TUIApp.shutdown()` 中调用 `scheduler.shutdown()`
- [x] 5.6 更新 `/status` 命令，显示运行中的后台任务
- [x] 5.7 添加配置加载逻辑（从 `nanohermes.json` 读取）
- [ ] 5.8 端到端测试：启动 TUI → 对话 → 退出 → 验证记忆写入

**验收标准**：
- TUI 启动时调度器初始化
- 对话结束时后台任务自动触发
- TUI 退出时调度器优雅关闭
- `/status` 命令显示后台任务状态

### 6. 配置系统

**目标**：添加配置开关，支持启用/禁用后台任务

- [x] 6.1 在 `src/config/models.py` 中添加 `BackgroundTasksConfig`
- [x] 6.2 添加全局开关：`background_tasks.enabled`（默认 true）
- [x] 6.3 添加并发控制：`background_tasks.max_concurrent`（默认 2）
- [x] 6.4 添加任务开关：`memory_flush.enabled`, `skill_review.enabled`
- [ ] 6.5 更新 `nanohermes.json` schema 文档
- [x] 6.6 编写配置测试

**验收标准**：
- 可以通过配置禁用所有后台任务
- 可以单独禁用特定任务
- 配置变更无需修改代码

## P1 扩展任务（可选）

### 7. 视觉提取工具

**目标**：实现 `vision_analyze` 工具，支持图片内容描述和 OCR

- [ ] 7.1 创建 `src/tools/impls/vision_tool.py`
- [ ] 7.2 实现 `vision_analyze(path, detail="high", ocr_only=False)` 函数
- [ ] 7.3 实现图片读取和 base64 编码
- [ ] 7.4 实现模型能力检查（`check_fn`）
- [ ] 7.5 构建多模态消息格式
- [ ] 7.6 注册工具（`defer_loading=True`）
- [ ] 7.7 编写单元测试

**验收标准**：
- 工具能够分析图片内容
- 不支持多模态的模型返回友好错误
- 工具可通过 `search_tools` 发现

### 8. 会话搜索摘要

**目标**：为 `session_search` 添加 LLM 驱动的摘要功能

- [ ] 8.1 修改 `session_search` 工具，添加 `summarize` 参数
- [ ] 8.2 实现摘要生成逻辑（`max_tokens=500`）
- [ ] 8.3 实现摘要缓存（LRU，20 条，5 分钟 TTL）
- [ ] 8.4 实现优雅降级（摘要失败返回原始结果）
- [ ] 8.5 更新工具 schema
- [ ] 8.6 编写单元测试

**验收标准**：
- `summarize=true` 时返回摘要
- 摘要失败时返回原始结果
- 缓存命中时不重复生成

## 文档和测试

### 9. 文档更新

- [ ] 9.1 更新 `AGENTS.md`，添加后台任务系统说明
- [ ] 9.2 创建 `src/background/ARCHITECTURE.md`
- [ ] 9.3 更新 `src/conversation/ARCHITECTURE.md`，说明 `LOOP_END` 事件
- [ ] 9.4 更新 `src/memory/ARCHITECTURE.md`，说明 `on_session_end()` 钩子
- [ ] 9.5 更新 `src/skills/ARCHITECTURE.md`，说明 `Curator` 集成

### 10. 集成测试

- [ ] 10.1 端到端测试：记忆刷写完整流程
- [ ] 10.2 端到端测试：技能审查完整流程
- [ ] 10.3 并发控制测试：多个任务同时触发
- [ ] 10.4 异常处理测试：后台任务失败不影响主对话
- [ ] 10.5 性能测试：测量后台任务的开销

## 任务依赖关系

```
1. 修复 fork_agent()
   ↓
2. 实现调度器
   ↓
3. 激活记忆刷写 ──┐
   ↓              │
4. 激活技能审查 ──┤
   ↓              │
5. 集成到 TUI ←──┘
   ↓
6. 配置系统

7. 视觉提取（独立）
8. 会话搜索摘要（独立）
9. 文档（并行）
10. 集成测试（依赖 1-6）
```

## 实施建议

### 优先级排序

1. **第一周**：完成任务 1-2（修复 bug + 调度器）
2. **第二周**：完成任务 3-4（记忆 + 技能）
3. **第三周**：完成任务 5-6（集成 + 配置）
4. **第四周**：完成任务 9-10（文档 + 测试）
5. **后续**：按需完成任务 7-8（扩展功能）

### 关键里程碑

- **M1**：`fork_agent()` 能够调用工具（任务 1 完成）
- **M2**：记忆刷写功能可用（任务 3 完成）
- **M3**：后台任务系统集成到 TUI（任务 5 完成）
- **M4**：所有 P0 任务完成，发布 v1.0

### 风险缓解

- **风险 1**：`fork_agent()` 修复复杂度高
  - 缓解：参考 `ConversationLoop` 实现，逐步迭代
- **风险 2**：后台任务消耗过多 token
  - 缓解：严格限制 `max_tokens` 和消息截断
- **风险 3**：集成到 TUI 时出现兼容性问题
  - 缓解：添加配置开关，可随时禁用
