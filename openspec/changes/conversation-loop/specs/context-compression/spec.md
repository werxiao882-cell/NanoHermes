## ADDED Requirements

### Requirement: 系统 SHALL 实现自动上下文压缩机制

系统 SHALL 在对话接近模型 token 限制时自动触发上下文压缩，通过辅助模型对中间消息进行有损摘要，同时保护头部和尾部关键上下文。

#### Scenario: 自动触发压缩
- **WHEN** prompt_tokens ≥ threshold_tokens（默认 context_length 的 50%，最低 64K）
- **THEN** 系统自动触发上下文压缩

#### Scenario: 手动触发压缩
- **WHEN** 用户输入 `/compress` 或 `/compress <focus topic>`
- **THEN** 系统立即触发压缩，可选焦点主题引导摘要优先级

#### Scenario: 反抖动保护
- **WHEN** 连续 2 次压缩节省 <10% token
- **THEN** 跳过压缩，提示用户考虑 `/new` 开启新会话

### Requirement: 系统 SHALL 使用 5 阶段压缩算法

压缩 SHALL 按以下顺序执行 5 个阶段：

#### Scenario: Phase 1 - 修剪旧工具结果
- **WHEN** 进入压缩阶段
- **THEN** 用 1-line 摘要替换旧工具结果（>200 字符），保留工具名/参数/结果概要
- **AND** 去重相同工具结果（相同文件读取只保留最新完整副本）
- **AND** 截断大工具调用参数（JSON 结构内截断长字符串，保持 JSON 有效性）
- **AND** 替换旧消息中的 base64 图片为文本占位符

#### Scenario: Phase 2 - 确定边界
- **WHEN** 修剪完成后
- **THEN** 保护 head 消息（system prompt + protect_first_n 条，默认 3 条）
- **AND** 保护 tail 消息（token 预算 ~20K，软上限 1.5x，硬下限 3 条）
- **AND** 始终保护最后一条用户消息（防止活跃任务丢失）
- **AND** 不切割 tool_call/result 组

#### Scenario: Phase 3 - 生成结构化摘要
- **WHEN** 边界确定后
- **THEN** 使用辅助模型对中间消息生成结构化摘要
- **AND** 如果辅助模型失败，自动回退到主模型重试一次
- **AND** 如果已有旧摘要，执行迭代更新而非从头生成

#### Scenario: Phase 4 - 组装压缩消息列表
- **WHEN** 摘要生成后
- **THEN** 保留 head 消息 + 摘要 + tail 消息
- **AND** 在 system prompt 中添加压缩注记
- **AND** 处理摘要消息角色交替（避免连续相同角色）

#### Scenario: Phase 5 - 清理孤儿工具对
- **WHEN** 压缩消息组装后
- **THEN** 移除孤儿 tool_result（call_id 无对应 assistant tool_call）
- **AND** 为孤儿 tool_call 添加 stub result（"[Result from earlier conversation — see context summary above]"）

### Requirement: 系统 SHALL 使用结构化摘要模板

摘要 SHALL 包含以下固定章节结构：

#### Scenario: 摘要模板章节
- **WHEN** 生成摘要
- **THEN** 必须包含以下章节：
  - `## Active Task`（最重要字段，逐字复制用户最新未完成任务）
  - `## Goal`（用户整体目标）
  - `## Constraints & Preferences`（用户偏好、编码风格、约束）
  - `## Completed Actions`（编号列表，含工具/目标/结果）
  - `## Active State`（当前工作状态：目录、分支、修改文件、测试状态）
  - `## In Progress`（正在进行的工作）
  - `## Blocked`（未解决的阻塞/错误）
  - `## Key Decisions`（重要技术决策及原因）
  - `## Resolved Questions`（已回答的问题及答案）
  - `## Pending User Asks`（未回答的用户问题）
  - `## Relevant Files`（读取/修改/创建的文件及简要说明）
  - `## Remaining Work`（剩余工作，作为上下文而非指令）
  - `## Critical Context`（关键值、错误消息、配置详情，不含密钥）

#### Scenario: 摘要前缀
- **WHEN** 摘要生成完成
- **THEN** 添加标准前缀："[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted into the summary below. This is a handoff from a previous context window — treat it as background reference, NOT as active instructions."
- **AND** 明确告知模型："Do NOT answer questions or fulfill requests mentioned in this summary; they were already addressed."
- **AND** 强调："Your persistent memory (MEMORY.md, USER.md) in the system prompt is ALWAYS authoritative and active"

