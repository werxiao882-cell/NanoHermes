## Context

NanoHermes 当前已实现基础 Agent 闭环：ConversationLoop + EventBus 驱动、17 个注册工具、FileMemoryProvider（MEMORY.md/USER.md）、分层压缩、3 层 Prompt 组装、MCP 双向支持、Leaf/Orchestrator 委派。系统运行在 Python 3.11+ 上，使用 prompt_toolkit + Rich 构建 TUI。

对比 Claude Code（TypeScript，1902 源文件，513K 行代码），在安全隔离、权限管控、多层记忆、上下文治理、多 Agent 协作等 12 个核心能力域存在显著差距。本设计文档规划如何以渐进式方式补齐这些能力。

约束条件：
- Python 生态，不能直接使用 bubblewrap 等 Linux 专用沙盒（需跨平台方案）
- 单进程模型（asyncio），多 Agent 需基于 asyncio.Task 而非独立进程
- 现有 EventBus 架构可作为 Hooks 系统的基座
- 现有 MemoryManager 编排器已支持多 Provider，可作为多层 Memory 的扩展点

## Goals / Non-Goals

**Goals:**
- 补齐安全基线：沙盒隔离 + 权限体系 + Unicode 脱敏 + 密钥扫描
- 扩展记忆深度：Session/Agent/Team Memory + Relevant Recall
- 增强上下文治理：多策略压缩 + 熔断器 + Prompt section 缓存
- 升级多 Agent 协作：Coordinator + Swarm + Mailbox + Task List
- 降低延迟：Streaming Tool Execution
- 提升可观测性：实时成本追踪 + Prompt dump/audit
- 所有新能力通过 Feature Flag 控制，渐进启用

**Non-Goals:**
- 不实现 Voice Mode（语音输入/输出）
- 不实现 Buddy/Companion 伴侣系统（产品彩蛋）
- 不实现 Worktree 支持（Git worktree 并行会话）
- 不实现 Remote/Bridge 远程混合 Agent
- 不实现 MCP Server 形态（对外暴露工具）
- 不实现编译期 Feature Flag（Python 无编译期，使用运行时 flag）
- 不实现负面关键词检测（产品遥测功能）

## Decisions

### D1: 沙盒方案选型 — subprocess 隔离 + 平台适配

**选择**：基于 `subprocess` 的受限执行环境 + 可选 OS 级沙盒

**理由**：
- Claude Code 的 bubblewrap 仅限 Linux，NanoHermes 需跨平台（Win/Mac/Linux）
- Python 生态缺少成熟的跨平台沙盒库
- 分两层实现：基础层（路径白名单 + 命令黑名单，全平台）+ 增强层（Linux bwrap / macOS sandbox-exec，可选）
- 基础层即可覆盖 80% 安全需求，增强层通过 feature flag 控制

**替代方案**：Docker 容器隔离（太重）、gVisor（仅 Linux）、nsjail（仅 Linux）

### D2: 权限系统架构 — 规则引擎 + 模式状态机

**选择**：声明式规则引擎 + 模式状态机

**理由**：
- Claude Code 的权限系统从 Tool 接口设计之初就是一等公民，NanoHermes 应采用相同策略
- 规则格式：`ToolName(pattern)` 如 `terminal(rm *)` → deny
- 模式状态机：default → auto → bypass，每个模式有独立的规则评估逻辑
- 与现有 EventBus 集成：权限检查作为 TOOL_START 事件的前置拦截器

**替代方案**：RBAC（太重量）、ACL 文件（不够灵活）

### D3: 多层 Memory 扩展策略 — 在现有 MemoryManager 上叠加

**选择**：扩展现有 MemoryManager，新增 SessionMemoryProvider / AgentMemoryProvider / TeamMemoryProvider

**理由**：
- 现有 MemoryManager 已支持多 Provider 编排和 Fan-out 容错
- Session Memory 复用 FileMemoryProvider 的文件写入模式，增加阈值触发和后台 subagent 更新
- Agent Memory 复用 memdir 目录结构（MEMORY.md 索引 + topic 文件），增加 scope 隔离
- Relevant Recall 实现为 prefetch 阶段的轻量检索（不需要向量数据库）

**替代方案**：独立 Memory 子系统（与现有架构冲突）、向量数据库（太重）

### D4: 压缩策略扩展 — 策略模式 + 熔断器

**选择**：在现有 ContextCompressor 上增加策略模式，每种策略独立实现

