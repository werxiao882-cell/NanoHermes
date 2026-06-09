## 1. Feature Flags 基础设施

- [ ] 1.1 创建 `src/flags/` 目录结构
- [ ] 1.2 实现 `FeatureFlagManager` 单例类（`__init__`, `is_enabled`, `get_value`, `list_flags`）
- [ ] 1.3 实现配置文件加载（从 `nanohermes.json` 的 `featureFlags` 字段）
- [ ] 1.4 实现环境变量加载（`NANOHERMES_FLAG_<NAME>`，优先级高于配置文件）
- [ ] 1.5 实现 flag 阶段定义（alpha/beta/ga）和默认值逻辑
- [ ] 1.6 注册所有新能力的 flag（sandbox, tool_permission, multi_layer_memory, advanced_compression, prompt_management, advanced_multi_agent, streaming_tool_execution, skills_enhancement, security_hardening, hooks_system, cost_tracking）
- [ ] 1.7 实现 `/flags` TUI 命令，列出所有 flag 及状态
- [ ] 1.8 编写 FeatureFlagManager 单元测试

## 2. 安全加固

- [ ] 2.1 创建 `src/security/` 目录结构
- [ ] 2.2 实现 `unicode_sanitizer.py`：`partially_sanitize_unicode()` 函数（NFKC + 危险范围移除 + 迭代 10 轮）
- [ ] 2.3 实现 `recursively_sanitize_unicode()` 递归 JSON 脱敏函数
- [ ] 2.4 实现 `secret_scanner.py`：定义 30+ 种凭据正则模式（AWS、GitHub PAT、OpenAI、Stripe、PEM 等）
- [ ] 2.5 实现 `scan_for_secrets()` 函数（返回规则 ID，不返回密钥原文）
- [ ] 2.6 实现 `redact_secrets()` 函数（替换为 `[REDACTED]`）
- [ ] 2.7 在 MCP 工具返回值处理路径集成 Unicode 脱敏（`src/tools/mcp_client_tool.py`）
- [ ] 2.8 在 ConversationLoop 入口集成用户输入 Unicode 脱敏
- [ ] 2.9 编写 unicode_sanitizer 单元测试（零宽字符、私有区、嵌套 JSON、迭代上限）
- [ ] 2.10 编写 secret_scanner 单元测试（各类凭据模式检测、redact 功能）

## 3. Tool Permission 权限体系

- [ ] 3.1 创建 `src/permissions/` 目录结构
- [ ] 3.2 定义 `PermissionMode` 枚举（default, accept_edits, plan, auto, bypass）
- [ ] 3.3 定义 `PermissionResult` 数据类（behavior: allow/deny/ask, message, updated_input）
- [ ] 3.4 实现 `PermissionRule` 解析器：`ToolName(pattern)` 格式解析
- [ ] 3.5 实现 `RuleEngine`：allow/deny/ask 规则评估，deny 优先
- [ ] 3.6 实现 `PermissionManager`：模式状态机 + 规则引擎组合
- [ ] 3.7 实现危险 Bash 模式黑名单（python, node, eval, sudo, ssh 等 15+ 模式）
- [ ] 3.8 实现 `strip_dangerous_permissions_for_auto_mode()` 和 `restore_dangerous_permissions()`
- [ ] 3.9 实现 `split_compound_command()` 复合命令拆分函数
- [ ] 3.10 实现路径穿越防护 `validate_path()` 函数
- [ ] 3.11 在 Tool dispatcher 中集成权限检查（TOOL_START 事件前置拦截）
- [ ] 3.12 在 TUI 中实现权限确认对话框（allow/deny/allow-always）
- [ ] 3.13 实现 bypass 模式远程 killswitch（检查策略配置）
- [ ] 3.14 编写 PermissionManager 单元测试（各模式、规则优先级、compound command）
- [ ] 3.15 编写路径穿越防护单元测试

## 4. Sandbox 沙盒系统

