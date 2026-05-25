## 上下文

业界成熟的自进化 AI Agent 系统的会话存储模块 (~2000 LOC) 实现了完整的 SQLite 会话存储系统。核心设计决策包括：
- WAL 模式用于并发读取 + 单写入（网关多平台场景）
- FTS5 虚拟表用于快速文本搜索
- 压缩触发的会话分割通过 parent_session_id 链实现
- 会话源标记（'cli'、'telegram'、'discord' 等）用于过滤
- 声明式 schema 协调（Beets/sqlite-utils 模式）

NanoHermes 需要在 TypeScript 中实现相同的功能，使用 better-sqlite3 作为 SQLite 绑定。

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

**技术方案：** 使用 better-sqlite3 同步 API，每个方法打开自己的游标。

```typescript
import Database from 'better-sqlite3';

class SessionDB {
  private db: Database.Database;
  private writeCount = 0;
  
  constructor(dbPath: string) {
    // 确保父目录存在
    ensureDirSync(dirname(dbPath));
    
    // 连接配置
    this.db = new Database(dbPath);
    
    // WAL 模式（带 fallback）
    this.applyWalWithFallback();
    
    // 外键约束
    this.db.pragma('foreign_keys = ON');
    
    // 初始化 schema
    this.initSchema();
  }
  
  private applyWalWithFallback(): void {
    try {
      this.db.pragma('journal_mode = WAL');
    } catch (err) {
      if (isWalIncompatible(err)) {
        this.db.pragma('journal_mode = DELETE');
        logger.warn('WAL 不支持，回退到 DELETE 模式');
      } else {
        throw err;
      }
    }
  }
}
```

**WAL 不兼容检测：** NFS/SMB/FUSE 文件系统会抛出 "locking protocol" 错误。捕获后回退到 DELETE 模式。

### 2. Schema 定义

**技术方案：** SCHEMA_SQL 作为唯一真实来源，使用 executescript 创建表。

```typescript
const SCHEMA_SQL = `
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
`;
```

### 3. FTS5 全文搜索

**技术方案：** 创建两个 FTS5 虚拟表，使用触发器保持同步。

```typescript
const FTS_SQL = `
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
`;

// Trigram 分词器用于 CJK 子串搜索
const FTS_TRIGRAM_SQL = `
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_trigram USING fts5(
  content,
  tokenize='trigram'
);
-- 触发器同上...
`;
```

**为什么需要 trigram：** 默认 unicode61 分词器会将 CJK 字符分割成单个字符，破坏短语匹配。trigram 分词器创建重叠的 3 字节序列，使子串查询对任何脚本（CJK、泰语等）都能正常工作。

### 4. 声明式 Schema 协调

**技术方案：** 使用内存 SQLite 数据库解析 SCHEMA_SQL，提取期望的列，然后与实际列对比。

```typescript
private reconcileColumns(): void {
  // 使用内存数据库解析 schema
  const ref = new Database(':memory:');
  ref.exec(SCHEMA_SQL);
  
  const expected = this.parseSchemaColumns(ref);
  ref.close();
  
  // 对比 live 列和期望列
  for (const [tableName, declaredCols] of Object.entries(expected)) {
    const liveCols = this.getLiveColumns(tableName);
    
    for (const [colName, colType] of Object.entries(declaredCols)) {
      if (!liveCols.has(colName)) {
        try {
          this.db.exec(`ALTER TABLE "${tableName}" ADD COLUMN "${colName}" ${colType}`);
        } catch (err) {
          logger.debug(`协调 ${tableName}.${colName}: ${err}`);
        }
      }
    }
  }
}

private parseSchemaColumns(ref: Database.Database): Map<string, Map<string, string>> {
  const tables = ref.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
  const result = new Map();
  
  for (const { name: tableName } of tables) {
    const cols = ref.pragma(`table_info(${tableName})`) as any[];
    const colMap = new Map();
    
    for (const col of cols) {
      const parts = [col.type || ''];
      if (col.notnull && !col.pk) parts.push('NOT NULL');
      if (col.dflt_value !== null) parts.push(`DEFAULT ${col.dflt_value}`);
      colMap.set(col.name, parts.join(' '));
    }
    
    result.set(tableName, colMap);
  }
  
  return result;
}
```

**优势：** 添加新列只需修改 SCHEMA_SQL，下次启动时自动协调。不需要版本控制的迁移代码。

### 5. 写锁竞争处理

**技术方案：** 应用层重试 + 随机抖动，打破 SQLite 内置的确定性退避造成的 convoy 效应。

