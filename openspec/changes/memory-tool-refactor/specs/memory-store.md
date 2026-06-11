# Spec: MemoryStore 类

## 概述

`MemoryStore` 是 NanoHermes 记忆系统的唯一数据源。管理两个目标文件（MEMORY.md 和 USER.md），提供有界、并发安全、漂移检测的记忆管理。

## 类签名

```python
class MemoryStore:
    def __init__(
        self,
        memory_dir: Path,
        memory_char_limit: int = 2200,
        user_char_limit: int = 1375,
    )
```

## 公共 API

### load_from_disk()

从磁盘加载条目，捕获系统提示冻结快照。

```python
def load_from_disk(self) -> None
```

- 读取 MEMORY.md 和 USER.md
- 按 `\n§\n` 分割为条目列表
- strip 每个条目，过滤空条目
- 去重（`dict.fromkeys` 保留首次出现）
- 捕获冻结快照到 `_system_prompt_snapshot`

### add(target, content) → dict

追加新条目。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| target | str | 是 | `"memory"` 或 `"user"` |
| content | str | 是 | 条目内容 |

**成功响应：**
```json
{
  "success": true,
  "target": "memory",
  "entries": ["Entry 1", "Entry 2"],
  "usage": "45% — 990/2,200 chars",
  "entry_count": 2,
  "message": "Entry added."
}
```

**错误场景：**

| 场景 | error |
|------|-------|
| 内容为空 | `"Content cannot be empty."` |
| 内容扫描失败 | `"Blocked: content matches threat pattern 'xxx'."` |
| 外部漂移 | `"Refusing to write MEMORY.md: file on disk has content that wouldn't round-trip..."` |
| 完全重复 | `"Entry already exists (no duplicate added)."` (success=true) |
| 超过字符限制 | `"Memory at 2100/2200 chars. Adding this entry (200 chars) would exceed the limit."` |

### replace(target, old_text, new_content) → dict

查找包含 `old_text` 子串的条目，替换为 `new_content`。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| target | str | 是 | `"memory"` 或 `"user"` |
| old_text | str | 是 | 短唯一子串 |
| new_content | str | 是 | 新内容 |

**额外错误场景：**

| 场景 | error |
|------|-------|
| old_text 为空 | `"old_text cannot be empty."` |
| new_content 为空 | `"new_content cannot be empty. Use 'remove' to delete entries."` |
| 无匹配 | `"No entry matched 'xxx'."` |
| 多个不同条目匹配 | `"Multiple entries matched 'xxx'. Be more specific."` + matches 列表 |
| 替换后超限 | `"Replacement would put memory at xxx/2200 chars."` |

### remove(target, old_text) → dict

删除包含 `old_text` 子串的条目。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| target | str | 是 | `"memory"` 或 `"user"` |
| old_text | str | 是 | 短唯一子串 |

### format_for_system_prompt(target) → str | None

返回冻结快照用于系统提示注入。

- 返回格式化的文本块（含标题和使用量指示器）
- 无条目时返回 `None`

**输出示例：**
```
══════════════════════════════════════════
MEMORY (your personal notes) [45% — 990/2,200 chars]
══════════════════════════════════════════
User prefers dark mode
§
Project uses Python 3.11
```

## 内部方法

| 方法 | 说明 |
|------|------|
| `_file_lock(path)` | 跨平台排他文件锁（.lock 文件） |
| `_read_file(path)` | 读取并按 `\n§\n` 解析条目列表 |
| `_write_file(path, entries)` | 原子写入（tempfile + os.replace） |
| `_reload_target(target)` | 锁内重新加载磁盘状态（检测漂移） |
| `_detect_external_drift(target)` | 检测外部修改，创建 .bak 备份 |
| `_scan_memory_content(content)` | 威胁模式 + 不可见字符扫描 |
| `_render_block(target, entries)` | 渲染系统提示块（含标题和使用量） |
| `_entries_for(target)` | 获取目标条目列表 |
| `_set_entries(target, entries)` | 设置目标条目列表 |
| `_char_count(target)` | 计算当前字符数 |
| `_char_limit(target)` | 获取目标字符限制 |
| `_success_response(target, message)` | 构建统一的成功响应 |

## 常量

```python
ENTRY_DELIMITER = "\n§\n"
MEMORY_CHAR_LIMIT = 2200
USER_CHAR_LIMIT = 1375
```

## 线程安全

- 所有写操作（add/replace/remove）在文件锁内执行
- 锁内重新加载磁盘状态，捕获并行会话的写入
- 读操作（format_for_system_prompt）无需锁（读取冻结快照）

## 与现有系统的关系

| 组件 | 重构前 | 重构后 |
|------|--------|--------|
| `memory_tool.py` | 直接读写文件 | 委托 `MemoryStore` |
| `FileMemoryProvider` | 自有读写逻辑 | 委托 `MemoryStore` |
| `PromptAssembler` | 独立读取文件 | 读取 `MemoryStore` 冻结快照 |
| `MemoryManager` | 编排多 provider | 不变 |
| `MemoryEventHandler` | 订阅事件调用 Manager | 不变 |
