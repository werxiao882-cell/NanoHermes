# SQLite 计数器排查流程

## 症状
`sqlite3 sessions.db "SELECT message_count, tool_call_count FROM sessions;"` 返回 0，但 JSONL 中实际有消息。

## 排查步骤

### 1. 确认是计数器问题而非数据丢失
```bash
# 统计 JSONL 实际消息数
grep -c '"role":' ~/.nanohermes/sessions/<session_id>.jsonl
# 查看角色分布
grep '"role":' ~/.nanohermes/sessions/*.jsonl | sort | uniq -c
```
如果 JSONL 有数据但 SQLite 计数器为 0 → 是计数器问题。

### 2. 检查 insert_message 是否调用 increment
```bash
grep -A 10 'def insert_message' src/session/session_db.py
# 修复后应包含: self.increment_message_count(session_id)
```

### 3. 检查 tool_call_count 更新路径
```bash
grep 'increment_tool_call_count' src/cli/event_handler.py
# 修复后应在 _on_tool_start 中看到调用
grep 'session_db.*ConversationEventHandler' src/cli/tui.py
# 实例化时应传入 session_db
```

## 关键代码路径

```
用户消息 → TUIApp._save_message_to_storage
         → session_db.insert_message(session_id, role, content)
         → [自动触发] increment_message_count(session_id)

工具调用 → ConversationEventHandler._on_tool_start(data)
         → session_db.increment_tool_call_count(session_id)
```

## 历史修复记录

| 日期 | 问题 | 修复 | 验证 |
|------|------|------|------|
| 2026-06-10 | message_count=0, tool_call_count=0 | insert_message 自动递增 + event_handler 调用 increment + tui.py 传入 session_db | 端到端 message_count=6, tool_call_count=2 |
