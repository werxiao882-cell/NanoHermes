# src/session — 会话持久化存储模块

## 模块概述

SQLite + JSONL 双存储层，为 NanoHermes 提供会话生命周期管理、消息持久化、全文搜索和完整历史恢复。
是所有上层功能（记忆、压缩、委托）的基础数据层。

## 文件职责

```
src/session/
├── __init__.py        # 模块入口，re-export 公开 API
├── schema.py          # 声明式 SQL schema 定义（核心表 + FTS5 索引）
├── session_db.py      # SessionDB 主类（SQLite 封装、WAL、重试、生命周期、搜索）
└── jsonl_store.py     # JsonlSessionStore（per-session JSONL 文件，流式追加完整历史）
```

- **`schema.py`** — 定义 `SCHEMA_SQL`、`FTS_SQL`、`FTS_TRIGRAM_SQL` 三段 SQL 常量，作为 schema 唯一真实来源
- **`session_db.py`** — 封装 SQLite 连接管理、事务重试、schema 协调、会话 CRUD、消息插入/搜索、标题管理、token 计数
- **`jsonl_store.py`** — 每个会话一个 JSONL 文件，增量追加消息记录（含 session_start/user/assistant/tool_call/tool_result）

## 核心数据流

### 初始化
```
SessionDB(db_path)
  → _connect() → _apply_wal() → _enable_foreign_keys()
  → init_schema()
      → executescript(SCHEMA_SQL)
      → executescript(FTS_SQL)
      → executescript(FTS_TRIGRAM_SQL)  [trigram 不可用时静默跳过]
      → _reconcile_schema()  → 内存 SQLite 解析期望列 → ALTER TABLE ADD COLUMN 补齐
```

### 写入路径
```
ConversationLoop 事件
  → insert_message()
      → BEGIN IMMEDIATE → INSERT INTO messages → commit
      → message_count 自动递增（仅 user/assistant/system）
      → SQLite 触发器自动同步 messages_fts / messages_fts_trigram
      → 每 50 次写触发 PASSIVE WAL checkpoint

JsonlSessionStore.append_message()
  → open(file, "a") → json.dumps() → write line
```

### 会话生命周期
```
create_session() → INSERT OR IGNORE（幂等）
    ↓
insert_message() [多次]
    ↓
end_session(reason) → WHERE ended_at IS NULL（防重复结束）
    ↓
branch_session() → create_session(parent_session_id=原会话)
    ↓
get_compression_tip() → walk parent_session_id 链 → 返回最新延续 ID
```

### 恢复路径
```
--resume 模式
  → JsonlSessionStore.load_messages() → 从 JSONL 解析完整历史
  → SessionDB.get_session() → 获取元数据（model, system_prompt 等）
  → ConversationLoop 重建上下文
```

## 关键设计决策

| 决策 | 理由 |
|------|------|
| **双存储 SQLite + JSONL** | SQLite 提供结构化查询/搜索/统计；JSONL 提供流式追加和完整上下文恢复，两者互补 |
| **WAL + BEGIN IMMEDIATE + 抖动重试** | WAL 支持多读单写。BEGIN IMMEDIATE 在事务开始就获取写锁，提前暴露竞争。20-150ms 随机 jitter 打破 convoy effect（优于 SQLite 内置 busy handler 的确定性退避） |
| **FTS5 双索引 unicode61 + trigram** | unicode61 将 CJK 拆成单字，破坏短语匹配；trigram 创建重叠 3 字符序列，支持任意语言的子串搜索 |
| **声明式 schema 协调** | 添加新列只需修改 `SCHEMA_SQL`，启动时用内存 SQLite 解析期望列并自动补齐，无需维护迁移版本 |
| **不用 ORM** | 需要精确控制事务边界（BEGIN IMMEDIATE）和重试策略，ORM 的连接池/自动事务管理会与自定义重试冲突 |
| **INSERT OR IGNORE 幂等创建** | 相同 session_id 重复创建不报错，支持崩溃恢复场景 |
| **end_session WHERE ended_at IS NULL** | 防止重复结束，第一次的 end_reason 获胜 |
| **title 索引非 UNIQUE** | 支持同名会话（恢复/分支场景），通过 `get_next_title_in_lineage()` 生成 #N 编号变体 |
| **insert_message 自动递增计数** | 避免应用层手动维护 message_count，减少不一致风险 |
| **system_prompt 快照存储** | 会话恢复或缓存失效时可复原冻结前缀，无需重新生成 |

