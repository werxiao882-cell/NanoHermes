## 上下文

业界成熟的自进化 AI Agent 系统的会话存储模块 (~2000 LOC) 实现了完整的 SQLite 会话存储系统。核心设计决策包括：
- WAL 模式用于并发读取 + 单写入（网关多平台场景）
- FTS5 虚拟表用于快速文本搜索
- 压缩触发的会话分割通过 parent_session_id 链实现
- 会话源标记（'cli'、'telegram'、'discord' 等）用于过滤
- 声明式 schema 协调（Beets/sqlite-utils 模式）

NanoHermes 使用 Python sqlite3 模块实现相同的功能。

## 目标 / 非目标

**目标：**
- 实现完整的 SessionDB 类，支持所有标准会话操作
- 实现 FTS5 全文搜索，包括 trigram 分词器
- 实现会话生命周期管理和 lineage 追踪
- 实现声明式 schema 协调
- 实现 WAL 写锁竞争的应用层抖动重试

**非目标：**
- 不实现 kanban 数据库（独立系统）
- 不实现 batch runner 轨迹存储（独立系统）
- 不实现网关平台特定的会话处理

## 技术方案

### 1. SQLite 连接管理

**技术方案：** 使用 Python sqlite3 模块，保持长连接。

```python
import sqlite3
import os
import random
import time
import logging

logger = logging.getLogger(__name__)

class SessionDB:
    def __init__(self, db_path: str):
        # 确保父目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 连接配置
        self._conn = sqlite3.connect(db_path)
        self._write_count = 0
        
        # WAL 模式（带 fallback）
        self._apply_wal_with_fallback()
        
        # 外键约束
        self._conn.execute("PRAGMA foreign_keys = ON")
        
        # 初始化 schema
        self._init_schema()
    
    def _apply_wal_with_fallback(self):
        try:
            self._conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.OperationalError as err:
            if "locking protocol" in str(err).lower():
                self._conn.execute("PRAGMA journal_mode = DELETE")
                logger.warning('WAL 不支持，回退到 DELETE 模式')
            else:
                raise
```

**WAL 不兼容检测：** NFS/SMB/FUSE 文件系统会抛出 "locking protocol" 错误。捕获后回退到 DELETE 模式。

### 2. Schema 定义

**技术方案：** SCHEMA_SQL 作为唯一真实来源，使用 executescript 创建表。

```python
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    user_id TEXT,
    model TEXT,
    model_config TEXT,
    system_prompt TEXT,
    parent_session_id TEXT,
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
    handoff_error TEXT,
    FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
);

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
    platform_message_id TEXT,
    observed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS state_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source);
CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp);
"""
```

### 3. FTS5 全文搜索

**技术方案：** 创建两个 FTS5 虚拟表，使用触发器保持同步。

```python
FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content
);

CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.id;
    INSERT INTO messages_fts(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;
"""

# Trigram 分词器用于 CJK 子串搜索
FTS_TRIGRAM_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_trigram USING fts5(
    content,
    tokenize='trigram'
);
-- 触发器同上...
"""
```

**为什么需要 trigram：** 默认 unicode61 分词器会将 CJK 字符分割成单个字符，破坏短语匹配。trigram 分词器创建重叠的 3 字节序列，使子串查询对任何脚本（CJK、泰语等）都能正常工作。

### 4. 声明式 Schema 协调

**技术方案：** 使用内存 SQLite 数据库解析 SCHEMA_SQL，提取期望的列，然后与实际列对比。

```python
def _reconcile_columns(self):
    # 使用内存数据库解析 schema
    ref = sqlite3.connect(':memory:')
    ref.executescript(SCHEMA_SQL)
    
    expected = self._parse_schema_columns(ref)
    ref.close()
    
    # 对比 live 列和期望列
    for table_name, declared_cols in expected.items():
        live_cols = self._get_live_columns(table_name)
        
        for col_name, col_type in declared_cols.items():
            if col_name not in live_cols:
                try:
                    self._conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type}')
                except sqlite3.OperationalError as err:
                    logger.debug(f'协调 {table_name}.{col_name}: {err}')

def _parse_schema_columns(self, ref):
    cursor = ref.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    result = {}
    
    for table_name in tables:
        cursor = ref.execute(f'PRAGMA table_info({table_name})')
        cols = cursor.fetchall()
        col_map = {}
        
        for col in cols:
            # col: (cid, name, type, notnull, dflt_value, pk)
            cid, name, col_type, notnull, dflt_value, pk = col
            parts = [col_type or '']
            if notnull and not pk:
                parts.append('NOT NULL')
            if dflt_value is not None:
                parts.append(f'DEFAULT {dflt_value}')
            col_map[name] = ' '.join(parts)
        
        result[table_name] = col_map
    
    return result
```

**优势：** 添加新列只需修改 SCHEMA_SQL，下次启动时自动协调。不需要版本控制的迁移代码。

### 5. 写锁竞争处理

**技术方案：** 应用层重试 + 随机抖动，打破 SQLite 内置的确定性退避造成的 convoy 效应。

