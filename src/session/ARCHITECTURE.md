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
│  │  - sessions: session_id, parent_session_id, title,     │  │
│  │    created_at, ended_at, end_reason, model, provider,  │  │
│  │    input_tokens, output_tokens, cache_read_tokens,     │  │
│  │    cache_write_tokens, system_prompt, metadata         │  │
│  │  - messages: message_id, session_id, role, content,    │  │
│  │    tool_calls, tool_call_id, timestamp, metadata       │  │
│  │  - state_meta: key, value, updated_at                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  WAL Mode + Jitter Retry                                │  │
│  │  - Concurrent reads, single write                      │  │
│  │  - BEGIN IMMEDIATE + retry on lock contention          │  │
│  │  - PASSIVE checkpoint on close                         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  FTS5 Search                                            │  │
│  │  - messages_fts: unicode61 tokenizer (English)         │  │
│  │  - messages_trigram: trigram tokenizer (CJK)           │  │
│  │  - Triggers: sync on insert/update/delete              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Session Lifecycle                                      │  │
│  │  - create_session() → new session with UUID            │  │
│  │  - end_session(reason) → set ended_at, end_reason      │  │
│  │  - reopen_session() → clear ended_at, end_reason       │  │
│  │  - branch_session() → child session with parent link   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Title Management                                       │  │
│  │  - set_session_title() → unique title                  │  │
│  │  - get_session_title() → title or None                 │  │
│  │  - resolve_session_by_title() → exact or numbered match│  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                 JsonlSessionStore                             │
│                                                              │
│  - Append-only JSONL file per session                        │
│  - Format: {role, content, tool_calls, tool_call_id, ...}   │
│  - Operations: append_message, load_messages, list_sessions │
│  - Complements SQLite: SQLite for search/stats, JSONL for   │
│    full history recovery                                     │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 启动时：initSchema() → WAL 模式 → FTS5 索引 → schema reconciliation
2. 会话创建：create_session() → sessions 表插入 → 返回 session_id
3. 消息保存：insert_message() → messages 表插入 + JSONL 追加 → FTS5 触发器自动更新
4. 搜索：search_messages() → FTS5 MATCH 查询 → 返回匹配消息
5. 会话结束：end_session() → 更新 ended_at 和 end_reason
6. 压缩延续：branch_session() → 创建子会话（parent_session_id 指向父会话）
7. 会话恢复：load_messages() → 从 JSONL 加载完整历史 → 重建消息列表

## Design Decisions
- **Decision**: 双存储层（SQLite + JSONL）
  - **Reason**: SQLite 用于搜索和统计，JSONL 用于完整历史恢复
- **Decision**: WAL 模式 + 应用层抖动重试
  - **Reason**: 支持并发读取，单写入。写锁竞争通过重试解决
- **Decision**: FTS5 + trigram 双索引
  - **Reason**: unicode61 分词器不支持 CJK 子串搜索，trigram 补充

## Dependencies
- Internal: None (基础层)
- External: sqlite3 (Python stdlib)
