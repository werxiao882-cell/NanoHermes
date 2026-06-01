"""SessionDB - SQLite 会话数据库。

对齐 hermes-agent-ref 的会话存储设计，提供：
1. 创建、结束、恢复、分支会话
2. 消息插入、查询、搜索
3. 标题管理和 lineage 追踪
4. WAL 模式 + 抖动重试
5. Schema 协调
"""

from __future__ import annotations

import logging
import os
import random
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from src.session.schema import SCHEMA_SQL, FTS_SQL, FTS_TRIGRAM_SQL

logger = logging.getLogger(__name__)

# 写锁竞争重试配置
MAX_RETRIES = 15
RETRY_MIN_MS = 0.020  # 20ms
RETRY_MAX_MS = 0.150  # 150ms
CHECKPOINT_INTERVAL = 50  # 每 50 次写入执行一次 checkpoint
MAX_TITLE_LENGTH = 100


class SessionDB:
    """SQLite 会话数据库管理器。

    特性：
    - WAL 模式并发访问（多读单写）
    - 应用层抖动重试处理写锁竞争
    - FTS5 全文搜索 + trigram CJK 子串搜索
    - 声明式 schema 协调（自动添加缺失列）

    Attributes:
        db_path: 数据库文件路径。
        conn: SQLite 连接对象。
        _closed: 是否已关闭。
        _write_count: 写操作计数器。
    """

    def __init__(self, db_path: str | Path):
        """初始化数据库连接。

        Args:
            db_path: 数据库文件路径。目录不存在时自动创建。
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn: sqlite3.Connection | None = None
        self._closed = False
        self._write_count = 0

        self._connect()
        self._apply_wal()
        self._enable_foreign_keys()
        self.init_schema()

    def _connect(self) -> None:
        """建立数据库连接。"""
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
        )
        self.conn.row_factory = sqlite3.Row

    def _apply_wal(self) -> None:
        """应用 WAL 模式，失败回退到 DELETE 模式。

        WAL（Write-Ahead Logging）模式支持：
        - 多个并发读取
        - 单个写入
        - 读取不阻塞写入

        在 NFS/SMB 网络文件系统上 WAL 可能不支持，
        此时回退到传统的 DELETE 模式。
        """
        if self.conn is None:
            return
        try:
            self.conn.execute("PRAGMA journal_mode=WAL")
            result = self.conn.execute("PRAGMA journal_mode").fetchone()
            mode = result[0] if result else "unknown"
            logger.debug(f"Journal mode: {mode}")
        except sqlite3.OperationalError as e:
            logger.warning(f"WAL mode not supported, falling back to DELETE: {e}")
            self.conn.execute("PRAGMA journal_mode=DELETE")

    def _enable_foreign_keys(self) -> None:
        """启用外键约束。"""
        if self.conn:
            self.conn.execute("PRAGMA foreign_keys=ON")

    def init_schema(self) -> None:
        """执行 schema 创建 SQL。

        包括：
        1. 核心表（sessions, messages, state_meta）
        2. FTS5 全文搜索索引
        3. Trigram 分词器索引
        4. Schema 协调（添加缺失列）
        """
        if self.conn is None:
            return

        # 创建核心表
        self.conn.executescript(SCHEMA_SQL)

        # 创建 FTS5 索引
        self.conn.executescript(FTS_SQL)

        # 创建 trigram 索引
        try:
            self.conn.executescript(FTS_TRIGRAM_SQL)
        except sqlite3.OperationalError as e:
            # trigram 分词器可能在某些 SQLite 版本中不可用
            logger.warning(f"Trigram FTS not available: {e}")

        # Schema 协调
        self._reconcile_schema()

    def _reconcile_schema(self) -> None:
        """协调 schema，添加缺失的列。

        使用内存 SQLite 数据库解析 SCHEMA_SQL，提取期望的列，
        然后与实际列对比，自动添加缺失列。

        优势：添加新列只需修改 SCHEMA_SQL，下次启动时自动协调。
        不需要版本控制的迁移代码。
        """
        if self.conn is None:
            return

        # 使用内存数据库解析 schema
        ref = sqlite3.connect(":memory:")
        ref.executescript(SCHEMA_SQL)

        expected = self._parse_schema_columns(ref)
        ref.close()

        # 对比 live 列和期望列
        for table_name, declared_cols in expected.items():
            live_cols = self._get_live_columns(table_name)

            for col_name, col_type in declared_cols.items():
                if col_name not in live_cols:
                    try:
                        self.conn.execute(
                            f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type}'
                        )
                        logger.debug(f"Added column {table_name}.{col_name}")
                    except sqlite3.OperationalError as e:
                        logger.debug(f"Reconcile {table_name}.{col_name}: {e}")

        # 更新 schema_version
        self._update_schema_version()

    def _parse_schema_columns(
        self, ref: sqlite3.Connection
    ) -> dict[str, dict[str, str]]:
        """从内存数据库解析期望的列。

        Args:
            ref: 内存 SQLite 连接。

        Returns:
            表名 -> {列名 -> 列类型表达式} 的映射。
        """
        cursor = ref.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        result = {}

        for table_name in tables:
            cursor = ref.execute(f"PRAGMA table_info({table_name})")
            cols = cursor.fetchall()
            col_map = {}

            for col in cols:
                # col: (cid, name, type, notnull, dflt_value, pk)
                cid, name, col_type, notnull, dflt_value, pk = col
                parts = [col_type or ""]
                if notnull and not pk:
                    parts.append("NOT NULL")
                if dflt_value is not None:
                    parts.append(f"DEFAULT {dflt_value}")
                col_map[name] = " ".join(parts)

            result[table_name] = col_map

        return result

    def _get_live_columns(self, table_name: str) -> dict[str, str]:
        """获取实际数据库表的列。

        Args:
            table_name: 表名。

        Returns:
            列名 -> 列类型 的映射。
        """
        if self.conn is None:
            return {}

        cursor = self.conn.execute(f"PRAGMA table_info({table_name})")
        cols = cursor.fetchall()
        return {col[1]: col[2] for col in cols}

    def _update_schema_version(self) -> None:
        """更新 schema_version 表到当前版本。"""
        if self.conn is None:
            return
        try:
            self.conn.execute("DELETE FROM schema_version")
            self.conn.execute("INSERT INTO schema_version (version) VALUES (1)")
        except sqlite3.OperationalError:
            pass

    def _execute_write(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行写操作，带 BEGIN IMMEDIATE + 抖动重试。

        设计理由：
        - BEGIN IMMEDIATE：在事务开始时就获取写锁，让锁竞争在最早时刻暴露
        - 随机 jitter：20-150ms 的随机延迟打破 convoy effect
        - 定期 checkpoint：每 50 次写入触发一次 WAL checkpoint

        Args:
            sql: SQL 语句。
            params: 参数元组。

        Returns:
            执行结果游标。
        """
        if self.conn is None:
            raise RuntimeError("数据库未连接")

        last_err: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                # 确保没有活跃事务
                self.conn.rollback()
                self.conn.execute("BEGIN IMMEDIATE")
                cursor = self.conn.execute(sql, params)
                self.conn.commit()

                # 定期 checkpoint
                self._write_count += 1
                if self._write_count % CHECKPOINT_INTERVAL == 0:
                    self._try_wal_checkpoint()

                return cursor
            except sqlite3.OperationalError as e:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                if "locked" in str(e).lower() and attempt < MAX_RETRIES - 1:
                    # 抖动重试：20-150ms 随机延迟
                    jitter = random.uniform(RETRY_MIN_MS, RETRY_MAX_MS)
                    time.sleep(jitter)
                    last_err = e
                    continue
                raise
            except BaseException:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                raise

        raise last_err or sqlite3.OperationalError("数据库锁定，达到最大重试次数")

    def _try_wal_checkpoint(self) -> None:
        """执行 PASSIVE WAL checkpoint。

        将 WAL 帧回写到主数据库文件，防止 WAL 文件无限增长。
        失败时不抛出异常（尽力而为）。
        """
        if self.conn is None:
            return
        try:
            cursor = self.conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            result = cursor.fetchone()
            if result and result[0] > 0:
                logger.debug(f"WAL checkpoint: {result[1]}/{result[0]} 页")
        except Exception:
            # 尽力而为，从不失败
            pass

    # ========================================================================
    # 会话生命周期管理
    # ========================================================================

    def create_session(
        self,
        session_id: str | None = None,
        parent_session_id: str | None = None,
        title: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        source: str = "local",
        user_id: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """创建新会话。

        Args:
            session_id: 会话 ID，None 时自动生成 UUID。
            parent_session_id: 父会话 ID（压缩延续/分支时设置）。
            title: 会话标题。
            model: 使用的模型名称。
            provider: 提供商 ID。
            source: 来源平台（local/telegram/discord 等）。
            user_id: 用户标识。
            system_prompt: 系统提示快照。

        Returns:
            会话 ID。
        """
        sid = session_id or str(uuid.uuid4())
        now = time.time()
        sql = """
            INSERT OR IGNORE INTO sessions (id, source, user_id, model, parent_session_id, title, started_at, system_prompt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute_write(sql, (sid, source, user_id, model, parent_session_id, title, now, system_prompt))
        return sid

    def end_session(self, session_id: str, end_reason: str | None = None) -> None:
        """结束会话。

        Args:
            session_id: 会话 ID。
            end_reason: 结束原因（如 "completed", "interrupted", "compressed"）。
        """
        sql = """
            UPDATE sessions SET ended_at = ?, end_reason = ?
            WHERE id = ? AND ended_at IS NULL
        """
        self._execute_write(sql, (time.time(), end_reason, session_id))

    def reopen_session(self, session_id: str) -> None:
        """重新打开已结束的会话。

        Args:
            session_id: 会话 ID。
        """
        sql = """
            UPDATE sessions SET ended_at = NULL, end_reason = NULL
            WHERE id = ?
        """
        self._execute_write(sql, (session_id,))

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """获取会话信息。

        Args:
            session_id: 会话 ID。

        Returns:
            会话信息字典，未找到返回 None。
        """
        if self.conn is None:
            return None
        cursor = self.conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def branch_session(
        self,
        parent_session_id: str,
        title: str | None = None,
    ) -> str:
        """从现有会话分支创建子会话。

        用于压缩延续：压缩后创建新会话，parent_session_id 指向原会话。

        Args:
            parent_session_id: 父会话 ID。
            title: 子会话标题。

        Returns:
            新会话 ID。
        """
        return self.create_session(
            parent_session_id=parent_session_id,
            title=title,
        )

    def update_system_prompt(self, session_id: str, system_prompt: str) -> None:
        """更新会话的系统提示快照。

        Args:
            session_id: 会话 ID。
            system_prompt: 系统提示内容。
        """
        sql = "UPDATE sessions SET system_prompt = ? WHERE id = ?"
        self._execute_write(sql, (system_prompt, session_id))

    def get_compression_tip(self, session_id: str) -> str:
        """获取压缩延续链的最新会话 ID。

        设计决策：通过 started_at >= ended_at 条件区分压缩延续和委托子 agent
        或分支子节点，后者也可以在 parent_session_id 有值，但是在父节点还活着时创建的。

        Args:
            session_id: 起始会话 ID。

        Returns:
            压缩延续链的最新会话 ID。
        """
        if self.conn is None:
            return session_id

        current = session_id

        # 限制 walk 深度（防御性）
        for _ in range(100):
            cursor = self.conn.execute(
                """
                SELECT id FROM sessions
                WHERE parent_session_id = ?
                    AND started_at >= (
                        SELECT ended_at FROM sessions
                        WHERE id = ? AND end_reason = 'compression'
                    )
                ORDER BY started_at DESC LIMIT 1
                """,
                (current, current),
            )
            row = cursor.fetchone()
            if not row:
                return current
            current = row[0]

        return current

    # ========================================================================
    # 消息管理
    # ========================================================================

    def insert_message(
        self,
        session_id: str,
        role: str,
        content: str | None = None,
        tool_calls: str | None = None,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
        reasoning: str | None = None,
        reasoning_content: str | None = None,
        reasoning_details: str | None = None,
        token_count: int | None = None,
        finish_reason: str | None = None,
    ) -> int:
        """插入一条消息。

        Args:
            session_id: 所属会话 ID。
            role: 消息角色（user/assistant/system/tool）。
            content: 消息内容。
            tool_calls: 工具调用 JSON 字符串。
            tool_call_id: 工具调用 ID（tool 角色时设置）。
            tool_name: 工具名称。
            reasoning: 思考内容。
            reasoning_content: 思考内容（备用）。
            reasoning_details: 思考详情（JSON）。
            token_count: Token 数量。
            finish_reason: 完成原因。

        Returns:
            消息 ID（自增）。
        """
        sql = """
            INSERT INTO messages (session_id, role, content, tool_calls, tool_call_id, tool_name, timestamp, reasoning, reasoning_content, reasoning_details, token_count, finish_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor = self._execute_write(sql, (
            session_id, role, content, tool_calls, tool_call_id, tool_name,
            time.time(), reasoning, reasoning_content, reasoning_details,
            token_count, finish_reason,
        ))
        return cursor.lastrowid

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        """获取会话的所有消息。

        Args:
            session_id: 会话 ID。

        Returns:
            消息列表，按时间排序。
        """
        if self.conn is None:
            return []
        cursor = self.conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def search_messages(
        self,
        query: str,
        session_id: str | None = None,
        use_trigram: bool = False,
    ) -> list[dict[str, Any]]:
        """搜索消息（FTS5 全文搜索）。

        Args:
            query: 搜索关键词。
            session_id: 过滤到特定会话（可选）。
            use_trigram: 是否使用 trigram 分词器（CJK 子串搜索）。

        Returns:
            匹配的消息列表。
        """
        if self.conn is None:
            return []

        fts_table = "messages_fts_trigram" if use_trigram else "messages_fts"

        if session_id:
            sql = f"""
                SELECT m.* FROM messages m
                JOIN {fts_table} f ON m.id = f.rowid
                WHERE {fts_table} MATCH ? AND m.session_id = ?
                ORDER BY rank
            """
            cursor = self.conn.execute(sql, (query, session_id))
        else:
            sql = f"""
                SELECT m.* FROM messages m
                JOIN {fts_table} f ON m.id = f.rowid
                WHERE {fts_table} MATCH ?
                ORDER BY rank
            """
            cursor = self.conn.execute(sql, (query,))

        return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # 标题管理
    # ========================================================================

    def set_session_title(self, session_id: str, title: str) -> None:
        """设置会话标题。

        Args:
            session_id: 会话 ID。
            title: 标题文本。
        """
        clean_title = sanitize_title(title)
        sql = "UPDATE sessions SET title = ? WHERE id = ?"
        self._execute_write(sql, (clean_title, session_id))

    def get_session_title(self, session_id: str) -> str | None:
        """获取会话标题。

        Args:
            session_id: 会话 ID。

        Returns:
            会话标题，未设置返回 None。
        """
        session = self.get_session(session_id)
        return session.get("title") if session else None

    def resolve_session_by_title(self, title: str) -> str | None:
        """根据标题解析会话 ID。

        支持精确匹配和编号变体（如 "title #2"）。

        Args:
            title: 标题文本。

        Returns:
            匹配的会话 ID，未找到返回 None。
        """
        if self.conn is None:
            return None

        # 1. 精确匹配
        cursor = self.conn.execute(
            "SELECT id FROM sessions WHERE title = ? ORDER BY started_at DESC LIMIT 1",
            (title,),
        )
        row = cursor.fetchone()
        if row:
            return row[0]

        # 2. 搜索编号变体 "title #2", "title #3"
        clean = sanitize_title(title)
        escaped = clean.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        cursor = self.conn.execute(
            f"SELECT id FROM sessions WHERE title LIKE ? ESCAPE '\\' ORDER BY started_at DESC",
            (f"{escaped} #%",),
        )
        row = cursor.fetchone()
        if row:
            return row[0]

        return None

    def get_next_title_in_lineage(self, base_title: str) -> str:
        """生成 lineage 中的下一个标题。

        剥离现有 #N 后缀，找到最大编号，生成下一个编号标题。

        Args:
            base_title: 基础标题（可能包含 #N 后缀）。

        Returns:
            下一个编号标题。
        """
        if self.conn is None:
            return base_title

        # 剥离现有 #N 后缀
        match = re.match(r"^(.*?) #(\d+)$", base_title)
        base = match.group(1) if match else base_title

        # 查找现有编号变体
        clean = sanitize_title(base)
        escaped = clean.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        cursor = self.conn.execute(
            f"SELECT title FROM sessions WHERE title = ? OR title LIKE ? ESCAPE '\\'",
            (clean, f"{escaped} #%"),
        )
        existing = [row[0] for row in cursor.fetchall() if row[0]]

        if not existing:
            return clean

        # 找到最大编号
        max_num = 1
        for t in existing:
            m = re.match(r"^.* #(\d+)$", t)
            if m:
                max_num = max(max_num, int(m.group(1)))

        return f"{clean} #{max_num + 1}"

    def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        """列出所有历史会话。

        Args:
            limit: 最大返回数量，默认 100。

        Returns:
            会话列表，按创建时间倒序，包含 id 和 title。
        """
        if self.conn is None:
            return []

        cursor = self.conn.execute(
            "SELECT id, title, started_at, model FROM sessions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def search_sessions_by_title(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        """根据标题关键词搜索会话。

        Args:
            keyword: 搜索关键词。
            limit: 最大返回数量。

        Returns:
            匹配的会话列表。
        """
        if self.conn is None:
            return []

        cursor = self.conn.execute(
            "SELECT id, title, started_at, model FROM sessions WHERE title LIKE ? ORDER BY started_at DESC LIMIT ?",
            (f"%{keyword}%", limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # Token 计数
    # ========================================================================

    def update_token_counts(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        reasoning_tokens: int = 0,
        incremental: bool = True,
    ) -> None:
        """更新会话 token 计数。

        Args:
            session_id: 会话 ID。
            input_tokens: 输入 token 数。
            output_tokens: 输出 token 数。
            cache_read_tokens: 缓存读取 token 数。
            cache_write_tokens: 缓存写入 token 数。
            reasoning_tokens: 思考 token 数。
            incremental: True 为增量更新，False 为绝对更新。
        """
        if incremental:
            sql = """
                UPDATE sessions SET
                    input_tokens = input_tokens + ?,
                    output_tokens = output_tokens + ?,
                    cache_read_tokens = cache_read_tokens + ?,
                    cache_write_tokens = cache_write_tokens + ?,
                    reasoning_tokens = reasoning_tokens + ?
                WHERE id = ?
            """
        else:
            sql = """
                UPDATE sessions SET
                    input_tokens = ?,
                    output_tokens = ?,
                    cache_read_tokens = ?,
                    cache_write_tokens = ?,
                    reasoning_tokens = ?
                WHERE id = ?
            """
        self._execute_write(
            sql,
            (input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens, session_id),
        )

    # ========================================================================
    # 关闭
    # ========================================================================

    def close(self) -> None:
        """关闭数据库连接。

        执行最终 checkpoint 后关闭连接。
        """
        if self._closed or self.conn is None:
            return

        try:
            # 最终 checkpoint
            self.conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        except sqlite3.OperationalError:
            pass  # checkpoint 失败不影响关闭

        self.conn.close()
        self.conn = None
        self._closed = True

    def __enter__(self) -> "SessionDB":
        return self

    def __exit__(self, *args) -> None:
        self.close()


def sanitize_title(title: str) -> str:
    """清理标题：去除控制字符，折叠空白，限制长度。

    Args:
        title: 原始标题。

    Returns:
        清理后的标题（最长 100 字符）。

    Raises:
        ValueError: 标题为空或超过最大长度。
    """
    # 去除控制字符和 Unicode 格式字符（零宽字符等）
    cleaned = "".join(
        c for c in title
        if (c >= " " and c not in "\u200b\u200c\u200d\u2060\ufeff") or c in "\n\t"
    )
    # 折叠空白
    cleaned = " ".join(cleaned.split())

    if not cleaned:
        raise ValueError("Title cannot be empty")

    if len(cleaned) > MAX_TITLE_LENGTH:
        raise ValueError(f"Title too long ({len(cleaned)} chars, max {MAX_TITLE_LENGTH})")

    return cleaned
