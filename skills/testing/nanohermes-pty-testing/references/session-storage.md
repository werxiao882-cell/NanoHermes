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

## 会话管理 (4)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-04 | 列出会话 | `/sessions` 命令 | 显示历史会话 | [PTY] |
| S-11 | 列表排序 | 多会话后查看 | 按时间倒序排列 | [PTY] |
| S-05 | 恢复会话 | `--resume` 重启 | 最近会话完整恢复 | [PTY] |
| S-14 | 标题匹配恢复 | `--resume-title "标题"` | 模糊匹配恢复 | [UNIT] |
| S-56 | 列出会话 limit | list_sessions limit=10 | 限制返回数量 | [PTY] |
| S-57 | 搜索会话标题 | search_sessions_by_title keyword | LIKE 搜索 | [PTY] |

## 会话存储验证 (6)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-08 | 标题自动生成 | 对话多轮后检查 | 标题格式正确 | [PTY] |
| S-18 | JSONL 格式验证 | 检查消息格式 | ⚠️ **多行 pretty-print 格式**（非紧凑单行）。用 `grep '"role":'` 统计角色分布。每条消息 `{...}` 含 role/timestamp 字段 | [PTY] |
| S-19 | 消息时间戳 | 检查 JSONL 字段 | 含时间戳字段 | [PTY] |
| S-09 | role 分类验证 | user/assistant/system | 分类正确 | [PTY] |
| S-10 | tool_result 格式 | 检查工具结果 | 格式正确存储 | [PTY] |
| S-20 | 元数据完整性 | SQLite 字段 | model/token_count/cost 完整 | [PTY] |

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

## 消息管理 (8)
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

## 标题管理 (8)
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

## Token 与计数 (8)
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

## 压缩延续 (2)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| S-36 | 更新系统提示 | update_system_prompt | 系统提示快照更新 | [DEBUG] |
| S-37 | 压缩延续链 | get_compression_tip | walk parent_session_id | [UNIT] |
| S-38 | 压缩延续深度限制 | 100 层限制 | 防止无限循环 | [UNIT] |

## 测试优先级

**P0（阶段 5 必测）**：S-01~03, S-04, S-05, S-06, S-08, S-11~13, S-16, S-18~20, S-30, S-33, S-35, S-39~41, S-44, S-48~50, S-53, S-56~58, S-62~64

**⚠️ 已知问题**：`message_count`、`tool_call_count`、`api_call_count` 在 SQLite 中可能为 0（实际消息已正确存储到 JSONL）。验证会话完整性应直接统计 JSONL 消息数，不要依赖 SQLite 计数器。详见 `references/test-findings.md`。

**P1（需 --debug）**：S-36, S-42, S-60, S-61, S-64

**P2（仅单元测试）**：S-07, S-09~10, S-14~15, S-17, S-21~29, S-31, S-32, S-34, S-37, S-38, S-43, S-45~47, S-51, S-52, S-54, S-55, S-59, S-60, S-61, S-65~69
