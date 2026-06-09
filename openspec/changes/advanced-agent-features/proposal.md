## Why

NanoHermes 已实现基础 Agent 闭环（对话循环、工具系统、单文件记忆、基础压缩、MCP、简单委派），但与 Claude Code 对比后发现 **12 个核心能力域** 存在显著差距。这些差距涵盖安全隔离、权限管控、多层记忆、上下文治理、多 Agent 协作等关键维度，制约了系统在生产级场景下的安全性、可扩展性和长期协作能力。

## What Changes

- 实现 **Sandbox 沙盒系统**：OS 级进程隔离（Linux bubblewrap / macOS sandbox），文件系统/网络白名单驱动，Git bare repo 逃逸防护，配置热更新
- 实现 **Tool Permission 权限体系**：多模式分级管控（default/acceptEdits/plan/auto/bypass），allow/deny/ask 规则引擎，危险 Bash 模式自动剥离，compound command 拆分检查
- 实现 **多层 Memory 系统**：在现有 FileMemory 基础上新增 Session Memory（会话摘要）、Agent Memory（agent 绑定持久记忆，3 种 scope）、Team Memory（团队同步）、Relevant Memory Recall（轻量检索注入）
- 实现 **高级上下文压缩**：新增 Reactive Compact（PTL 紧急压缩）、Micro Compact（轻量缩减）、Snip Compact（历史裁剪）、压缩熔断器（连续失败 3 次停止）、压缩后能力复灌
- 实现 **Prompt 管理增强**：section 级缓存 + dynamic boundary、prompt 覆盖优先级链（override > coordinator > agent > custom > default + append）、prompt 可观测性（dump-prompts、token 分析）
- 实现 **高级 Multi-Agent**：Coordinator 调度模式、Swarm Teammates（team file + mailbox 通信 + task list 协作 + leader 权限桥接）、in-process/tmux 后端
- 实现 **Streaming Tool Execution**：模型流式输出期间即开始执行工具，减少端到端延迟
- 实现 **Skills 增强**：内嵌 Shell 执行（`` !`command` ``）、条件技能（`paths` 字段文件变更触发）
- 实现 **安全加固**：Unicode 隐写防御（NFKC + 危险范围移除 + 递归脱敏）、客户端密钥扫描（30+ 凭据模式）、MCP 返回值清洗
- 实现 **Hooks 系统**：用户可配置的生命周期钩子（PreSampling/PostSampling/PreCompact/PostCompact/SessionStart/FileChanged/SubagentStart/Stop）
- 实现 **实时成本追踪**：per-model、per-session 成本累计，实时显示在 StatusBar，支持预算上限告警
- 实现 **Feature Flags 体系**：运行时特性开关，控制能力裁剪和实验分流

## Capabilities

### New Capabilities

