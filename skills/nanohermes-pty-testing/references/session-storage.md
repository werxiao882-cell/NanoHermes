# 会话存储 — 70 用例

## 会话生命周期 (13)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-01 | 创建新会话 | 启动 NanoHermes | 生成唯一会话 ID (UUID v4) | [PTY] |
| S-02 | 用户消息存储 | 发送消息 | JSONL 包含用户消息 | [PTY] |
| S-03 | 助手消息存储 | AI 回复 | JSONL 含助手+工具调用 | [PTY] |
| S-13 | 空会话创建 | 新会话创建 | 无历史消息 | [PTY] |
| S-12 | ID 格式验证 | 检查会话 ID | UUID v4 格式(8-4-4-4-12) | [PTY] |
| S-15 | 大会话性能 | 100+ 轮对话 | JSONL 文件大小合理(<10MB) | [UNIT] |
| S-30 | 创建会话 UUID | 不传 session_id | 自动生成 UUID v4 | [PTY] |
| S-31 | 创建会话传 ID | 传自定义 session_id | 使用指定 ID | [UNIT] |
| S-32 | 分支会话 | branch_session | parent_session_id 指向原会话 | [UNIT] |
| S-33 | 结束会话 | end_session | ended_at 和 end_reason 设置 | [PTY] |
| S-34 | 重新打开会话 | reopen_session | ended_at 和 end_reason 清空 | [UNIT] |
| S-35 | 获取会话 | get_session | 返回完整会话信息 | [PTY] |
| S-69 | 上下文管理器 | with SessionDB() as db | __enter__/__exit__ 正确 | [UNIT] |
| S-120 | 会话元数据 | 检查 sessions 表 | model/title 字段正确 | [PTY] |
| S-121 | 会话时间戳 | 检查 created_at | 包含时间戳 | [PTY] |
| S-122 | 会话结束原因 | /quit 后检查 | end_reason='user_quit' | [PTY] |

## 会话管理 (10)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-04 | 列出会话 | `/sessions` 命令 | 显示历史会话 | [PTY] |
| S-11 | 列表排序 | 多会话后查看 | 按时间倒序排列 | [PTY] |
| S-05 | 恢复会话 | `--resume` 重启 | 最近会话完整恢复 | [PTY] |
| S-14 | 标题匹配恢复 | `--resume-title "标题"` | 模糊匹配恢复 | [UNIT] |
| S-56 | 列出会话 limit | list_sessions limit=10 | 限制返回数量 | [PTY] |
| S-57 | 搜索会话标题 | search_sessions_by_title keyword | LIKE 搜索 | [PTY] |
| S-123 | 多会话列表 | 创建 3 个会话后列出 | 显示 3 个会话 | [PTY] |
| S-124 | 会话标题显示 | 检查 /sessions 输出 | 显示会话标题 | [PTY] |
| S-125 | 会话模型显示 | 检查 /sessions 输出 | 显示使用的模型 | [PTY] |
| S-126 | 会话时间显示 | 检查 /sessions 输出 | 显示创建时间 | [PTY] |
| S-127 | 会话消息数 | 检查 /sessions 输出 | 显示消息数量 | [PTY] |
| S-128 | 会话工具调用数 | 检查 /sessions 输出 | 显示工具调用数 | [PTY] |
| S-129 | 空会话列表 | 无会话时列出 | 显示"无会话" | [PTY] |
| S-130 | 会话删除 | 删除会话后列出 | 不再显示 | [PTY] |

## 会话存储验证 (10)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-08 | 标题自动生成 | 对话多轮后检查 | 标题格式正确 | [PTY] |
| S-18 | JSONL 格式验证 | 检查每行 JSON | 每行完整 JSON，无截断 | [PTY] |
| S-19 | 消息时间戳 | 检查 JSONL 字段 | 含时间戳字段 | [PTY] |
| S-09 | role 分类验证 | user/assistant/system | 分类正确 | [PTY] |
| S-10 | tool_result 格式 | 检查工具结果 | 格式正确存储 | [PTY] |
| S-20 | 元数据完整性 | SQLite 字段 | model/token_count/cost 完整 | [PTY] |
| S-131 | JSONL 消息完整性 | 发送消息后检查 JSONL | 包含 role/content/timestamp | [PTY] |
| S-132 | JSONL 工具调用 | 调用工具后检查 JSONL | 包含 tool_calls 字段 | [PTY] |
| S-133 | JSONL 工具结果 | 工具返回后检查 JSONL | 包含 tool_result 字段 | [PTY] |
| S-134 | JSONL 思考内容 | AI 思考后检查 JSONL | 包含 reasoning 字段 | [PTY] |
| S-135 | JSONL 使用量 | AI 回复后检查 JSONL | 包含 usage 字段 | [PTY] |
| S-136 | SQLite 消息表 | 检查 messages 表 | 包含所有消息 | [PTY] |
| S-137 | SQLite 消息角色 | 检查 messages.role | user/assistant/tool 正确 | [PTY] |
| S-138 | SQLite 消息时间 | 检查 messages.timestamp | 时间戳正确 | [PTY] |

