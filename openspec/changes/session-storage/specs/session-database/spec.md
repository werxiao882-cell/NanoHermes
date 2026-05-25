## ADDED Requirements

### Requirement: 系统 SHALL 使用 SQLite 作为会话存储
系统 SHALL 使用 better-sqlite3 创建 SQLite 数据库，包含 sessions 表、messages 表、state_meta 表。数据库路径 SHALL 可配置，默认存储在 NanoHermes home 目录下。

#### Scenario: 创建数据库连接
- **WHEN** SessionDB 初始化时
- **THEN** 创建 SQLite 连接，确保父目录存在，设置 WAL 模式和外键约束

#### Scenario: WAL 模式回退
- **WHEN** WAL 模式在不支持的文件系统上（NFS/SMB/FUSE）抛出 "locking protocol" 错误
- **THEN** 系统回退到 DELETE 日志模式，并记录一次 WARNING

### Requirement: 会话表 SHALL 存储完整会话元数据
sessions 表 SHALL 包含：id (TEXT PRIMARY KEY)、source、user_id、model、model_config、system_prompt、parent_session_id、started_at、ended_at、end_reason、message_count、tool_call_count、input_tokens、output_tokens、cache_read_tokens、cache_write_tokens、reasoning_tokens、billing_provider、billing_base_url、billing_mode、estimated_cost_usd、actual_cost_usd、cost_status、cost_source、pricing_version、title、api_call_count、handoff_state、handoff_platform、handoff_error。

#### Scenario: 插入会话记录
- **WHEN** 新会话创建时
- **THEN** 插入包含 id、source、model、started_at 的记录，其他字段为默认值

#### Scenario: 更新 token 计数
- **WHEN** API 调用完成后
- **THEN** 增量更新 input_tokens、output_tokens、cache_read_tokens、cache_write_tokens、reasoning_tokens、api_call_count

### Requirement: 消息表 SHALL 存储完整对话历史
messages 表 SHALL 包含：id (INTEGER PRIMARY KEY AUTOINCREMENT)、session_id、role、content、tool_call_id、tool_calls、tool_name、timestamp、token_count、finish_reason、reasoning、reasoning_content、reasoning_details、platform_message_id、observed。

#### Scenario: 插入消息记录
- **WHEN** 对话轮次完成后
- **THEN** 插入包含 session_id、role、content、timestamp 的记录

#### Scenario: 存储工具调用
- **WHEN** 模型返回工具调用时
- **THEN** tool_calls 字段存储 JSON 格式的工具调用数组，tool_name 存储首个工具名称

### Requirement: 写操作 SHALL 使用 BEGIN IMMEDIATE + 抖动重试
系统 SHALL 使用 BEGIN IMMEDIATE 开始写事务，在 "database is locked" 错误时使用应用层重试 + 随机抖动（20-150ms）。最大重试次数 SHALL 为 15 次。

#### Scenario: 写锁竞争重试
- **WHEN** 写操作遇到 "database is locked" 错误
- **THEN** 系统等待 20-150ms 随机时间后重试，最多 15 次

#### Scenario: 非锁定错误传播
- **WHEN** 写操作遇到非锁定错误（如约束违反）
- **THEN** 错误立即传播，不进行重试

### Requirement: 系统 SHALL 定期执行 WAL checkpoint
系统 SHALL 在每 50 次成功写操作后执行 PASSIVE WAL checkpoint，防止 WAL 文件无限增长。

#### Scenario: 定期 checkpoint
- **WHEN** 写操作计数达到 50 的倍数
- **THEN** 执行 PRAGMA wal_checkpoint(PASSIVE)，记录 checkpoint 结果
