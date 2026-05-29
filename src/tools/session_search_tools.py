"""Session Search 工具：历史会话搜索。

基于 SQLite SessionDB 实现 FTS5 全文搜索。
支持三种模式：
1. DISCOVERY - 传入 query 进行搜索
2. SCROLL - 传入 session_id + around_message_id 滚动查看
3. BROWSE - 不传参数查看最近会话
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.tools.registry import register_tool

logger = logging.getLogger(__name__)


def _get_session_db():
    """获取 SessionDB 实例。"""
    try:
        from src.session.session_db import SessionDB
        
        # 使用默认路径
        db_path = Path.home() / ".nanohermes" / "sessions.db"
        if db_path.exists():
            return SessionDB(db_path)
        return None
    except Exception as e:
        logger.debug(f"SessionDB 不可用: {e}")
        return None


def session_search(
    query: str = "",
    session_id: str = "",
    around_message_id: int = None,
    limit: int = 10,
    role_filter: str = "",
    task_id: str = None,
) -> str:
    """搜索历史会话。
    
    支持三种调用方式：
    - 搜索：传入 query
    - 滚动：传入 session_id + around_message_id
    - 浏览：不传参数，返回最近会话
    """
    db = _get_session_db()
    if db is None:
        return json.dumps({
            "status": "error",
            "message": "Session database not found. No session history available yet."
        }, ensure_ascii=False)

    try:
        # SCROLL 模式：滚动查看特定会话
        if session_id and around_message_id is not None:
            return _scroll(db, session_id, around_message_id, limit)
        
        # BROWSE 模式：查看最近会话
        if not query or not query.strip():
            return _browse_recent(db, limit)
        
        # DISCOVERY 模式：FTS5 搜索
        return _search_discovery(db, query.strip(), limit, role_filter)
        
    except Exception as e:
        logger.error(f"Session search error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Search failed: {str(e)}"
        }, ensure_ascii=False)


def _scroll(db, session_id: str, around_message_id: int, window: int) -> str:
    """滚动查看会话消息窗口。"""
    messages = db.get_messages(session_id)
    if not messages:
        return json.dumps({
            "status": "error",
            "message": f"Session {session_id} not found or has no messages."
        }, ensure_ascii=False)
    
    # 找到锚点消息的索引
    anchor_idx = None
    for i, msg in enumerate(messages):
        if msg.get("message_id") == str(around_message_id) or msg.get("rowid") == around_message_id:
            anchor_idx = i
            break
    
    if anchor_idx is None:
        return json.dumps({
            "status": "error",
            "message": f"Message ID {around_message_id} not found in session."
        }, ensure_ascii=False)
    
    # 获取窗口
    start = max(0, anchor_idx - window)
    end = min(len(messages), anchor_idx + window + 1)
    window_messages = messages[start:end]
    
    return json.dumps({
        "status": "success",
        "mode": "scroll",
        "session_id": session_id,
        "window_messages": [
            {
                "id": msg.get("message_id"),
                "role": msg.get("role"),
                "content": msg.get("content", "")[:500],
                "timestamp": msg.get("timestamp"),
            }
            for msg in window_messages
        ],
        "count": len(window_messages),
        "message": f"Showing {len(window_messages)} messages around anchor. Re-anchor on first/last message ID to scroll."
    }, ensure_ascii=False)


def _browse_recent(db, limit: int) -> str:
    """浏览最近会话。"""
    try:
        # 获取所有会话
        cursor = db.conn.execute(
            "SELECT * FROM sessions WHERE ended_at IS NOT NULL ORDER BY created_at DESC LIMIT ?",
            (limit + 5,)
        )
        sessions = [dict(row) for row in cursor.fetchall()]
        
        results = []
        for session in sessions:
            sid = session.get("session_id")
            # 获取消息预览
            messages = db.get_messages(sid)
            preview = ""
            if messages:
                # 取前几条消息作为预览
                first_msgs = messages[:3]
                preview = " | ".join([
                    f"{m.get('role')}: {(m.get('content') or '')[:50]}"
                    for m in first_msgs if m.get('content')
                ])
            
            results.append({
                "session_id": sid,
                "title": session.get("title") or "Untitled",
                "created_at": session.get("created_at"),
                "ended_at": session.get("ended_at"),
                "message_count": len(messages),
                "preview": preview[:200],
            })
            
            if len(results) >= limit:
                break
        
        return json.dumps({
            "status": "success",
            "mode": "browse",
            "results": results,
            "count": len(results),
            "message": f"Showing {len(results)} most recent sessions. Pass a query= to search, or session_id+around_message_id to scroll."
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browse error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Failed to list recent sessions: {str(e)}"
        }, ensure_ascii=False)


def _search_discovery(db, query: str, limit: int, role_filter: str = "") -> str:
    """FTS5 搜索发现。"""
    try:
        # 尝试使用 FTS5 搜索
        use_trigram = False
        messages = db.search_messages(query, use_trigram=use_trigram)
        
        if not messages:
            # 回退到 LIKE 搜索
            cursor = db.conn.execute(
                "SELECT * FROM messages WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit * 3)
            )
            messages = [dict(row) for row in cursor.fetchall()]
        
        # 按 role 过滤
        if role_filter:
            roles = [r.strip().lower() for r in role_filter.split(",")]
            messages = [m for m in messages if m.get("role", "").lower() in roles]
        
        # 按 session 分组
        session_results = {}
        for msg in messages:
            sid = msg.get("session_id")
            if sid not in session_results:
                session_info = db.get_session(sid)
                session_results[sid] = {
                    "session_id": sid,
                    "title": session_info.get("title") if session_info else "Untitled",
                    "created_at": session_info.get("created_at") if session_info else None,
                    "matches": [],
                }
            
            session_results[sid]["matches"].append({
                "id": msg.get("message_id"),
                "role": msg.get("role"),
                "content": msg.get("content", "")[:300],
                "timestamp": msg.get("timestamp"),
            })
        
        # 限制结果数
        results = list(session_results.values())[:limit]
        total_matches = sum(len(r["matches"]) for r in results)
        
        return json.dumps({
            "status": "success",
            "mode": "discover",
            "query": query,
            "results": results,
            "count": len(results),
            "total_matches": total_matches,
            "message": f"Found {total_matches} matches across {len(results)} sessions."
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Search failed: {str(e)}"
        }, ensure_ascii=False)


def check_session_search_requirements() -> bool:
    """检查是否满足 session_search 的要求。"""
    try:
        db_path = Path.home() / ".nanohermes" / "sessions.db"
        return db_path.exists()
    except Exception:
        return False


register_tool(
    name="session_search",
    toolset="session_search",
    schema={
        "name": "session_search",
        "description": (
            "搜索历史会话。支持三种模式：\n"
            "1. DISCOVERY - 传入 query 进行全文搜索\n"
            "2. SCROLL - 传入 session_id + around_message_id 滚动查看\n"
            "3. BROWSE - 不传参数查看最近会话\n\n"
            "基于 SQLite FTS5 索引，零 LLM 成本。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词（DISCOVERY 模式）。",
                },
                "session_id": {
                    "type": "string",
                    "description": "指定会话 ID（SCROLL 模式）。",
                },
                "around_message_id": {
                    "type": "integer",
                    "description": "锚点消息 ID（SCROLL 模式）。",
                },
                "limit": {
                    "type": "integer",
                    "description": "最大结果数（默认 10）。",
                },
                "role_filter": {
                    "type": "string",
                    "description": "按角色过滤，如 'user,assistant'。",
                },
            },
            "required": [],
        },
    },
    handler=session_search,
    check_fn=check_session_search_requirements,
    description="历史会话搜索",
)