## 数据库特性 (8)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-06 | FTS5 搜索 | `/sessions` + 关键词 | 找到相关会话 | [PTY] |
| S-07 | WAL 并发 | 快速消息写入 | 无锁竞争 | [UNIT] |
| S-16 | WAL 模式验证 | `PRAGMA journal_mode` | 返回 "wal" | [PTY] |
| S-17 | FTS5 索引 | 检查虚拟表 | FTS5 虚拟表存在 | [UNIT] |
| S-21 | WAL 回退机制 | NFS 文件系统 | 回退到 DELETE 模式 | [UNIT] |
| S-22 | 外键约束 | 创建会话时 | 外键启用 | [UNIT] |
| S-23 | schema 协调 | 添加新列到 SCHEMA_SQL | 自动添加缺失列 | [UNIT] |
| S-24 | trigram 分词器 | CJK 子串搜索 | trigram 索引创建 | [UNIT] |
| S-139 | FTS5 中文搜索 | 搜索中文会话标题 | 正确匹配 | [PTY] |

## WAL 与重试 (7)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-25 | BEGIN IMMEDIATE | 并发写入时 | 最早暴露锁竞争 | [UNIT] |
| S-26 | 抖动重试 | 锁竞争时 20-150ms 随机延迟 | 打破 convoy effect | [UNIT] |
| S-27 | 定期 checkpoint | 每 50 次写入 | WAL checkpoint 执行 | [UNIT] |
| S-28 | 最大重试 15 次 | 持续锁竞争 | 达到最大重试抛出异常 | [UNIT] |
| S-29 | PASSIVE checkpoint | 写入后 checkpoint | WAL 帧回写主文件 | [UNIT] |
| S-68 | 关闭数据库 | close() | 最终 checkpoint 后关闭 | [UNIT] |
| S-70 | 重复关闭 | close() 多次 | 幂等操作 | [UNIT] |

## 消息管理 (12)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-39 | 插入消息 user | insert_message role=user | 消息正确存储 | [PTY] |
| S-40 | 插入消息 assistant | insert_message role=assistant+tool_calls | 工具调用存储 | [PTY] |
| S-41 | 插入消息 tool | insert_message role=tool+tool_call_id | 工具结果存储 | [PTY] |
| S-42 | 消息 reasoning | insert_message reasoning 字段 | 思考内容存储 | [DEBUG] |
| S-43 | 消息 observed 字段 | observed=True | 标记为已观察 | [UNIT] |
| S-44 | 获取消息 | get_messages | 按时间排序返回 | [PTY] |
| S-45 | 搜索消息 FTS5 | search_messages query | FTS5 全文搜索 | [UNIT] |
| S-46 | 搜索消息 trigram | search_messages use_trigram=True | CJK 子串搜索 | [UNIT] |
| S-47 | 搜索消息限定会话 | search_messages session_id | 过滤到特定会话 | [UNIT] |
| S-140 | 消息顺序 | 发送多条消息后获取 | 按时间顺序返回 | [PTY] |
| S-141 | 消息内容完整性 | 发送长消息后获取 | 内容完整无截断 | [PTY] |
| S-142 | 消息工具调用 | AI 调用工具后检查 | tool_calls 字段正确 | [PTY] |
| S-143 | 消息工具结果 | 工具返回后检查 | tool_result 正确关联 | [PTY] |
| S-144 | 消息系统提示 | 启动后检查 | system 消息存在 | [PTY] |
| S-145 | 消息数量统计 | 发送 N 条消息后检查 | messages 表有 N 条 | [PTY] |

