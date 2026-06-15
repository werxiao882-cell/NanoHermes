## 背景

### 当前状态

NanoHermes 的后台任务系统存在"代码存在但从未运行"的问题：

```
src/conversation/background_review.py
├── spawn_background_review()  # 从未被调用
└── fork_agent()               # 有 bug，无法调用工具

src/skills/curator.py
└── Curator                    # 从未被实例化
```

### 参考实现对比

| 特性 | Claude Code | Hermes Agent | NanoHermes 当前 | NanoHermes 目标 |
|------|-------------|--------------|----------------|----------------|
| 后台执行模型 | 独立进程 | 后台线程 | 后台线程（未使用） | 后台线程 |
| 工具隔离 | 工具白名单 | `REVIEW_TOOL_WHITELIST` | 有定义但未使用 | 启用白名单 |
| 触发机制 | 事件驱动 | 手动调用 | 无 | 事件驱动（`LOOP_END`） |
| 并发控制 | 进程池 | 无 | 无 | 信号量（max=2） |
| 任务类型 | 通用 | 记忆/技能审查 | 记忆/技能（未启用） | 记忆/技能/视觉/搜索 |

## 目标与非目标

**目标**：
- 修复 `fork_agent()` 的工具调用 bug
- 激活记忆刷写和技能审查功能
- 创建统一的后台任务调度器
- 后台任务不阻塞主对话

**非目标**：
- 不实现独立的辅助 LLM 客户端（已移除 `src/auxiliary/`）
- 不实现实时流式后台任务
- 不支持后台任务的用户交互（如确认对话框）

## 设计决策

### 决策 1：修复 `fork_agent()` 而非重写

**选择**：修复现有 `fork_agent()` 的工具调用逻辑

**理由**：
- 现有代码结构合理，只是工具调用循环有 bug
- 参考 `ConversationLoop.run()` 的工具调用逻辑即可修复
- 比重写整个模块风险更低

**替代方案**：
- 重写为新的 `BackgroundAgent` 类：工作量大，收益不明显
- 复用 `ConversationLoop`：过重，后台任务不需要所有特性

### 决策 2：事件驱动触发（`LOOP_END`）

**选择**：在 `ConversationLoop` 的 `LOOP_END` 事件后触发后台任务

**理由**：
- 对话结束时是审查记忆和技能的最佳时机
- 事件驱动比定时轮询更高效
- 与现有事件总线架构一致

**实现方式**：
```python
# src/conversation/loop.py
self.events.emit(EventType.LOOP_END, {...})

# 新增：触发后台任务
if self._background_scheduler:
    self._background_scheduler.on_loop_end(messages, iteration)
```

### 决策 3：信号量控制并发

**选择**：使用 `threading.Semaphore(max_concurrent=2)` 控制并发

**理由**：
- 防止多个后台任务同时调用 LLM API，避免速率限制
- 信号量比任务队列更简单，适合当前场景
- 参考 `delegation/manager.py` 的 `Semaphore` 实现

**替代方案**：
- 任务队列（`queue.Queue`）：更复杂，需要额外的调度逻辑
- 无并发控制：可能导致 API 速率限制

### 决策 4：增量记忆提取（最近 10 轮）

**选择**：只审查最近 10 轮对话（20 条消息）

**理由**：
- 成本控制：全量审查长对话会消耗大量 token
- 时效性：最近对话更可能包含值得记住的信息
- 去重：`MemoryStore` 已有去重逻辑

**实现细节**：
- 每条消息截断到 500 字符
- 使用 `_MEMORY_REVIEW_PROMPT` 模板
- `max_tokens=1000` 限制响应长度

### 决策 5：工具白名单隔离

**选择**：使用 `REVIEW_TOOL_WHITELIST` 限制后台任务的工具访问

**理由**：
- 安全隔离：防止后台任务执行危险操作（如 `terminal`、`write_file`）
- 职责清晰：后台任务只使用需要的工具（`memory`、`skill_manage`）
- 参考 Claude Code 和 Hermes Agent 的最佳实践

**白名单定义**：
```python
REVIEW_TOOL_WHITELIST = {"memory", "skill_manage", "skill_view", "skills_list"}
```

## 风险与权衡

### 风险 1：后台任务消耗过多 token

**缓解措施**：
- 每个任务设置 `max_tokens` 上限（记忆 1000，技能 2000）
- 审查消息截断到 500 字符
- 只审查最近 10 轮对话

### 风险 2：后台任务失败影响主对话

**缓解措施**：
- 所有后台任务在 `try-except` 中运行
- 失败只记录日志，不抛出异常
- 使用独立线程，崩溃不影响主线程

### 风险 3：`fork_agent()` 修复可能引入新 bug

**缓解措施**：
- 参考 `ConversationLoop.run()` 的成熟实现
- 添加详细的单元测试
- 限制最大迭代次数（5 轮）

### 权衡 1：后台任务增加响应延迟

**接受**：后台任务在独立线程运行，用户感知不到延迟

### 权衡 2：技能审查可能产生不必要的提议

**接受**：审查提示强调"只提议通用、可复用的技能"，用户可以拒绝

## 迁移计划

### 分阶段实施

**阶段 1：核心修复（P0）**
1. 修复 `fork_agent()` 工具调用 bug
2. 实现 `BackgroundTaskScheduler`
3. 激活记忆刷写

**阶段 2：技能审查（P0）**
4. 激活技能审查
5. 集成 `Curator`

**阶段 3：扩展功能（P1，可选）**
6. 视觉提取工具
7. 会话搜索摘要

### 回滚策略

- 所有后台任务通过配置开关控制
- 可以逐个禁用特定任务
- 回滚只需修改配置，无需代码变更

## 开放问题

1. **技能审查的触发频率**：每 10 轮对话还是每 30 分钟？建议两者取先
2. **记忆去重策略**：语义相似度还是字符串匹配？建议先用字符串匹配，后续优化
3. **后台任务日志级别**：INFO 还是 DEBUG？建议 INFO，用户可以看到后台活动