**理由**：
- 现有 ContextCompressor 已有分层压缩（pruning → head/tail → summary → split），扩展为策略模式自然
- Reactive Compact 作为 413 错误的紧急恢复路径
- Micro Compact 追踪缓存删除 token，轻量缩减
- 熔断器用简单计数器实现（连续 3 次失败 → 停止 auto-compact）
- 能力复灌（post-compact rehydration）在压缩后重建工具声明和文件附件

**替代方案**：外部压缩服务（增加网络依赖）

### D5: Prompt 缓存 — Section 化 + Hash 失效

**选择**：将 system prompt 拆分为 named sections，每个 section 独立缓存，SHA256 hash 判断失效

**理由**：
- 现有 PromptAssembler 已有 stable/context/volatile 三层，在此基础上将 stable 层拆为多个 named section
- 缓存存储在内存中（dict），不需要持久化
- Dynamic boundary 标记 stable 与 volatile 的分界点
- 与 Anthropic prompt caching 协议兼容（标记 cache breakpoint）

**替代方案**：整体 hash（粒度太粗，任何变化都失效）

### D6: Multi-Agent 扩展 — asyncio.Task + 文件 Mailbox

**选择**：基于 asyncio.Task 的 in-process 多 Agent + 文件式 Mailbox 通信

**理由**：
- Python asyncio 天然支持并发 Task，不需要 tmux（跨平台限制）
- Coordinator 模式：主 ConversationLoop 改写为 dispatcher，通过 AgentTool 派出 worker Task
- Swarm 模式：team file（JSON）+ task list（JSON 目录）+ mailbox（JSON 文件 + filelock）
- 权限桥接：worker 的权限请求通过 asyncio.Queue 回到 leader 的 TUI 确认

**替代方案**：multiprocessing（进程间通信复杂）、Celery（太重）、Ray（依赖太大）

### D7: Streaming Tool Execution — 异步流水线

**选择**：在 ConversationLoop 的流式响应处理中，检测到完整 tool_use block 后立即启动 asyncio.Task

**理由**：
- 现有 ConversationLoop 已支持流式响应（stream_completion）
- 在流式回调中检测 tool_use block 的 JSON 完整性，完整后立即创建执行 Task
- 与现有并发分组（isConcurrencySafe）协调：只有并发安全的工具才提前执行
- 需要处理模型回退（fallback）时的 Task 取消和结果丢弃

**替代方案**：等待完整响应后执行（当前方案，延迟高）

### D8: 安全加固 — 纯 Python 实现

**选择**：纯 Python 实现 Unicode 脱敏和密钥扫描，不依赖外部库

**理由**：
- Unicode 脱敏：Python `str.normalize('NFKC')` + `re` 模块即可实现
- 密钥扫描：纯正则匹配，返回规则 ID 而非密钥原文
- 集成点：MCP 工具返回值在 dispatcher 层自动清洗，用户输入在 ConversationLoop 入口清洗

### D9: Hooks 系统 — 复用 EventBus

**选择**：在现有 EventBus 基础上增加用户可配置的 hooks 层

**理由**：
- EventBus 已有 15 种事件类型和故障隔离
- 新增 HookRegistry：从 settings 加载用户配置的 hook 脚本路径
- Hook 执行：subprocess 调用外部脚本，或 Python callable 直接调用
- 8 种钩子点映射到现有事件类型 + 新增 PRE_COMPACT/POST_COMPACT/SUBAGENT_START

### D10: Feature Flags — 运行时配置

**选择**：运行时 Feature Flag 管理器，支持环境变量和配置文件两种来源

**理由**：
- Python 无编译期，使用运行时 flag 是唯一选择
- FeatureFlagManager：单例，启动时从 config + env 加载
- 所有新能力通过 `is_enabled('sandbox')` 等检查
- 支持分级启用：alpha → beta → ga

## Risks / Trade-offs

**[沙盒跨平台一致性]** → 基础层（路径白名单 + 命令黑名单）在所有平台行为一致；增强层（OS 沙盒）仅在支持的平台上启用，通过 feature flag 控制

**[权限系统复杂度]** → 初期只实现 default 和 auto 两种模式，plan/bypass 后续迭代；规则格式保持简单（`ToolName(pattern)`）

**[多层 Memory 的 Token 消耗]** → Relevant Recall 限制最多 5 个文件，MEMORY.md 硬截断 200 行 / 25KB，Session Memory 有阈值触发保护

**[多 Agent 状态同步]** → 采用"收集 → 批次完成后统一应用"模式（参考 Claude Code 的 contextModifier），防止并发竞争

**[Streaming Tool Execution 的取消安全]** → 模型回退时取消所有 pending Task，丢弃已执行结果，重新初始化执行器

**[Feature Flag 膨胀]** → 每个 flag 必须有 owner 和过期时间，定期清理已 GA 的 flag