- [ ] 4.1 创建 `src/sandbox/` 目录结构
- [ ] 4.2 实现 `SandboxManager` 单例类（`is_enabled`, `wrap_command`, `cleanup_after_command`）
- [ ] 4.3 实现基础层：路径白名单检查（allowWrite/denyWrite/allowRead/denyRead）
- [ ] 4.4 实现 `convert_to_sandbox_runtime_config()`：从 settings 解析白名单配置
- [ ] 4.5 实现 settings 文件自动保护（config.json、nanohermes.json 加入 denyWrite）
- [ ] 4.6 实现 `.claude/skills/` 目录自动保护
- [ ] 4.7 实现网络域名白名单提取（从 WebFetch 权限规则）
- [ ] 4.8 实现 `scrub_bare_git_repo_files()`：命令执行后清理 Git 裸仓库文件
- [ ] 4.9 实现 `cleanup_after_command()` 钩入 Shell 执行链路
- [ ] 4.10 实现配置热更新（监听 settings 变化，`refresh_config()`）
- [ ] 4.11 实现沙盒可用性检测（`check_dependencies()`, `get_unavailable_reason()`）
- [ ] 4.12 实现 `failIfUnavailable` 严格模式
- [ ] 4.13 实现增强层：Linux bubblewrap 适配（可选，feature flag 控制）
- [ ] 4.14 实现增强层：macOS sandbox-exec 适配（可选，feature flag 控制）
- [ ] 4.15 在 TUI 中实现 `SandboxDoctorSection` 显示沙盒状态和依赖问题
- [ ] 4.16 编写 SandboxManager 单元测试（白名单、Git 清理、配置热更新）

## 5. 多层 Memory 系统

- [ ] 5.1 实现 `SessionMemoryProvider`：阈值检测（10000 token 初始化，5000 token + 3 次工具调用间隔）
- [ ] 5.2 实现自然断点检测（`has_tool_calls_in_last_turn` 检查）
- [ ] 5.3 实现 Session Memory 文件安全创建（目录 0o700，文件 0o600，flag='wx'）
- [ ] 5.4 实现后台 subagent 摘要生成（forked agent，只允许 FileEdit 操作精确路径）
- [ ] 5.5 实现 `AgentMemoryProvider`：三种 scope（user/project/local）目录解析
- [ ] 5.6 实现 Agent Memory prompt 注入（`load_agent_memory_prompt()` 拼接到 agent system prompt）
- [ ] 5.7 实现 Agent Memory 自动工具注入（声明 memory 的 agent 自动获得 FileRead/FileWrite/FileEdit）
- [ ] 5.8 实现 Agent Memory Snapshot（snapshot.json + .snapshot-synced.json，三种状态判断）
- [ ] 5.9 实现 `TeamMemoryProvider`：按 repo 识别命名空间，pull/push 同步
- [ ] 5.10 在 Team Memory 上传前集成密钥扫描
- [ ] 5.11 实现 `find_relevant_memories()`：扫描文件头 → 生成 manifest → 轻量模型选择 → 最多 5 文件
- [ ] 5.12 实现 `already_surfaced` 过滤避免重复召回
- [ ] 5.13 实现 MEMORY.md 硬截断保护（200 行 / 25KB，`truncate_entrypoint_content()`）
- [ ] 5.14 在 MemoryManager 中注册所有新 Provider
- [ ] 5.15 编写 SessionMemoryProvider 单元测试
- [ ] 5.16 编写 AgentMemoryProvider 单元测试
- [ ] 5.17 编写 Relevant Recall 单元测试

## 6. 高级上下文压缩

- [ ] 6.1 实现 `ReactiveCompact`：413 错误触发紧急压缩，最多尝试 1 次
- [ ] 6.2 实现 `MicroCompact`：追踪 cache_deleted_input_tokens，标记 boundary
- [ ] 6.3 实现 `SnipCompact`：历史片段裁剪（旧 tool_result 块）
- [ ] 6.4 实现压缩熔断器 `CircuitBreaker`：连续 3 次失败停止 auto-compact
- [ ] 6.5 实现熔断器重置（手动 compact 成功后重置）
- [ ] 6.6 实现 `build_post_compact_messages()`：工具能力声明重建 + 文件附件恢复
- [ ] 6.7 实现 auto-compact 缓冲区阈值（有效窗口 - 13000 token）
- [ ] 6.8 在 ConversationLoop 中集成新压缩策略（策略模式调度）
- [ ] 6.9 编写各压缩策略单元测试
- [ ] 6.10 编写熔断器单元测试

