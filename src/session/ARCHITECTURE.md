# Session Storage Architecture

## Responsibility
SQLite 会话持久化存储，支持 WAL 并发、FTS5 全文搜索、JSONL 完整历史、会话恢复。
是所有其他功能（记忆、压缩、委托）的基础层。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    SessionDB (SQLite)                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Schema                                                 │  │
│  │  - sessions: id, source, user_id, model, system_prompt │  │
│  │    parent_session_id, started_at, ended_at, end_reason │  │
│  │    message_count, tool_call_count, api_call_count      │  │
│  │    input_tokens, output_tokens, cache_read_tokens      │  │
│  │    cache_write_tokens, reasoning_tokens                │  │
│  │    billing_provider, billing_base_url, billing_mode    │  │
│  │    estimated_cost_usd, actual_cost_usd                 │  │
│  │    cost_status, cost_source, pricing_version           │  │
│  │    title, handoff_state, handoff_platform, handoff_error│  │
│  │  - messages: id, session_id, role, content, tool_calls │  │
│  │    tool_call_id, tool_name, timestamp, token_count     │  │
│  │    finish_reason, reasoning, reasoning_content         │  │
│  │    reasoning_details, codex_reasoning_items            │  │
│  │    codex_message_items, platform_message_id, observed  │  │
│  │  - state_meta: key, value                              │  │
│  │  - schema_version: version                             │  │
│  │                                                        │  │
│  │  索引:                                                 │  │
│  │  - idx_sessions_source, idx_sessions_parent            │  │
│  │  - idx_sessions_started (DESC), idx_sessions_title     │  │
│  │  - idx_messages_session (session_id, timestamp)        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  WAL Mode + Jitter Retry                                │  │
│  │  - PRAGMA journal_mode=WAL (fallback to DELETE)        │  │
│  │  - BEGIN IMMEDIATE: 事务开始时获取写锁                  │  │
│  │  - 15 次重试 + 20-150ms 随机抖动打破 convoy effect     │  │
│  │  - 每 50 次写入执行 PASSIVE checkpoint                 │  │
│  │  - 关闭时执行最终 checkpoint                            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Declarative Schema Reconciliation                      │  │
│  │  - SCHEMA_SQL 为唯一真实来源                            │  │
│  │  - 内存 SQLite 解析期望列                               │  │
│  │  - 对比 live 列，自动 ALTER TABLE ADD COLUMN            │  │
│  │  - 无需版本控制的迁移代码                               │  │
│  │  - schema_version 表保留用于未来数据迁移                │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  FTS5 Search                                            │  │
│  │  - messages_fts: unicode61 tokenizer (英文/精确匹配)   │  │
│  │  - messages_fts_trigram: trigram tokenizer (CJK 子串)  │  │
│  │  - Triggers: INSERT/DELETE/UPDATE 自动同步             │  │
│  │  - 零配置全文搜索，无需外部引擎或向量嵌入               │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Session Lifecycle                                      │  │
│  │  - create_session(): INSERT OR IGNORE 幂等创建         │  │
│  │  - end_session(): WHERE ended_at IS NULL 防重复结束    │  │
│  │  - reopen_session(): 清除 ended_at/end_reason          │  │
│  │  - branch_session(): 创建子会话（parent_session_id）   │  │
│  │  - update_system_prompt(): 冻结 system_prompt 快照     │  │
│  │  - update_token_counts(): 增量/绝对模式更新            │  │
│  │  - get_compression_tip(): walk 压缩延续链              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Title Management                                       │  │
│  │  - sanitize_title(): 去除控制字符/零宽字符，100 字符   │  │
│  │  - set_session_title(): 更新标题                        │  │
│  │  - get_session_title(): 获取标题                        │  │
│  │  - resolve_session_by_title(): 精确匹配 + 编号变体     │  │
│  │  - get_next_title_in_lineage(): 生成下一个编号标题     │  │
│  │  - list_sessions(): 按时间倒序列出                      │  │
│  │  - search_sessions_by_title(): 标题关键词搜索           │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Compression Lineage                                    │  │
│  │  - parent_session_id 外键形成血缘链                    │  │
│  │  - started_at >= parent.ended_at 区分压缩延续和委托    │  │
│  │  - end_reason='compression' 标记压缩分割               │  │
│  │  - 限制 walk 深度（100）防御性                          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                 JsonlSessionStore                             │
│                                                              │
│  - 每个会话一个 JSONL 文件: {session_id}.jsonl               │
│  - 存储路径: ~/.nanohermes/sessions/                         │
│  - 格式: {role, content, tool_calls, timestamp, reasoning}  │
│  - 操作: append_message, load_messages, list_sessions       │
│  - Complements SQLite: SQLite 用于搜索/统计，JSONL 用于     │
│    完整历史恢复                                               │
│  - 支持: session_exists, delete_session, get_message_count  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