## 对外接口

### 公开类
- **`SessionDB(db_path)`** — 支持 context manager（`with SessionDB(...) as db:`）
- **`JsonlSessionStore(base_dir=None)`** — 默认存储路径 `~/.nanohermes/sessions/`

### SessionDB 公开方法
| 方法 | 用途 |
|------|------|
| `create_session(...)` | 创建会话，返回 session_id |
| `end_session(id, reason)` | 结束会话 |
| `reopen_session(id)` | 重新打开已结束的会话 |
| `branch_session(parent_id)` | 创建子会话（压缩延续） |
| `get_session(id)` | 获取会话信息 dict |
| `get_compression_tip(id)` | 获取压缩延续链最新会话 ID |
| `insert_message(...)` | 插入消息，返回 message id |
| `get_messages(id)` | 获取会话全部消息列表 |
| `search_messages(query, ...)` | FTS5 全文搜索消息 |
| `set_session_title(id, title)` | 设置标题 |
| `resolve_session_by_title(title)` | 按标题解析 session_id |
| `get_next_title_in_lineage(base)` | 生成 lineage 中下一个编号标题 |
| `list_sessions(limit)` | 列出会话（按时间倒序） |
| `search_sessions_by_title(keyword)` | 标题关键词搜索 |
| `update_token_counts(...)` | 更新 token 计数（增量/绝对） |
| `increment_message_count(id)` | 消息计数 +1 |
| `increment_tool_call_count(id)` | 工具调用计数 +1 |
| `increment_api_call_count(id)` | API 调用计数 +1 |
| `update_billing_info(...)` | 更新计费信息 |
| `update_cost_info(...)` | 更新成本信息 |
| `update_handoff_info(...)` | 更新交接信息 |
| `update_system_prompt(id, prompt)` | 更新系统提示快照 |

### 公开函数
- **`sanitize_title(title)`** — 清理标题（去控制字符/零宽字符，折叠空白，限 100 字符）
- **`get_sessions_list_for_display()`** — 结合 JSONL + SQLite 数据，返回展示用会话列表

### 公开常量
- `SCHEMA_SQL` / `FTS_SQL` / `FTS_TRIGRAM_SQL` — 声明式 schema SQL

### JsonlSessionStore 公开方法
| 方法 | 用途 |
|------|------|
| `start_session(id, model, ...)` | 记录会话开始元数据 |
| `append_message(id, role, ...)` | 追加消息记录 |
| `load_messages(id)` | 加载完整会话历史 |
| `session_exists(id)` | 检查 JSONL 文件是否存在 |
| `list_sessions()` | 列出所有有 JSONL 文件的会话 ID |
| `delete_session(id)` | 删除会话 JSONL 文件 |
| `get_message_count(id)` | 获取消息数量 |

## 依赖关系

- **内部依赖**: 无（自包含模块）
- **外部依赖**: `sqlite3`、`json`、`uuid`、`re`、`time`、`pathlib`（均为 Python 标准库）

## 配置常量（session_db.py）

| 常量 | 值 | 用途 |
|------|----|------|
| `MAX_RETRIES` | 15 | 写锁竞争最大重试次数 |
| `RETRY_MIN_MS` | 0.020 | 抖动延迟下限（20ms） |
| `RETRY_MAX_MS` | 0.150 | 抖动延迟上限（150ms） |
| `CHECKPOINT_INTERVAL` | 50 | 每 N 次写入执行 WAL checkpoint |
| `MAX_TITLE_LENGTH` | 100 | 标题最大字符数 |
