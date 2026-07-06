# SQLite 计数器调试指南

## 问题

`sessions` 表中 `message_count`、`tool_call_count`、`api_call_count` 始终为 0。

## 调试路径

```sql
-- 验证问题
sqlite3 ~/.nanohermes/sessions.db "SELECT id, title, message_count, tool_call_count FROM sessions;"
-- 结果: message_count=0, tool_call_count=0 (但 JSONL 中有 138 条消息)
```

### 第一步：搜索调用点

```bash
# 查找 increment 方法定义
grep -rn "increment_message_count\|increment_tool_call_count" src/
# 结果: 只在 session_db.py 中定义，从未被调用
```

### 第二步：查找消息插入点

```bash
grep -rn "insert_message\|append_message" src/
# 结果: tui.py:_save_message_to_storage, event_handler.py:_save_to_jsonl
```

### 第三步：确认缺失调用

检查 `session_db.py:insert_message` 的返回值 — 成功插入后没有递增计数器。

## 修复方案

### 1. session_db.py: insert_message 自动递增

```python
cursor = self._execute_write(sql, (...))
if role in ("user", "assistant", "system"):
    self.increment_message_count(session_id)
return cursor.lastrowid
```

### 2. event_handler.py: _on_tool_start 递增工具计数

添加 `session_db` 参数到 `ConversationEventHandler.__init__`，在 `_on_tool_start` 中调用 `increment_tool_call_count`。

### 3. tui.py: 传入 session_db

实例化 `ConversationEventHandler` 时传入 `session_db=self.session_db`。

## 验证

```bash
sqlite3 ~/.nanohermes/sessions.db "SELECT message_count, tool_call_count FROM sessions;"
# 期望: message_count=6, tool_call_count=2
```

## 通用模式

当发现"计数器/统计值始终为 0"类 bug 时：
1. 搜索 increment/update 方法定义
2. grep 搜索调用点 — 如果只在定义处找到，说明从未被调用
3. 找到最接近的调用点（数据写入处），添加自动递增
