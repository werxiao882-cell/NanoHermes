# Session Database Architecture

## Responsibility
SQLite 会话持久化存储，支持 WAL 并发、FTS5 全文搜索、会话生命周期管理、
标题管理和 lineage 追踪。是所有其他功能（记忆、压缩、委托）的基础层。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                      SessionDB                                │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Schema Management                                      │  │
│  │  - SCHEMA_SQL (sessions, messages, state_meta)          │  │
│  │  - FTS_SQL (messages_fts virtual table)                 │  │
│  │  - FTS_TRIGRAM_SQL (CJK trigram tokenizer)             │  │
│  │  - Schema reconciliation (auto-add missing columns)     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Session Lifecycle                                      │  │
│  │  - create_session()                                     │  │
│  │  - end_session(session_id, reason)                      │  │
│  │  - reopen_session(session_id)                           │  │
│  │  - branch_session(session_id) → new child session       │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Message Management                                     │  │
│  │  - insert_message(session_id, role, content, ...)       │  │
│  │  - get_messages(session_id)                             │  │
│  │  - search_messages(query, session_filter)               │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Title Management                                       │  │
│  │  - set_session_title(session_id, title)                 │  │
│  │  - get_session_title(session_id)                        │  │
│  │  - resolve_session_by_title(title)                      │  │
│  │  - lineage title resolution (latest in chain)           │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 启动时：initSchema() → WAL 模式 → FTS5 索引 → schema reconciliation
2. 会话创建：create_session() → sessions 表插入 → 返回 session_id
3. 消息保存：insert_message() → messages 表插入 → FTS5 触发器自动更新
4. 搜索：search_messages() → FTS5 MATCH 查询 → 返回匹配消息
5. 会话结束：end_session() → 更新 ended_at 和 end_reason
6. 压缩延续：branch_session() → 创建子会话（parent_session_id 指向父会话）

## Design Decisions
- **Decision**: 使用 Python sqlite3 标准库
  - **Reason**: 零额外依赖，WAL 模式支持良好
- **Decision**: WAL 模式 + 应用层抖动重试
  - **Reason**: 支持并发读取，单写入。写锁竞争通过重试解决
- **Decision**: FTS5 + trigram 双索引
  - **Reason**: unicode61 分词器不支持 CJK 子串搜索，trigram 补充

## Dependencies
- Internal: None (基础层)
- External: sqlite3 (Python 标准库)
