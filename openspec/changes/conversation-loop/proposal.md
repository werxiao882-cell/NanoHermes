## 为什么

业界成熟的自进化 AI Agent 系统的对话循环 (~4300 LOC) 是核心引擎，包含模型调用、工具分发、错误分类、重试、回退、压缩触发、后轮次钩子、后台记忆/技能审查。NanoHermes 需要实现相同的对话循环架构。

## 变更内容

- 实现核心对话循环（模型调用 → 工具分发 → 重试 → 后处理）
- 实现 API 错误分类器，支持智能故障转移和恢复
- 实现后台记忆/技能审查线程
- 实现轨迹保存
- 实现 debug 模式，输出发送到模型的完整请求和模型返回的完整响应
- 实现 CLI 斜杠命令系统（/clear, /status, /sessions, /title, /skills, /tools）
- 实现 /tools 命令查看已加载工具列表
- 实现现代化 TUI 聊天界面（基于 rich + prompt_toolkit），作为默认交互模式：
  - 顶部横幅（模型、工具、技能、会话信息）
  - 对话输出区域（流式显示工具调用和响应）
  - 底部固定输入区（支持斜杠命令自动补全）
  - 工具调用进度显示（类似 Hermes 的 preparing xxx... 格式）
  - 工具执行时间显示
  - 代理响应分隔符
  - 实际对话循环集成（非 Mock，支持模型调用和工具分发）
  - 工具调用简要结果显示（read_file 显示行数，write_file 显示字节数等）
  - 模型思考内容显示（+ Thought: xxxms，可折叠展开）
  - 移除传统 CLI 交互模式，TUI 成为唯一默认界面
- 实现传统 CLI 工具调用显示，展示工具名称、参数摘要和执行耗时，避免死循环
- 实现工具调用简要结果显示（Read, Write, Glob 等操作返回摘要）

## 能力

### New Capabilities

- `conversation-loop`: 核心对话循环，包含模型调用、工具分发、迭代预算、中断检查、后轮次钩子。
- `error-classifier`: API 错误分类器，包含错误分类学（auth、billing、rate_limit、context_overflow、format_error 等），提供恢复策略提示。
- `background-review`: 后台审查线程，fork Agent 评估对话，决定是否保存记忆或更新技能。使用工具白名单，不影响主对话。
- `debug-mode`: Debug 模式，输出发送到大模型的完整请求体（JSON）、模型返回的完整响应体（JSON）、模型的思考内容（reasoning），以及工具执行结果。通过 `--debug` 命令行参数开启。
- `slash-commands`: CLI 斜杠命令系统，所有内置命令使用 `/xxx` 格式。支持 /clear, /status, /sessions, /title, /skills, /tools。模型不会拦截斜杠命令。
- `tools-list`: /tools 命令查看已加载工具列表，显示工具名称、工具集、描述。
- `modern-tui`: 现代化 TUI 聊天界面，基于 rich + prompt_toolkit 实现。包含顶部横幅（模型/工具/技能/会话信息）、对话输出区域（流式显示工具调用和响应）、底部固定输入区（支持斜杠命令自动补全）。集成实际对话循环，非 Mock 实现。通过 `--tui` 参数启动。
- `tool-result-summary`: 工具调用简要结果显示，Read/Write/Glob 等操作返回摘要信息，方便用户理解工具执行情况。

### Modified Capabilities

<!-- 无现有能力需要修改 -->

## Impact

- 新增 `src/conversation/` 目录
- 依赖所有其他功能模块
- 无破坏性变更，从零开始构建
