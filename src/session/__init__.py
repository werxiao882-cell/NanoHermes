"""会话数据库模块。

SQLite 会话持久化存储，支持：
- WAL 模式并发访问
- FTS5 全文搜索（含 CJK trigram）
- 会话生命周期管理
- 标题管理和 lineage 追踪
- 声明式 schema 协调
- JSONL 格式完整历史存储
"""

from src.session.session_db import SessionDB
from src.session.schema import SCHEMA_SQL, FTS_SQL, FTS_TRIGRAM_SQL
from src.session.jsonl_store import JsonlSessionStore

__all__ = ["SessionDB", "SCHEMA_SQL", "FTS_SQL", "FTS_TRIGRAM_SQL", "JsonlSessionStore"]