```typescript
private executeWrite<T>(fn: (db: Database.Database) => T): T {
  const MAX_RETRIES = 15;
  const RETRY_MIN_MS = 20;
  const RETRY_MAX_MS = 150;
  
  let lastErr: Error | null = null;
  
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      this.db.exec('BEGIN IMMEDIATE');
      try {
        const result = fn(this.db);
        this.db.exec('COMMIT');
        
        // 定期 checkpoint
        this.writeCount++;
        if (this.writeCount % 50 === 0) {
          this.tryWalCheckpoint();
        }
        
        return result;
      } catch (err) {
        this.db.exec('ROLLBACK');
        throw err;
      }
    } catch (err) {
      if (isLockError(err)) {
        lastErr = err;
        if (attempt < MAX_RETRIES - 1) {
          const jitter = randomInt(RETRY_MIN_MS, RETRY_MAX_MS);
          sleep(jitter);
          continue;
        }
      }
      throw err;
    }
  }
  
  throw lastErr || new Error('数据库锁定，达到最大重试次数');
}

private tryWalCheckpoint(): void {
  try {
    const result = this.db.pragma('wal_checkpoint(PASSIVE)') as any[];
    if (result[0]?.pages > 0) {
      logger.debug(`WAL checkpoint: ${result[0].pages_checkpointed}/${result[0].pages} 页`);
    }
  } catch {
    // 尽力而为，从不失败
  }
}
```

**为什么用抖动：** SQLite 内置的 busy handler 使用确定性退避，在高并发下会造成 convoy 效应。随机抖动自然错开竞争写入者。

### 6. 会话标题管理

**技术方案：** 唯一标题索引 + lineage 解析。

```typescript
// 创建唯一标题索引
const UNIQUE_TITLE_INDEX = `
CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_title_unique 
ON sessions(title) WHERE title IS NOT NULL
`;

// 标题解析：精确匹配 → 编号变体 → 最新
resolveSessionByTitle(title: string): string | null {
  // 1. 精确匹配
  const exact = this.db.prepare(
    'SELECT id FROM sessions WHERE title = ? ORDER BY started_at DESC LIMIT 1'
  ).get(title);
  
  if (exact) return (exact as any).id;
  
  // 2. 搜索编号变体 "title #2", "title #3"
  const escaped = title.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '\\_');
  const numbered = this.db.prepare(
    `SELECT id FROM sessions WHERE title LIKE ? ESCAPE '\\' ORDER BY started_at DESC`
  ).all(`${escaped} #%`);
  
  if (numbered.length > 0) return (numbered[0] as any).id;
  
  return null;
}

// 生成 lineage 中的下一个标题
getNextTitleInLineage(baseTitle: string): string {
  // 剥离现有 #N 后缀
  const match = baseTitle.match(/^(.*?) #(\d+)$/);
  const base = match ? match[1] : baseTitle;
  
  // 查找现有编号变体
  const escaped = base.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '\\_');
  const existing = this.db.prepare(
    `SELECT title FROM sessions WHERE title = ? OR title LIKE ? ESCAPE '\\'`
  ).all(base, `${escaped} #%`);
  
  if (existing.length === 0) return base;
  
  // 找到最大编号
  let maxNum = 1;
  for (const row of existing as any[]) {
    const m = row.title.match(/^.* #(\d+)$/);
    if (m) maxNum = Math.max(maxNum, parseInt(m[1]));
  }
  
  return `${base} #${maxNum + 1}`;
}
```

### 7. 压缩延续链解析

**技术方案：** 递归 CTE 或循环查询 walk parent_session_id 链。

```typescript
getCompressionTip(sessionId: string): string {
  let current = sessionId;
  
  // 限制 walk 深度（防御性）
  for (let i = 0; i < 100; i++) {
    const row = this.db.prepare(`
      SELECT id FROM sessions 
      WHERE parent_session_id = ? 
        AND started_at >= (
          SELECT ended_at FROM sessions 
          WHERE id = ? AND end_reason = 'compression'
        ) 
      ORDER BY started_at DESC LIMIT 1
    `).get(current, current);
    
    if (!row) return current;
    current = (row as any).id;
  }
  
  return current;
}
```

**设计决策：** 第二个条件（started_at >= ended_at）区分压缩延续和委托子 agent 或分支子节点，后者也可以在 parent_session_id 有值，但是在父节点还活着时创建的。

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| better-sqlite3 在 Windows 上的预编译二进制可能不匹配 Node 版本 | 使用 electron-rebuild 或从源码编译 |
| FTS5 trigram 分词器在某些 SQLite 构建中不可用 | better-sqlite3 预编译二进制包含 FTS5，跨平台一致 |
| WAL 文件在网络文件系统上可能损坏 | 检测 "locking protocol" 错误，回退到 DELETE 模式 |
| 声明式 schema 协调无法处理数据迁移（行转换） | 保留 schema_version 表，用于未来的数据迁移 |
