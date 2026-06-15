## 为什么需要这个变更

NanoHermes 当前的后台任务系统存在严重问题：**代码存在但从未真正运行**。

### 现状分析

| 功能 | 代码状态 | 运行状态 | 问题 |
|------|---------|---------|------|
| 上下文压缩 | ✅ 已实现 | ✅ 运行中 | 无 |
| 记忆刷写 | ⚠️ 部分实现 | ❌ 未调用 | `background_review.py` 存在但从未被集成 |
| 技能审查 | ⚠️ 部分实现 | ❌ 未调用 | `Curator` 存在但从未实例化 |
| `fork_agent()` | ⚠️ 有 bug | ❌ 无法工作 | 工具调用逻辑错误，无法真正调用工具 |

### 核心问题

1. **AI 被动记忆**：用户必须显式调用 `memory` 工具，AI 不会主动学习
2. **技能无法进化**：`Curator` 和技能审查代码是"死代码"
3. **架构断裂**：`background_review.py` 与主对话循环没有连接

### 参考实现

**Claude Code 的后台代理模式**：
- 后台代理在独立上下文中运行，不污染主对话
- 使用工具白名单限制能力（安全隔离）
- 任务完成后通过事件通知主对话
- 支持长时间运行的任务（如代码审查、文档生成）

**Hermes Agent 的后台审查模式**：
- `spawn_background_review()` 在后台线程中运行
- `fork_agent()` 创建简化的子代理
- 使用 `REVIEW_TOOL_WHITELIST` 限制工具访问
- 支持记忆审查和技能审查两种模式

## 变更内容

### 核心变更（优先级 P0）

1. **修复 `fork_agent()` 工具调用 bug**
   - 当前问题：收到内容响应就返回，不处理工具调用
   - 修复方案：参考 `ConversationLoop` 的工具调用循环

2. **激活记忆刷写**
   - 在 `LOOP_END` 事件后触发后台审查
   - 提取最近 10 轮对话中的关键信息
   - 自动写入 MEMORY.md/USER.md

3. **激活技能审查**
   - 定期评估对话模式（每 10 轮或 30 分钟）
   - 自动提议创建或更新技能
   - 集成 `Curator` 到 TUI 运行时

### 扩展变更（优先级 P1，可选）

4. **视觉提取工具**（`vision_analyze`）
   - 支持图片内容描述和 OCR
   - 需要多模态模型（GPT-4o、Claude 3）

5. **会话搜索摘要**
   - 为 `session_search` 添加 LLM 驱动的摘要
   - 可选触发，按需生成

### 架构变更

6. **统一后台任务调度器**
   - 创建 `BackgroundTaskScheduler` 管理所有后台任务
   - 信号量控制并发（默认 max_concurrent=2）
   - 事件驱动触发（`LOOP_END` 事件）

## 能力清单

### 新增能力

- `background-task-scheduler`：统一的后台任务调度框架
- `memory-flush`：对话结束时自动提取记忆
- `skill-review`：定期评估并提议技能

### 修改能力

- `conversation-loop`：在 `LOOP_END` 后触发后台任务
- `memory-system`：实现 `on_session_end()` 钩子
- `skill-system`：集成 `Curator` 到运行时

### 可选能力（P1）

- `vision-extraction`：图片分析工具
- `session-search-summary`：搜索结果摘要

## 影响范围

**代码影响**：
- `src/conversation/background_review.py`：修复 `fork_agent()` bug
- `src/conversation/loop.py`：添加 `LOOP_END` 事件触发
- `src/memory/file_provider.py`：实现 `on_session_end()`
- `src/cli/tui.py`：集成调度器和 `Curator`

**依赖**：
- 复用 `model_caller`，无需额外 LLM 客户端
- 视觉功能需要多模态模型（可选）

**性能**：
- 后台线程运行，不阻塞主对话
- 信号量控制并发，防止 API 速率限制

**兼容性**：
- 所有变更为内部实现，不影响外部 API
- 通过配置开关控制，可随时禁用