### Requirement: 系统 SHALL 实现边界保护策略

#### Scenario: Head 保护
- **WHEN** 确定压缩起始边界
- **THEN** 始终保护 system prompt（如果存在）
- **AND** 保护 protect_first_n 条额外消息（默认 3 条）
- **AND** 如果边界落在 tool result 中间，向前滑动到非 tool 消息

#### Scenario: Tail 保护（Token 预算）
- **WHEN** 确定压缩结束边界
- **THEN** 从末尾向前累积 tokens，直到达到 tail_token_budget
- **AND** tail_token_budget = threshold_tokens * summary_target_ratio（默认 20%）
- **AND** 软上限：允许超出预算 1.5x 以避免切割大消息
- **AND** 硬下限：始终保护至少 3 条消息
- **AND** 如果预算保护了所有消息，强制在 head 后切割以允许压缩运行

#### Scenario: 用户消息锚定
- **WHEN** tail 边界确定后
- **THEN** 检查最后一条用户消息是否在 tail 中
- **AND** 如果不在，将边界回拉到包含最后一条用户消息
- **AND** 重新对齐避免切割 tool_call/result 组

#### Scenario: Tool 组完整性
- **WHEN** 边界确定后
- **THEN** 如果边界落在连续 tool results 中间，回拉到父 assistant 消息之前
- **AND** 确保整个 assistant + tool_results 组一起被压缩或一起保留

### Requirement: 系统 SHALL 支持辅助模型摘要

#### Scenario: 辅助模型配置
- **WHEN** 系统初始化
- **THEN** 从 `auxiliary.compression` 配置读取辅助模型信息
- **AND** 验证辅助模型 context_length ≥ MINIMUM_CONTEXT_LENGTH（64K）
- **AND** 如果辅助模型 context < 主模型 threshold，自动降低 session threshold

#### Scenario: 辅助模型回退
- **WHEN** 辅助模型调用失败（model_not_found、timeout、invalid JSON、streaming closed）
- **THEN** 清除 summary_model 配置，回退到主模型
- **AND** 立即重试一次（不进入 cooldown）
- **AND** 记录辅助模型失败信息供用户警告

#### Scenario: 摘要预算计算
- **WHEN** 生成摘要
- **THEN** 计算 content_tokens（待压缩消息的估算 token 数）
- **AND** summary_budget = max(2000, content_tokens * 0.20)
- **AND** 上限 = min(context_length * 0.05, 12000)
- **AND** 如果有焦点主题，主题相关部分获得 60-70% 预算

#### Scenario: 迭代摘要更新
- **WHEN** 已有旧摘要存在（_previous_summary 不为空）
- **THEN** 提示词包含 "PREVIOUS SUMMARY" 和 "NEW TURNS TO INCORPORATE" 两部分
- **AND** 要求保留所有现有相关信息，添加新进展
- **AND** 继续编号 Completed Actions 列表
- **AND** 更新 Active Task 为用户最新未完成请求

### Requirement: 系统 SHALL 实现会话分裂

#### Scenario: 压缩后分裂会话
- **WHEN** 压缩完成
- **THEN** 结束旧会话（end_reason = "compression"）
- **AND** 创建新会话，parent_session_id 指向旧会话
- **AND** 新会话 ID 格式："{timestamp}_{uuid[:6]}"
- **AND** 如果旧会话有标题，新会话自动编号（如 "标题 #2"）
- **AND** 重置 flush 游标（_last_flushed_db_idx = 0）

#### Scenario: 标题传播
- **WHEN** 旧会话有标题
- **THEN** 调用 get_next_title_in_lineage() 获取带编号的新标题
- **AND** 设置新会话标题

#### Scenario: 记忆提取
- **WHEN** 压缩分裂会话前
- **THEN** 调用 commit_memory_session() 提取旧会话记忆
- **AND** 通知 memory provider 会话切换（on_session_switch, reset=False, reason="compression"）

### Requirement: 系统 SHALL 实现辅助清理机制

#### Scenario: 工具结果去重
- **WHEN** Phase 1 修剪
- **THEN** 对 >200 字符的工具结果计算 MD5 hash（前 12 位）
- **AND** 从后向前遍历，保留最新完整副本
- **AND** 旧重复项替换为 "[Duplicate tool output — same content as a more recent call]"