- `sandbox-isolation`: OS 级沙盒隔离系统。包括 bubblewrap/macOS runtime 适配、文件系统/网络白名单配置转换、Git bare repo 清理、settings 文件保护、配置热更新、`failIfUnavailable` 严格模式、沙盒可用性检测与诊断
- `tool-permission-system`: 工具权限管控体系。包括多模式分级（default/acceptEdits/plan/auto/bypass）、allow/deny/ask 规则引擎、危险 Bash 模式检测与 Auto 模式剥离、compound command 拆分检查、路径穿越防护、`bypassPermissions` 远程策略禁用
- `multi-layer-memory`: 多层记忆系统扩展。包括 Session Memory（会话摘要，阈值触发，后台 subagent 更新）、Agent Memory（user/project/local 三种 scope，自动工具注入）、Team Memory（团队同步，密钥扫描）、Relevant Memory Recall（轻量检索，最多 5 文件注入）
- `advanced-compression`: 高级上下文压缩策略。包括 Reactive Compact（PTL 紧急压缩）、Micro Compact（缓存删除追踪）、Snip Compact（历史裁剪）、压缩熔断器（连续 3 次失败停止）、压缩后能力复灌（文件附件 + 工具声明重建）
- `prompt-management`: Prompt 管理增强。包括 section 级缓存与 dynamic boundary、prompt 覆盖优先级链、CLI prompt 注入入口、appendSystemPrompt 追加总线、prompt dump/audit 可观测性、section token 分析
- `advanced-multi-agent`: 高级多 Agent 协作。包括 Coordinator 调度模式（主线程改写为 dispatcher）、Swarm Teammates（team file + mailbox 文件通信 + task list 协作 + leader 权限桥接）、in-process/tmux 后端、teammate 约束（不可嵌套）
- `streaming-tool-execution`: 流式工具执行。在模型还在流式输出 tool_use 时即开始执行工具，减少端到端延迟，与并发分组协调
- `skills-enhancement`: Skills 增强。包括内嵌 Shell 执行（`!`command`` 语法，MCP 来源安全切断）、条件技能（`paths` 字段 glob pattern 文件变更触发）
- `security-hardening`: 安全加固。包括 Unicode 隐写防御（NFKC 规范化 + 危险范围移除 + 递归 JSON 脱敏）、客户端密钥扫描（30+ 凭据正则，redact 而非拒绝）、MCP 返回值自动清洗
- `hooks-system`: 用户可配置生命周期钩子。支持 PreSampling/PostSampling/PreCompact/PostCompact/SessionStart/FileChanged/SubagentStart/Stop 八种钩子点，通过 settings 配置自定义脚本
- `cost-tracking`: 实时成本追踪。per-model、per-session 成本累计，StatusBar 实时显示，预算上限告警，OpenTelemetry 计数器集成
- `feature-flags`: 特性开关体系。运行时 feature flag 管理，控制能力裁剪和实验分流，支持环境变量和配置文件两种来源

### Modified Capabilities

- `tool-runtime`: Tool 接口新增安全元数据声明（`isConcurrencySafe`/`isReadOnly`/`isDestructive`/`checkPermissions`），`buildTool()` 默认值改为 fail-closed 策略
- `memory-system`: 现有 FileMemoryProvider 扩展为多层架构基座，新增 Session/Agent/Team Memory 提供者，MemoryManager 编排器支持多层并行
- `context-compression`: 现有 ContextCompressor 扩展为多策略引擎，新增 Reactive/Micro/Snip 压缩策略，新增熔断器和能力复灌
- `system-prompt-assembly`: PromptAssembler 扩展为 section 化缓存架构，新增覆盖优先级链和可观测性
- `multi-agent-delegation`: DelegationManager 扩展为三层多 Agent 体系，新增 Coordinator 和 Swarm 模式
- `skill-system`: SkillManager 扩展支持内嵌 Shell 执行和条件触发

## Impact

- 新增 `src/sandbox/` 目录：沙盒适配器、运行时管理、依赖检测
- 新增 `src/permissions/` 目录：权限模式、规则引擎、路径验证、危险模式检测
- 扩展 `src/memory/`：新增 session_memory.py、agent_memory.py、team_memory.py、relevant_recall.py
- 扩展 `src/compression/`：新增 reactive_compact.py、micro_compact.py、snip_compact.py、circuit_breaker.py
- 扩展 `src/prompt/`：新增 section_cache.py、prompt_hierarchy.py、prompt_dump.py
- 扩展 `src/delegation/`：新增 coordinator.py、swarm/（team.py、mailbox.py、task_list.py、backends/）
- 新增 `src/hooks/` 目录：钩子注册器、配置加载、执行器
- 新增 `src/security/` 目录：unicode_sanitizer.py、secret_scanner.py
- 新增 `src/flags/` 目录：feature flag 管理
- 扩展 `src/cli/widgets.py`：成本显示、特性状态
- 依赖新增：`bubblewrap`（Linux 沙盒，可选）、`filelock`（mailbox 锁）
- 无破坏性变更：所有新能力通过 feature flag 控制，默认关闭渐进启用