```python
def _execute_write(self, fn):
    MAX_RETRIES = 15
    RETRY_MIN_MS = 0.020  # 20ms
    RETRY_MAX_MS = 0.150  # 150ms
    
    last_err = None
    
    for attempt in range(MAX_RETRIES):
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                result = fn(self._conn)
                self._conn.commit()
                
                # 定期 checkpoint
                self._write_count += 1
                if self._write_count % 50 == 0:
                    self._try_wal_checkpoint()
                
                return result
            except BaseException:
                self._conn.rollback()
                raise
        except sqlite3.OperationalError as err:
            if "locked" in str(err).lower():
                last_err = err
                if attempt < MAX_RETRIES - 1:
                    jitter = random.uniform(RETRY_MIN_MS, RETRY_MAX_MS)
                    time.sleep(jitter)
                    continue
            raise
    
    raise last_err or sqlite3.OperationalError('数据库锁定，达到最大重试次数')

def _try_wal_checkpoint(self):
    try:
        cursor = self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        result = cursor.fetchone()
        if result and result[0] > 0:
            logger.debug(f'WAL checkpoint: {result[1]}/{result[0]} 页')
    except Exception:
        # 尽力而为，从不失败
        pass
```

**为什么用抖动：** SQLite 内置的 busy handler 使用确定性退避，在高并发下会造成 convoy 效应。随机抖动自然错开竞争写入者。

### 6. 会话标题管理

**技术方案：** 唯一标题索引 + lineage 解析。

```python
# 创建唯一标题索引
UNIQUE_TITLE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_title_unique 
ON sessions(title) WHERE title IS NOT NULL
"""

def resolve_session_by_title(self, title: str) -> str | None:
    # 1. 精确匹配
    cursor = self._conn.execute(
        'SELECT id FROM sessions WHERE title = ? ORDER BY started_at DESC LIMIT 1',
        (title,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # 2. 搜索编号变体 "title #2", "title #3"
    escaped = title.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    cursor = self._conn.execute(
        f"SELECT id FROM sessions WHERE title LIKE ? ESCAPE '\\' ORDER BY started_at DESC",
        (f'{escaped} #%',)
    )
    rows = cursor.fetchall()
    if rows:
        return rows[0][0]
    
    return None

def get_next_title_in_lineage(self, base_title: str) -> str:
    import re
    # 剥离现有 #N 后缀
    match = re.match(r'^(.*?) #(\d+)$', base_title)
    base = match.group(1) if match else base_title
    
    # 查找现有编号变体
    escaped = base.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    cursor = self._conn.execute(
        f"SELECT title FROM sessions WHERE title = ? OR title LIKE ? ESCAPE '\\'",
        (base, f'{escaped} #%')
    )
    existing = [row[0] for row in cursor.fetchall()]
    
    if not existing:
        return base
    
    # 找到最大编号
    max_num = 1
    for title in existing:
        m = re.match(r'^.* #(\d+)$', title)
        if m:
            max_num = max(max_num, int(m.group(1)))
    
    return f'{base} #{max_num + 1}'
```

### 7. 压缩延续链解析

**技术方案：** 循环查询 walk parent_session_id 链。

```python
def get_compression_tip(self, session_id: str) -> str:
    current = session_id
    
    # 限制 walk 深度（防御性）
    for _ in range(100):
        cursor = self._conn.execute("""
            SELECT id FROM sessions 
            WHERE parent_session_id = ? 
                AND started_at >= (
                    SELECT ended_at FROM sessions 
                    WHERE id = ? AND end_reason = 'compression'
                ) 
            ORDER BY started_at DESC LIMIT 1
        """, (current, current))
        row = cursor.fetchone()
        
        if not row:
            return current
        current = row[0]
    
    return current
```

**设计决策：** 第二个条件（started_at >= ended_at）区分压缩延续和委托子 agent 或分支子节点，后者也可以在 parent_session_id 有值，但是在父节点还活着时创建的。

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| FTS5 trigram 分词器在某些 SQLite 构建中不可用 | Python 标准库 sqlite3 包含 FTS5，跨平台一致 |
| WAL 文件在网络文件系统上可能损坏 | 检测 "locking protocol" 错误，回退到 DELETE 模式 |
| 声明式 schema 协调无法处理数据迁移（行转换） | 保留 schema_version 表，用于未来的数据迁移 |

## 设计启示

SessionDB 展示了"为个人 Agent 选择存储方案"的关键考量：

1. **SQLite > PostgreSQL**：零配置、单文件部署、无守护进程——适合个人 VPS 场景
2. **WAL > 默认 journal**：支持并发读写——Gateway 多平台并发的必需
3. **应用级 retry > SQLite busy handler**：随机 jitter 打破 convoy effect
4. **FTS5 > 向量搜索**：对于精确的文本匹配，FTS5 更简单可靠
5. **不用 ORM**：需要精确控制事务边界，ORM 的连接池和自动事务管理会与自定义的 jitter retry 冲突
6. **system_prompt 快照**：存储每个 session 的完整 system prompt，用于会话恢复、缓存失效或进程重建时复原同一段冻结前缀
7. **parent_session_id 血缘链**：形成可追溯的会话 lineage，用户可以追溯一次长对话的完整历史
8. **BEGIN IMMEDIATE**：在事务开始时就获取写锁，让锁竞争在最早时刻暴露
