## 1. 项目设置

- [x] 1.1 创建 `src/conversation/` 目录结构
- [x] 1.2 定义对话循环相关类型和接口
- [x] 1.3 配置 pytest 测试框架

## 2. 核心对话循环实现

- [x] 2.1 实现 ConversationLoop 类
- [x] 2.2 实现 runConversation 方法
- [x] 2.3 实现 callModel 方法
- [x] 2.4 实现 dispatchTool 方法
- [x] 2.5 实现中断检查逻辑
- [x] 2.6 实现迭代预算管理
- [x] 2.7 实现 debug 模式（请求体/响应体 JSON 输出）
- [x] 2.8 实现 reasoning 思考内容输出
- [x] 2.9 实现 on_message_append 回调（实时保存 tool 消息）
- [x] 2.10 编写对话循环的单元测试
  - [x] 2.10.1 测试单轮工具调用
  - [x] 2.10.2 测试多轮工具调用
  - [x] 2.10.3 测试达到迭代限制
  - [x] 2.10.4 测试中断停止循环
  - [x] 2.10.5 测试 debug 模式输出请求体 JSON
  - [x] 2.10.6 测试 debug 模式输出响应体 JSON
  - [x] 2.10.7 测试 debug 模式输出 reasoning 内容

## 3. 错误分类器实现

- [x] 3.1 实现 FailoverReason 枚举
- [x] 3.2 实现 ClassifiedError 类
- [x] 3.3 实现 ErrorClassifier 类
- [x] 3.4 实现所有错误模式匹配（auth、billing、rate_limit、context_overflow 等）
- [x] 3.5 实现恢复策略决策逻辑
- [x] 3.6 编写错误分类的单元测试
  - [x] 3.6.1 测试分类 401 认证错误
  - [x] 3.6.2 测试分类 402 计费错误
  - [x] 3.6.3 测试分类 429 速率限制
  - [x] 3.6.4 测试分类上下文溢出
  - [x] 3.6.5 测试分类服务器错误
  - [x] 3.6.6 测试分类未知错误

## 4. CLI 斜杠命令系统

- [x] 4.1 实现 /clear 清空对话
- [x] 4.2 实现 /status 查看会话状态
- [x] 4.3 实现 /sessions 查看历史会话列表
- [x] 4.4 实现 /title 设置会话标题
- [x] 4.5 实现 /skills 查看可用技能
- [x] 4.6 实现 /tools 查看已加载工具列表
- [x] 4.7 所有命令使用 /xxx 格式，模型不拦截

## 5. 现代化 TUI 聊天界面

- [x] 5.1 添加 rich 和 prompt_toolkit 依赖到 pyproject.toml
- [x] 5.2 实现 TUI 布局类（顶部横幅、对话区域、输入区）
- [x] 5.3 实现顶部横幅组件（模型、工具、技能、会话信息）
- [x] 5.4 实现对话输出区域（流式显示工具调用和响应）
- [x] 5.5 实现底部固定输入区
- [x] 5.6 实现斜杠命令自动补全
- [x] 5.7 实现 --tui 命令行参数启动 TUI 模式
- [x] 5.8 实现工具调用进度显示（preparing xxx... 格式）
- [x] 5.9 实现工具执行时间显示
- [x] 5.10 实现代理响应分隔符
- [x] 5.11 编写 TUI 组件单元测试

## 6. 传统 CLI 工具调用显示

- [x] 6.1 实现 ConversationLoop 工具回调机制（on_tool_start, on_tool_end）
- [x] 6.2 实现传统 CLI 工具调用显示（工具名称、参数摘要、执行耗时）
- [x] 6.3 移除死循环防护（不限制模型能力）
- [x] 6.4 更新 main.py 使用工具回调

## 7. 后台审查实现

- [x] 7.1 实现 spawnBackgroundReview 函数
- [x] 7.2 实现 forkAgent 函数
- [x] 7.3 实现 buildReviewPrompt 函数
- [x] 7.4 实现 _MEMORY_REVIEW_PROMPT 和 _SKILL_REVIEW_PROMPT 常量
- [x] 7.5 编写后台审查的单元测试
  - [x] 7.5.1 测试 fork Agent 继承配置
  - [x] 7.5.2 测试审查记忆
  - [x] 7.5.3 测试审查技能
  - [x] 7.5.4 测试无内容可保存

## 8. TUI 实际逻辑集成

- [x] 8.1 实现 TUI 对话循环集成（替换 Mock 逻辑）
- [x] 8.2 实现 TUI 工具调用显示
- [x] 8.3 实现 TUI 流式响应显示
- [x] 8.4 实现 TUI 思考过程显示
- [x] 8.5 实现 TUI 工具调用简要结果显示
- [x] 8.6 编写 TUI 集成测试
- [x] 8.7 将 TUI 设为默认聊天界面，移除传统 CLI 交互模式
- [x] 8.8 实现模型思考内容折叠显示（+ Thought: xxxms，点击展开）