### 初始化流程
1. `SessionDB(db_path)` → 创建父目录 → 建立连接
2. `_apply_wal()` → WAL 模式（失败回退 DELETE）
3. `_enable_foreign_keys()` → 外键约束
4. `init_schema()` → 创建核心表 → FTS5 索引 → trigram 索引
5. `_reconcile_schema()` → 内存解析期望列 → 对比添加缺失列 → 更新 schema_version

### 会话生命周期
1. **创建**: `create_session()` → INSERT OR IGNORE → 返回 session_id
2. **保存消息**: `insert_message()` → messages 表插入 → message_count 自动递增 → FTS5 触发器自动更新索引
3. **更新 token**: `update_token_counts(incremental=True)` → 增量累加
4. **结束会话**: `end_session(reason)` → WHERE ended_at IS NULL → 防重复
5. **压缩延续**: `branch_session(parent_id)` → 新会话 parent_session_id 指向父会话
6. **恢复会话**: `reopen_session()` → 清除 ended_at/end_reason
7. **获取压缩 tip**: `get_compression_tip()` → walk parent_session_id 链 → 返回最新延续

### 搜索流程
1. **消息搜索**: `search_messages(query, session_id=None, use_trigram=False)`
   - FTS5 MATCH 查询 → JOIN messages → 返回匹配消息
   - use_trigram=True 使用 trigram 分词器（CJK 子串搜索）
2. **标题搜索**: `search_sessions_by_title(keyword, limit=10)`
   - LIKE 模糊匹配 → 按时间倒序

### 标题管理
1. **设置标题**: `set_session_title()` → sanitize_title() → UPDATE
2. **解析标题**: `resolve_session_by_title()` → 精确匹配 → 编号变体匹配
3. **生成编号**: `get_next_title_in_lineage()` → 剥离 #N → 找最大编号 → 生成下一个

## Design Decisions

| Decision | Reason |
|----------|--------|
| **双存储层（SQLite + JSONL）** | SQLite 用于搜索和统计，JSONL 用于完整历史恢复。SQLite 提供结构化查询，JSONL 提供流式追加和完整上下文 |
| **WAL 模式 + 应用层抖动重试** | WAL 支持多读单写并发。BEGIN IMMEDIATE 提前暴露锁竞争。20-150ms 随机抖动打破 convoy effect（SQLite 内置 busy handler 使用确定性退避） |
| **FTS5 + trigram 双索引** | unicode61 分词器将 CJK 字符分割成单字符，破坏短语匹配。trigram 创建重叠 3 字节序列，支持任何脚本的子串搜索 |
| **声明式 schema 协调** | SCHEMA_SQL 为唯一真实来源。添加新列只需修改 SQL，下次启动自动协调。无需版本控制的迁移代码 |
| **不用 ORM** | 需要精确控制事务边界（BEGIN IMMEDIATE）。ORM 的连接池和自动事务管理会与自定义 jitter retry 冲突 |
| **system_prompt 快照** | 存储每个 session 的完整 system prompt，用于会话恢复、缓存失效或进程重建时复原同一段冻结前缀 |
| **parent_session_id 血缘链** | 形成可追溯的会话 lineage。started_at >= ended_at 条件区分压缩延续和委托子节点 |
| **INSERT OR IGNORE 幂等创建** | 相同 session_id 重复创建不产生错误，支持恢复场景 |
| **end_session WHERE ended_at IS NULL** | 防止重复结束，第一次的 end_reason 获胜 |
| **title 索引（非 UNIQUE）** | 支持同名会话（如恢复后分支），通过 `get_next_title_in_lineage()` 生成编号变体区分 |
| **insert_message 自动递增 message_count** | 避免应用层手动维护计数，减少不一致风险 |

## Dependencies
- Internal: None（自包含模块）
- External: sqlite3 (Python stdlib), uuid (Python stdlib)

## Configuration Constants
```python
MAX_RETRIES = 15           # 写锁竞争最大重试次数
RETRY_MIN_MS = 0.020       # 最小抖动延迟（20ms）
RETRY_MAX_MS = 0.150       # 最大抖动延迟（150ms）
CHECKPOINT_INTERVAL = 50   # 每 N 次写入执行 checkpoint
MAX_TITLE_LENGTH = 100     # 标题最大长度
```

## FTS5 全文搜索原理

### 倒排索引（Inverted Index）

FTS5 不扫描全表，而是维护**词 → 行 ID** 的倒排索引：

```
原始消息:                      倒排索引:
"bug fix completed"    →       bug → [rowid=1, rowid=3]
"test message"         →       fix → [rowid=1]
"bug found"            →       completed → [rowid=1]
                               test → [rowid=2]
                               message → [rowid=2]
                               found → [rowid=3]
```

搜索 `MATCH 'bug'` 时直接查索引返回 rowid=1,3，时间复杂度 O(1) 而非 O(n)。

### 分词器（Tokenizer）对比