## 7. Prompt 管理增强

- [ ] 7.1 实现 `PromptSectionCache`：named section 缓存（dict），SHA256 hash 判断失效
- [ ] 7.2 实现 `DANGEROUS_uncached_section()` 显式声明打断缓存的 section
- [ ] 7.3 实现 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 标记
- [ ] 7.4 将现有 stable 层拆为 named sections（identity, system_rules, tool_guidance, skills_prompt, model_tips）
- [ ] 7.5 实现 prompt 覆盖优先级链（`build_effective_system_prompt()`：override > coordinator > agent > custom > default + append）
- [ ] 7.6 实现 `--system-prompt` 和 `--append-system-prompt` CLI 参数
- [ ] 7.7 实现 `--system-prompt-file` 和 `--append-system-prompt-file` CLI 参数
- [ ] 7.8 实现 prompt cache 失效事件（/clear, /compact, session resume）
- [ ] 7.9 实现 `dump_prompts` 模式（拦截 API 请求写入 JSONL）
- [ ] 7.10 实现 `/context` 命令的 section token 分析
- [ ] 7.11 编写 section cache 单元测试
- [ ] 7.12 编写 prompt 优先级链单元测试

## 8. Streaming Tool Execution

- [ ] 8.1 实现 `StreamingToolExecutor` 类：在流式响应中检测完整 tool_use block 并启动 asyncio.Task
- [ ] 8.2 实现 tool_use block JSON 完整性检测（input JSON 已完整解析）
- [ ] 8.3 实现与 `isConcurrencySafe` 的协调（只有并发安全工具才提前执行）
- [ ] 8.4 实现结果收集：模型响应结束后按原始顺序收集提前执行的结果
- [ ] 8.5 实现 fallback 取消：FallbackTriggeredError 时取消所有 pending Task
- [ ] 8.6 在 ConversationLoop 中集成 StreamingToolExecutor
- [ ] 8.7 编写 StreamingToolExecutor 单元测试（提前执行、结果排序、fallback 取消）

## 9. Skills 增强

- [ ] 9.1 实现 `execute_shell_commands_in_prompt()`：扫描 `!`command`` 和 ```` ```!\ncommand\n``` ```` 语法
- [ ] 9.2 实现 Shell 命令权限检查（走统一 hasPermissionsToUseTool）
- [ ] 9.3 实现 MCP 来源安全切断（`loadedFrom != 'mcp'` 才执行 Shell）
- [ ] 9.4 实现内置变量替换（`${NANOHERMES_SKILL_DIR}`, `${NANOHERMES_SESSION_ID}`）
- [ ] 9.5 实现条件技能：`paths` 字段 glob pattern 解析
- [ ] 9.6 实现文件变更监听触发条件技能激活
- [ ] 9.7 实现技能发现 memoize 缓存
- [ ] 9.8 编写 Shell 执行单元测试（内联、代码块、MCP 切断）
- [ ] 9.9 编写条件技能单元测试

## 10. Hooks 系统

- [ ] 10.1 创建 `src/hooks/` 目录结构
- [ ] 10.2 实现 `HookRegistry` 类：注册/注销 handler，按钩子点分组
- [ ] 10.3 定义 8 种钩子点枚举（PreSampling, PostSampling, PreCompact, PostCompact, SessionStart, FileChanged, SubagentStart, Stop）
- [ ] 10.4 实现 hook 配置加载（从 settings 的 `hooks` 字段）
- [ ] 10.5 实现 hook 执行器：subprocess 调用外部脚本，stdin 传入 JSON 上下文
- [ ] 10.6 实现故障隔离：单个 hook 失败不影响其他 hook 和主流程
- [ ] 10.7 实现执行超时（默认 30 秒）
- [ ] 10.8 实现 Stop 钩子输出解析（`{"block": true, "message": "..."}` 阻止继续）
- [ ] 10.9 实现 FileChanged 钩子 glob pattern 过滤
- [ ] 10.10 将钩子点映射到现有 EventBus 事件类型
- [ ] 10.11 编写 HookRegistry 单元测试（注册、执行、故障隔离、超时）

