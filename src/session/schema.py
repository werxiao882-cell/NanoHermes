"""数据库 Schema 定义。

对齐 hermes-agent-ref 的会话存储 Schema，包含：

1. sessions 表：会话元数据（25+ 字段）
   - id: 主键（session_id）
   - source: 来源平台（local/telegram/discord 等）
   - user_id: 用户标识
   - model: 模型名称
   - model_config: 模型配置（JSON）
   - system_prompt: 系统提示
   - parent_session_id: 父会话（分支/压缩延续）
   - started_at / ended_at: 时间戳（REAL，Unix 时间）
   - end_reason: 结束原因
   - message_count / tool_call_count / api_call_count: 计数器
   - input_tokens / output_tokens / cache_read_tokens / cache_write_tokens / reasoning_tokens
   - billing_provider / billing_base_url / billing_mode: 计费信息
   - estimated_cost_usd / actual_cost_usd: 成本估算
   - cost_status / cost_source / pricing_version: 成本来源
   - title: 会话标题
   - handoff_state / handoff_platform / handoff_error: 交接信息

2. messages 表：对话消息（15+ 字段）
   - id: 自增主键
   - session_id: 所属会话
   - role: user / assistant / system / tool
   - content: 消息内容
   - tool_call_id: 工具调用 ID
   - tool_calls: 工具调用列表（JSON）
   - tool_name: 工具名称
   - timestamp: 时间戳（REAL，Unix 时间）
   - token_count: Token 数量
   - finish_reason: 完成原因
   - reasoning: 思考内容
   - reasoning_content: 思考内容（备用）
   - reasoning_details: 思考详情（JSON）
   - codex_reasoning_items: Codex 推理项（JSON）
   - codex_message_items: Codex 消息项（JSON）
   - platform_message_id: 平台消息 ID
   - observed: 是否已观察（0/1）

3. state_meta 表：会话状态元数据

4. messages_fts: FTS5 全文搜索虚拟表
5. messages_fts_trigram: trigram 分词器虚拟表（CJK 子串搜索）
"""

# ============================================================================
# 核心表 Schema（对齐 hermes-agent-ref）
# ============================================================================
SCHEMA_SQL = """
-- Schema 版本管理
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

-- 会话表（对齐 hermes-agent-ref sessions 表）
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'local',
    user_id TEXT,
    model TEXT,
    model_config TEXT,
    system_prompt TEXT,
    parent_session_id TEXT REFERENCES sessions(id),
    started_at REAL NOT NULL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    billing_provider TEXT,
    billing_base_url TEXT,
    billing_mode TEXT,
    estimated_cost_usd REAL,
    actual_cost_usd REAL,
    cost_status TEXT,
    cost_source TEXT,
    pricing_version TEXT,
    title TEXT,
    api_call_count INTEGER DEFAULT 0,
    handoff_state TEXT,
    handoff_platform TEXT,
    handoff_error TEXT
);

-- 消息表（对齐 hermes-agent-ref messages 表）
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT,
    tool_call_id TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    timestamp REAL NOT NULL,
    token_count INTEGER,
    finish_reason TEXT,
    reasoning TEXT,
    reasoning_content TEXT,
    reasoning_details TEXT,
    codex_reasoning_items TEXT,
    codex_message_items TEXT,
    platform_message_id TEXT,
    observed INTEGER DEFAULT 0
);

-- 状态元数据表
CREATE TABLE IF NOT EXISTS state_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source);
CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_title ON sessions(title);

"""

# ============================================================================
# FTS5 全文搜索（标准 unicode61 分词器）
# ============================================================================
FTS_SQL = """
-- FTS5 虚拟表
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content
);

-- 触发器：消息插入时同步到 FTS
CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;

-- 触发器：消息删除时同步到 FTS
CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.id;
END;

-- 触发器：消息更新时同步到 FTS
CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.id;
    INSERT INTO messages_fts(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;
"""

# ============================================================================
# Trigram 分词器（CJK 子串搜索）
# ============================================================================
FTS_TRIGRAM_SQL = """
-- Trigram FTS5 虚拟表
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_trigram USING fts5(
    content,
    tokenize='trigram'
);

-- 触发器：消息插入时同步到 trigram
CREATE TRIGGER IF NOT EXISTS messages_fts_trigram_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts_trigram(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;

-- 触发器：消息删除时同步到 trigram
CREATE TRIGGER IF NOT EXISTS messages_fts_trigram_delete AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts_trigram WHERE rowid = old.id;
END;

-- 触发器：消息更新时同步到 trigram
CREATE TRIGGER IF NOT EXISTS messages_fts_trigram_update AFTER UPDATE ON messages BEGIN
    DELETE FROM messages_fts_trigram WHERE rowid = old.id;
    INSERT INTO messages_fts_trigram(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;
"""