| 分词器 | 分词方式 | "测试消息" 分词结果 | 搜索"测试" |
|--------|---------|-------------------|-----------|
| unicode61（默认） | 按 Unicode 边界分割 | 测、试、消、息（单字） | 需前缀匹配 `测*` |
| trigram | 重叠 3 字节序列 | 测、测试、试消、测试消、试、消息、息 | 直接子串匹配 |

**trigram 原理：**
```
输入: "测试消息"
输出: "测", "测试", "测试消", "试", "试消", "试消息", "消", "消息", "息"
      (所有 1-3 字符的重叠子串)
```

### 为什么需要双索引

| 场景 | unicode61 | trigram |
|------|-----------|---------|
| 英文精确匹配 | ✅ `MATCH 'bug'` | ✅ `MATCH 'bug'` |
| 英文前缀匹配 | ✅ `MATCH 'bu*'` | ✅ `MATCH 'bu*'` |
| 中文单字搜索 | ✅ `MATCH '测*'` | ✅ `MATCH '测'` |
| 中文短语搜索 | ❌ 无法匹配连续短语 | ✅ `MATCH '测试'` |
| 混合语言 | ✅ 英文好，中文差 | ✅ 所有语言一致 |

**设计决策：** 同时创建两个 FTS5 虚拟表，英文搜索用 unicode61（更精确），中文/混合搜索用 trigram（支持子串）。

### 触发器同步机制

FTS5 是虚拟表，不存储实际数据，需要通过触发器保持与 messages 表同步：

```sql
-- 插入时同步
CREATE TRIGGER messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;

-- 删除时同步
CREATE TRIGGER messages_fts_delete AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.id;
END;

-- 更新时同步（先删后插）
CREATE TRIGGER messages_fts_update AFTER UPDATE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.id;
    INSERT INTO messages_fts(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;
```

**同步内容组合：** `content + tool_name + tool_calls`，使搜索能覆盖消息内容、工具名称和工具调用参数。

### 触发更新时机

FTS5 虚拟表的更新完全由 SQLite 触发器自动处理，**不需要应用层手动调用同步方法**。

| messages 表操作 | 触发的触发器 | FTS5 表动作 |
|----------------|-------------|------------|
| `INSERT INTO messages` | `messages_fts_insert` | `INSERT INTO messages_fts` |
| `DELETE FROM messages` | `messages_fts_delete` | `DELETE FROM messages_fts WHERE rowid = old.id` |
| `UPDATE messages` | `messages_fts_update` | 先 `DELETE` 旧记录，再 `INSERT` 新记录 |

**代码中的触发点：**

```python
# 1. insert_message() 调用时
db.insert_message(sid, "user", "你好")
# ↓ 自动触发 messages_fts_insert
# ↓ FTS5 索引立即更新

# 2. 直接删除消息时
db.conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
db.conn.commit()
# ↓ 自动触发 messages_fts_delete
# ↓ FTS5 索引立即删除对应条目

# 3. 直接更新消息时
db.conn.execute("UPDATE messages SET content = ? WHERE id = ?", ("新内容", msg_id))
db.conn.commit()
# ↓ 自动触发 messages_fts_update
# ↓ FTS5 索引先删后插
```

**关键点：**
*   只要操作 `messages` 表，触发器就会在同一个事务内自动同步 FTS5 索引。
*   这是“零配置”的核心原因——创建触发器后，应用代码完全不需要关心 FTS5 的维护。

### 搜索查询示例

```sql
-- 英文精确搜索（unicode61）
SELECT m.* FROM messages m
JOIN messages_fts f ON m.id = f.rowid
WHERE messages_fts MATCH 'bug'
ORDER BY rank;

-- 中文子串搜索（trigram）
SELECT m.* FROM messages m
JOIN messages_fts_trigram f ON m.id = f.rowid
WHERE messages_fts_trigram MATCH '测试'
ORDER BY rank;

-- 按会话过滤
SELECT m.* FROM messages m
JOIN messages_fts f ON m.id = f.rowid
WHERE messages_fts MATCH 'error' AND m.session_id = 'xxx'
ORDER BY rank;
```

### FTS5 vs 向量搜索

| 特性 | FTS5 | 向量搜索（RAG） |
|------|------|----------------|
| 配置 | 零配置，SQLite 内置 | 需要嵌入模型、向量数据库 |
| 网络 | 无需网络调用 | 需要 API 调用或本地模型 |
| 精确匹配 | ✅ 精确文本匹配 | ❌ 语义相似，可能不精确 |
| 子串搜索 | ✅ trigram 支持 | ❌ 需要 n-gram 预处理 |
| 适用场景 | 历史对话精确搜索 | 语义理解、知识检索 |

**设计决策：** 个人 Agent 的历史搜索场景需要精确匹配（如"上次那个 deploy 脚本"），FTS5 比 RAG 更简单可靠。