## 标题管理 (10)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-48 | 设置标题 | set_session_title | 标题存储并清理 | [PTY] |
| S-49 | 获取标题 | get_session_title | 返回标题或 None | [PTY] |
| S-50 | 标题精确匹配 | resolve_session_by_title | 精确匹配返回 ID | [PTY] |
| S-51 | 标题编号变体 | resolve_session_by_title 'title #2' | 搜索编号变体 | [UNIT] |
| S-52 | 标题编号生成 | get_next_title_in_lineage | 生成 #N+1 标题 | [UNIT] |
| S-53 | 标题清理 | sanitize_title | 去除控制字符/折叠空白 | [UNIT] |
| S-54 | 标题空值拒绝 | sanitize_title '' | ValueError | [UNIT] |
| S-55 | 标题超长拒绝 | sanitize_title 超 100 字符 | ValueError | [UNIT] |
| S-146 | /title 命令 | `/title 我的测试会话` | 标题更新成功 | [PTY] |
| S-147 | 标题显示 | /sessions 后检查 | 显示自定义标题 | [PTY] |
| S-148 | 标题恢复 | `--resume-title "我的测试会话"` | 通过标题恢复 | [PTY] |
| S-149 | 标题特殊字符 | `/title 测试 <>&"'` | 特殊字符被清理 | [PTY] |
| S-150 | 标题中文 | `/title 中文标题测试` | 中文标题正常 | [PTY] |

## Token 与计数 (10)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-58 | Token 增量更新 | update_token_counts incremental=True | 增量累加 | [PTY] |
| S-59 | Token 绝对更新 | update_token_counts incremental=False | 绝对覆盖 | [UNIT] |
| S-60 | cache tokens | cache_read/write_tokens | 缓存 token 统计 | [DEBUG] |
| S-61 | reasoning tokens | reasoning_tokens | 思考 token 统计 | [DEBUG] |
| S-62 | 消息计数 +1 | increment_message_count | message_count 增加 | [PTY] |
| S-63 | 工具计数 +1 | increment_tool_call_count | tool_call_count 增加 | [PTY] |
| S-64 | API 计数 +1 | increment_api_call_count | api_call_count 增加 | [DEBUG] |
| S-65 | 计费信息更新 | update_billing_info | COALESCE 不覆盖已有值 | [UNIT] |
| S-66 | 成本信息更新 | update_cost_info | 预估/实际成本更新 | [UNIT] |
| S-67 | 交接信息更新 | update_handoff_info | 交接状态/平台/错误 | [UNIT] |
| S-151 | 状态栏 token | 对话后检查状态栏 | 显示 token 数量 | [PTY] |
| S-152 | token 累加 | 多轮对话后检查 | token 数量递增 | [PTY] |
| S-153 | 消息计数验证 | 发送 5 条消息后检查 | message_count=5 | [PTY] |
| S-154 | 工具计数验证 | 调用 3 次工具后检查 | tool_call_count=3 | [PTY] |

## 压缩延续 (2)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-36 | 更新系统提示 | update_system_prompt | 系统提示快照更新 | [DEBUG] |
| S-37 | 压缩延续链 | get_compression_tip | walk parent_session_id | [UNIT] |
| S-38 | 压缩延续深度限制 | 100 层限制 | 防止无限循环 | [UNIT] |

## 会话恢复 (8)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-155 | --resume 恢复 | `python -m src.main --resume` | 恢复最近会话 | [PTY] |
| S-156 | --resume <id> | `python -m src.main --resume <id>` | 恢复指定会话 | [PTY] |
| S-157 | --resume-title | `python -m src.main --resume-title "标题"` | 通过标题恢复 | [PTY] |
| S-158 | --list-sessions | `python -m src.main --list-sessions` | 列出所有会话 | [PTY] |
| S-159 | 恢复后历史 | 恢复后查看历史 | 显示之前对话 | [PTY] |
| S-160 | 恢复后继续 | 恢复后发送消息 | 对话继续 | [PTY] |
| S-161 | 恢复不存在会话 | `--resume 不存在的 ID` | 友好提示 | [PTY] |
| S-162 | 恢复后工具调用 | 恢复后调用工具 | 工具正常工作 | [PTY] |

## 测试优先级

**P0（阶段 5 必测）**：S-01~03, S-04, S-05, S-06, S-08, S-11~13, S-16, S-18~20, S-30, S-33, S-35, S-39~41, S-44, S-48~50, S-53, S-56~58, S-62~64

**P1（需 --debug）**：S-36, S-42, S-60, S-61, S-64

**P2（仅单元测试）**：S-07, S-09~10, S-14~15, S-17, S-21~29, S-31, S-32, S-34, S-37, S-38, S-43, S-45~47, S-51, S-52, S-54, S-55, S-59, S-60, S-61, S-65~69
