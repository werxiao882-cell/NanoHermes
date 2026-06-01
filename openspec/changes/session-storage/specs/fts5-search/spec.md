## ADDED Requirements

### Requirement: 系统 SHALL 创建 FTS5 全文搜索索引
系统 SHALL 创建 messages_fts 虚拟表，使用 unicode61 分词器。FTS 索引 SHALL 包含 content、tool_name、tool_calls 字段的组合。

**设计理由：** FTS5 提供零配置全文搜索——不需要外部搜索引擎，不需要向量嵌入，不需要网络调用。对于个人 Agent 的历史搜索场景，这比复杂的 RAG 方案更简单可靠。

#### Scenario: 创建 FTS 虚拟表
- **WHEN** SessionDB 初始化时
- **THEN** 创建 messages_fts 虚拟表，如果不存在

#### Scenario: FTS 触发器同步
- **WHEN** messages 表插入新记录
- **THEN** messages_fts_insert 触发器自动将 content || tool_name || tool_calls 插入 FTS 索引

### Requirement: 系统 SHALL 创建 trigram FTS5 索引用于 CJK 搜索
系统 SHALL 创建 messages_fts_trigram 虚拟表，使用 trigram 分词器。trigram 分词器 SHALL 创建重叠的 3 字节序列，支持任何脚本的子串搜索。

#### Scenario: 创建 trigram 虚拟表
- **WHEN** SessionDB 初始化时
- **THEN** 创建 messages_fts_trigram 虚拟表，使用 tokenize='trigram'

#### Scenario: CJK 子串搜索
- **WHEN** 用户使用中文字符串搜索
- **THEN** trigram FTS 表返回包含该子串的消息

### Requirement: FTS 索引 SHALL 通过触发器保持同步
系统 SHALL 创建 INSERT、DELETE、UPDATE 触发器，确保 FTS 索引与 messages 表保持同步。

#### Scenario: 插入同步
- **WHEN** 新消息插入 messages 表
- **THEN** messages_fts_insert 和 messages_fts_trigram_insert 触发器自动更新 FTS 索引

#### Scenario: 删除同步
- **WHEN** 消息从 messages 表删除
- **THEN** messages_fts_delete 和 messages_fts_trigram_delete 触发器自动从 FTS 索引删除

#### Scenario: 更新同步
- **WHEN** 消息在 messages 表更新
- **THEN** messages_fts_update 和 messages_fts_trigram_update 触发器先删除旧记录再插入新记录

### Requirement: 系统 SHALL 支持跨会话消息搜索
系统 SHALL 提供搜索方法，接受搜索关键词，返回匹配的消息列表，包含 session_id、role、content、timestamp 字段。

#### Scenario: 搜索所有会话
- **WHEN** 用户搜索关键词 "bug"
- **THEN** 系统返回所有包含 "bug" 的消息，跨所有会话

#### Scenario: 按会话过滤搜索
- **WHEN** 用户在特定会话中搜索
- **THEN** 系统只返回该会话中匹配的消息
