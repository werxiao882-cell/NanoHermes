"""数据库 Schema 定义。

包含三个核心表和 FTS5 全文搜索索引：

1. sessions 表：会话元数据
   - session_id: 唯一标识（UUID）
   - parent_session_id: 父会话（压缩延续/分支时设置）
   - title: 会话标题（唯一）
   - created_at / ended_at: 时间戳
   - end_reason: 结束原因
   - model / provider: 使用的模型和提供商
   - token 计数

2. messages 表：对话消息
   - message_id: 唯一标识
   - session_id: 所属会话
   - role: user / assistant / system / tool
   - content: 消息内容
   - tool_calls: 工具调用（JSON）
   - timestamp: 时间戳

3. state_meta 表：会话状态元数据
   - key / value: 键值对存储

4. messages_fts: FTS5 全文搜索虚拟表
5. messages_trigram: trigram 分词器虚拟表（CJK 子串搜索）
"""

# ============================================================================
# 核心表 Schema
# ============================================================================
SCHEMA_SQL = """
-- 会话表
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    parent_session_id TEXT REFERENCES sessions(session_id),
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    end_reason TEXT,
    model TEXT,
    provider TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    system_prompt TEXT,
    metadata TEXT
);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT,
    tool_calls TEXT,
    tool_call_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);

-- 状态元数据表
CREATE TABLE IF NOT EXISTS state_meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);
"""

# ============================================================================
# FTS5 全文搜索（标准 unicode61 分词器）
# ============================================================================
# 用于英文和一般文本的全文搜索
# ============================================================================
FTS_SQL = """
-- FTS5 虚拟表
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='rowid',
    tokenize='unicode61'
);

-- 触发器：消息插入时同步到 FTS
CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content)
    VALUES (NEW.rowid, NEW.content);
END;

-- 触发器：消息删除时同步到 FTS
CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content)
    VALUES ('delete', OLD.rowid, OLD.content);
END;

-- 触发器：消息更新时同步到 FTS
CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content)
    VALUES ('delete', OLD.rowid, OLD.content);
    INSERT INTO messages_fts(rowid, content)
    VALUES (NEW.rowid, NEW.content);
END;
"""

# ============================================================================
# Trigram 分词器（CJK 子串搜索）
# ============================================================================
# 将文本按 3 字符滑动窗口切分，支持中文/日文子串匹配
# 例如："人工智能" → "人工智", "工智能"
# ============================================================================
FTS_TRIGRAM_SQL = """
-- Trigram FTS5 虚拟表
CREATE VIRTUAL TABLE IF NOT EXISTS messages_trigram USING fts5(
    content,
    content='messages',
    content_rowid='rowid',
    tokenize='trigram'
);

-- 触发器：消息插入时同步到 trigram
CREATE TRIGGER IF NOT EXISTS messages_trigram_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_trigram(rowid, content)
    VALUES (NEW.rowid, NEW.content);
END;

-- 触发器：消息删除时同步到 trigram
CREATE TRIGGER IF NOT EXISTS messages_trigram_delete AFTER DELETE ON messages BEGIN
    INSERT INTO messages_trigram(messages_trigram, rowid, content)
    VALUES ('delete', OLD.rowid, OLD.content);
END;

-- 触发器：消息更新时同步到 trigram
CREATE TRIGGER IF NOT EXISTS messages_trigram_update AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_trigram(messages_trigram, rowid, content)
    VALUES ('delete', OLD.rowid, OLD.content);
    INSERT INTO messages_trigram(rowid, content)
    VALUES (NEW.rowid, NEW.content);
END;
"""