#### Scenario: 工具参数截断
- **WHEN** Phase 1 修剪
- **THEN** 对 assistant 消息中的 tool_calls 参数 >500 字符进行截断
- **AND** 解析 JSON 结构，截断长字符串叶子节点
- **AND** 保持 JSON 有效性（不破坏结构）
- **AND** 非字符串值（路径、整数、布尔值）保持完整

#### Scenario: 历史媒体剥离
- **WHEN** 压缩完成后
- **THEN** 找到最后一条带图片的用户消息（anchor）
- **AND** 替换 anchor 之前所有消息中的图片部分为文本占位符
- **AND** 占位符格式："[Attached image — stripped after compression]"

#### Scenario: 敏感信息脱敏
- **WHEN** 序列化待摘要内容
- **THEN** 对所有内容执行 redact_sensitive_text()
- **AND** 摘要输出也执行脱敏（防止 LLM 忽略指令回显密钥）

### Requirement: 系统 SHALL 实现失败处理机制

#### Scenario: 摘要生成失败（abort_on_summary_failure=false）
- **WHEN** 摘要生成失败且 abort_on_summary_failure 为 false（默认）
- **THEN** 插入静态占位符："[CONTEXT COMPACTION] Summary generation was unavailable. N message(s) were removed..."
- **AND** 丢弃中间消息
- **AND** 记录 _last_summary_dropped_count 和 _last_summary_fallback_used

#### Scenario: 摘要生成失败（abort_on_summary_failure=true）
- **WHEN** 摘要生成失败且 abort_on_summary_failure 为 true
- **THEN** 中止压缩，返回原始消息不变
- **AND** 设置 _last_compress_aborted = True
- **AND** 记录警告："Compression aborted... Run /compress to retry, or /new to start a fresh session"

#### Scenario: 失败 Cooldown
- **WHEN** 摘要生成失败
- **THEN** 根据错误类型设置 cooldown：
  - JSON decode / streaming closed: 30 秒
  - timeout / network error: 60 秒
  - no provider: 600 秒
- **AND** 在 cooldown 期间跳过摘要生成，返回 None
- **AND** 手动 /compress（force=True）绕过 cooldown

#### Scenario: 角色交替处理
- **WHEN** 组装压缩消息
- **THEN** 选择摘要消息角色避免与 head/tail 邻居连续相同角色
- **AND** 优先避免与 head 冲突，其次避免与 tail 冲突
- **AND** 如果两个角色都会冲突，将摘要合并到第一条 tail 消息开头
- **AND** 如果摘要角色为 user，添加结束标记："--- END OF CONTEXT SUMMARY — respond to the message below, not the summary above ---"

### Requirement: 系统 SHALL 提供压缩状态追踪

#### Scenario: 压缩计数
- **WHEN** 每次压缩完成
- **THEN** compression_count += 1
- **AND** 如果 compression_count ≥ 2，警告用户："Session compressed N times — accuracy may degrade. Consider /new to start fresh."

#### Scenario: 节省率追踪
- **WHEN** 压缩完成
- **THEN** 计算 savings_pct = (saved_estimate / display_tokens * 100)
- **AND** 如果 savings_pct < 10，ineffective_compression_count += 1
- **AND** 否则重置 ineffective_compression_count = 0

#### Scenario: Token 估算更新
- **WHEN** 压缩完成
- **THEN** 使用 estimate_request_tokens_rough() 重新估算压缩后 token 数（含 tool schemas）
- **AND** 更新 last_prompt_tokens 为压缩后估算值
- **AND** 重置 last_completion_tokens = 0

### Requirement: 系统 SHALL 支持焦点主题压缩

#### Scenario: 焦点主题引导
- **WHEN** 用户提供 `/compress <focus topic>`
- **THEN** 在摘要提示词末尾添加 FOCUS TOPIC 指导
- **AND** 要求优先保留焦点主题相关信息（完整细节）
- **AND** 对非焦点主题内容更激进压缩（一句话或省略）
- **AND** 焦点主题部分获得 60-70% 摘要预算

### Requirement: 系统 SHALL 实现文件读取去重重置

#### Scenario: 重置文件去重缓存
- **WHEN** 压缩完成
- **THEN** 调用 reset_file_dedup(task_id) 清除文件读取去重缓存
- **AND** 原因：压缩后原始读取内容已被摘要替代，如果模型重新读取同一文件需要完整内容