## 11. 高级 Multi-Agent

- [ ] 11.1 实现 Coordinator 模式：`get_coordinator_system_prompt()` 定义调度器身份
- [ ] 11.2 实现 worker 结果 task-notification 格式（XML 包装，user-role message 回流）
- [ ] 11.3 实现 Coordinator 工作流分相提示（Research → Synthesis → Implementation → Verification）
- [ ] 11.4 实现 `TeamCreateTool`：创建 team file（JSON）+ task list 目录 + leader context
- [ ] 11.5 实现文件式 Mailbox 系统：`read_mailbox()`, `write_to_mailbox()`, `read_unread_messages()`
- [ ] 11.6 实现 Mailbox filelock 并发写入保护
- [ ] 11.7 实现消息类型协议（regular, permission_request, permission_response, shutdown_request, plan_approval）
- [ ] 11.8 实现 `SendMessageTool` 消息路由（本地 agentId → 队列/resume，teammate → mailbox，`*` → broadcast）
- [ ] 11.9 实现 inbox poller：周期性轮询 teammate inbox，注入未读消息
- [ ] 11.10 实现共享 task list：`create_task()`, `claim_task()`, `update_task()`, `list_tasks()`
- [ ] 11.11 实现 teammate 自动 claim 空闲任务
- [ ] 11.12 实现 leader 权限桥接：teammate 权限请求通过 asyncio.Queue 回流到 leader TUI
- [ ] 11.13 实现 worker badge 显示（TUI 权限对话框标识请求来源）
- [ ] 11.14 实现 in-process teammate 后端：asyncio.Task 隔离上下文
- [ ] 11.15 实现 teammate spawn 约束（不可嵌套 teammate，in-process 不可启动 background agent）
- [ ] 11.16 实现 context modifier 原子化应用（批次收集后统一按序应用）
- [ ] 11.17 编写 Coordinator 模式单元测试
- [ ] 11.18 编写 Mailbox 系统单元测试
- [ ] 11.19 编写 task list 协作单元测试

## 12. 实时成本追踪

- [ ] 12.1 实现 `CostTracker` 类：per-model、per-session 成本累计
- [ ] 12.2 在 API 调用回调中集成成本计算（利用现有 `model_metadata.py` 定价数据）
- [ ] 12.3 实现多模型分别计价（主模型 + 辅助模型）
- [ ] 12.4 在 StatusBar 中显示实时会话成本（`$X.XX` 格式）
- [ ] 12.5 实现 `/cost` 命令显示模型使用明细
- [ ] 12.6 实现预算上限告警（`maxBudgetUsd` 配置，90% 阈值警告）
- [ ] 12.7 实现成本持久化到 SessionDB
- [ ] 12.8 实现会话恢复时加载历史成本
- [ ] 12.9 编写 CostTracker 单元测试

## 13. Tool 接口增强

- [ ] 13.1 在 ToolEntry 数据类中新增安全元数据字段（is_concurrency_safe, is_read_only, is_destructive, check_permissions）
- [ ] 13.2 修改 `build_tool()` 默认值为 fail-closed 策略
- [ ] 13.3 新增 `should_defer` 和 `always_load` 字段
- [ ] 13.4 更新现有 17 个工具的安全元数据声明
- [ ] 13.5 编写 Tool 接口增强单元测试

## 14. 集成测试与文档

- [ ] 14.1 编写 Sandbox + Permission 集成测试（沙盒内命令权限检查）
- [ ] 14.2 编写 Multi-layer Memory 集成测试（Session + Agent + Relevant Recall）
- [ ] 14.3 编写 Multi-Agent 集成测试（Coordinator + Worker 完整流程）
- [ ] 14.4 编写 Hooks + Compression 集成测试（PreCompact hook 影响压缩策略）
- [ ] 14.5 更新 AGENTS.md 文档，记录新增模块和命令
- [ ] 14.6 为每个新模块创建 ARCHITECTURE.md