## 9. 工具调用简要结果显示

- [x] 9.1 实现 Read 操作简要结果显示
- [x] 9.2 实现 Write 操作简要结果显示
- [x] 9.3 实现 Glob 操作简要结果显示
- [x] 9.4 集成到传统 CLI 聊天界面
- [x] 9.5 集成到 TUI 聊天界面

## 10. 会话管理命令

- [x] 10.1 实现 /sessions 命令处理逻辑
- [x] 10.2 实现 list_sessions() 函数，查询 SQLite 获取全部历史会话
- [x] 10.3 格式化输出会话 ID 和标题列表
- [x] 10.4 实现 /resume 命令处理逻辑
- [x] 10.5 实现 resume_session(identifier) 函数，支持 ID 或标题匹配
- [x] 10.6 加载历史消息到当前对话循环
- [x] 10.7 处理会话不存在的情况，给出友好提示
- [x] 10.8 编写会话管理命令的单元测试

## 11. SQLite Schema 对齐 Hermes Agent

- [x] 11.1 更新 sessions 表 schema，添加 source, user_id, model_config, system_prompt, parent_session_id 字段
- [x] 11.2 更新 sessions 表 schema，添加 started_at (REAL), ended_at, end_reason 字段
- [x] 11.3 更新 sessions 表 schema，添加 message_count, tool_call_count, api_call_count 字段
- [x] 11.4 更新 sessions 表 schema，添加 input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens 字段
- [x] 11.5 更新 sessions 表 schema，添加 billing_provider, billing_base_url, billing_mode 字段
- [x] 11.6 更新 sessions 表 schema，添加 estimated_cost_usd, actual_cost_usd, cost_status, cost_source, pricing_version 字段
- [x] 11.7 更新 sessions 表 schema，添加 handoff_state, handoff_platform, handoff_error 字段
- [x] 11.8 更新 messages 表 schema，添加 tool_name, timestamp (REAL), token_count 字段
- [x] 11.9 更新 messages 表 schema，添加 finish_reason, reasoning, reasoning_content, reasoning_details 字段
- [x] 11.10 更新 messages 表 schema，添加 codex_reasoning_items, codex_message_items, platform_message_id, observed 字段
- [x] 11.11 实现 FTS5 全文搜索触发器（messages_fts_insert/update/delete）
- [x] 11.12 实现 trigram 分词器触发器（messages_fts_trigram_insert/update/delete）
- [x] 11.13 实现会话分支功能（parent_session_id 关联）
- [x] 11.14 编写 schema 迁移测试

## 12. 上下文压缩实现

- [x] 12.1 创建 `src/compression/` 目录及 `__init__.py`
- [x] 12.2 实现 `ContextCompressor` 类（compressor.py）
- [x] 12.3 实现 `_prune_old_tool_results()` 方法（Phase 1：修剪旧工具结果）
- [x] 12.4 实现 `_protect_head_size()` 和 `_align_boundary_forward()` 方法（Phase 2：Head 保护）
- [x] 12.5 实现 `_find_tail_cut_by_tokens()` 方法（Phase 2：Tail Token 预算保护）
- [x] 12.6 实现 `_ensure_last_user_message_in_tail()` 方法（用户消息锚定）
- [x] 12.7 实现 `_serialize_for_summary()` 方法（序列化待摘要内容）
- [x] 12.8 实现 `_generate_summary()` 方法（Phase 3：LLM 摘要生成）
- [x] 12.9 实现 `_compute_summary_budget()` 方法（摘要预算计算）
- [x] 12.10 实现 `_fallback_to_main_for_compression()` 方法（辅助模型回退）
- [x] 12.11 实现 `_sanitize_tool_pairs()` 方法（Phase 5：清理孤儿工具对）
- [x] 12.12 实现 `_strip_historical_media()` 方法（历史媒体剥离）
- [x] 12.13 实现 `compress()` 主方法（5 阶段压缩入口）
- [x] 12.14 实现摘要模板常量（SUMMARY_PREFIX + 结构化章节）
- [x] 12.15 实现工具结果去重和参数截断逻辑
- [x] 12.16 实现失败处理和 cooldown 机制
- [x] 12.17 实现反抖动保护（连续 2 次 <10% 节省跳过）
- [x] 12.18 实现会话分裂逻辑（end_session + create_session + parent_session_id）
- [x] 12.19 实现 `/compress` TUI 命令处理
- [x] 12.20 实现 `/compress <focus topic>` 焦点主题压缩
- [x] 12.21 集成到 TUI 对话循环（自动触发检查）
- [x] 12.22 编写上下文压缩单元测试
- [x] 12.23 编写上下文压缩集成测试
