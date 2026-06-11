# Design: Memory Tool 重构

## 1. 架构总览

### 重构前：三条并行路径

```
                    ┌─────────────────────────────────┐
                    │         MEMORY.md / USER.md      │
                    └───┬──────────┬──────────┬────────┘
                        │          │          │
                   ┌────▼───┐ ┌───▼────┐ ┌───▼──────────┐
                   │memory_ │ │FileMem │ │PromptAssembler│
                   │tool.py │ │Provider│ │(独立读取)     │
                   └────────┘ └────────┘ └──────────────┘
                   无锁/无边界  原子写入   每轮重读文件
                   无漂移检测   无边界     无冻结快照
```

### 重构后：MemoryStore 单一数据源

```
                    ┌─────────────────────────────────┐
                    │          MemoryStore              │
                    │  ┌───────────┐ ┌──────────────┐  │
                    │  │ live state│ │frozen snapshot│  │
                    │  │(实时状态) │ │(冻结快照)    │  │
                    │  └─────┬─────┘ └──────┬───────┘  │
                    │        │              │          │
                    │  ┌─────▼──────────────▼───────┐  │
                    │  │    MEMORY.md / USER.md      │  │
                    │  │    (文件锁 + 原子写入)      │  │
                    │  └────────────────────────────┘  │
                    └──┬──────────┬──────────┬─────────┘
                       │          │          │
                  ┌────▼───┐ ┌───▼────┐ ┌───▼──────────┐
                  │memory_ │ │FileMem │ │PromptAssembler│
                  │tool.py │ │Provider│ │(读冻结快照)   │
                  └────────┘ └────────┘ └──────────────┘
                  委托调用    委托调用    不再直接读文件
```

## 2. MemoryStore 设计

### 2.1 双状态模型

```python
class MemoryStore:
    def __init__(self, memory_dir, memory_char_limit=2200, user_char_limit=1375):
        # 实时状态：工具响应反映此状态
        self.memory_entries: list[str] = []
        self.user_entries: list[str] = []

        # 冻结快照：系统提示使用，load_from_disk() 时捕获，会话内不变
        self._system_prompt_snapshot: dict[str, str] = {"memory": "", "user": ""}
```

**为什么需要双状态？**

- Anthropic Claude 的 prompt caching 要求系统提示前缀稳定
- 如果每轮对话都重新读取记忆文件注入系统提示，前缀缓存会失效
- 冻结快照在会话启动时捕获一次，之后不再变化
- 工具调用（add/replace/remove）修改实时状态并持久化到磁盘
- 下次会话启动时，快照会刷新为最新状态

### 2.2 § 分隔符

```python
ENTRY_DELIMITER = "\n§\n"
```

**为什么不用 Markdown 列表？**

| 格式 | 多行条目 | 解析复杂度 | 替换准确性 |
|------|---------|-----------|-----------|
| `- entry` | 需要检测缩进 | 高 | 低（行匹配易误删） |
| `\n§\n` | 天然支持 | 低（split 即可） | 高（子串匹配） |

### 2.3 文件锁

```python
@staticmethod
@contextmanager
def _file_lock(path: Path):
    """跨平台排他文件锁。"""
    lock_path = path.with_suffix(path.suffix + ".lock")
    # Unix: fcntl.flock(fd, LOCK_EX)
    # Windows: msvcrt.locking(fd, LK_LOCK, 1)
    # 两者都不可用: 降级为无锁（单用户场景可接受）
```

**为什么用 .lock 文件而非锁定原文件？**

- 记忆文件使用原子写入（temp + os.replace）
- 如果锁定原文件，os.replace 会被阻塞
- 单独的 .lock 文件不影响原子写入流程

### 2.4 原子写入

```python
@staticmethod
def _write_file(path: Path, entries: list[str]) -> None:
    content = ENTRY_DELIMITER.join(entries) if entries else ""
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)  # 原子替换
    except BaseException:
        os.unlink(tmp_path)
        raise
```

**为什么不用 open("w")？**

- `open("w")` 会先截断文件再写入
- 如果写入中途崩溃，文件内容丢失
- 原子写入保证读者始终看到完整的旧文件或新文件

### 2.5 漂移检测

```python
def _detect_external_drift(self, target: str) -> Optional[str]:
    """检测外部修改并拒绝覆盖。"""
    # 信号 1: 往返不匹配 — 解析后重新序列化 ≠ 原文件
    # 信号 2: 条目大小溢出 — 单个条目 > 整个文件的字符限制
    # 检测到漂移时：创建 .bak.<timestamp> 备份，返回备份路径
```

**什么场景会触发漂移？**

- 用户手动编辑 MEMORY.md
- patch 工具修改了记忆文件
- 并行会话（另一个 NanoHermes 实例）写入了记忆
- shell 命令 append 到记忆文件

### 2.6 内容扫描

```python
_MEMORY_THREAT_PATTERNS = [
    (r'ignore\s+(?:\w+\s+)*(previous|all|above|prior)\s+(?:\w+\s+)*instructions', "prompt_injection"),
    (r'you\s+are\s+(?:\w+\s+)*now\s+(?:a|an|the)\s+', "role_hijack"),
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD)', "exfil_curl"),
    # ... 更多模式
]

_INVISIBLE_CHARS = {'\u200b', '\u200c', '\u200d', '\u2060', ...}
```

**为什么需要内容扫描？**

- 记忆内容会注入到系统提示中
- 如果 LLM 被诱导写入 `ignore previous instructions`，下次会话会被注入攻击
- 不可见 Unicode 字符可用于隐藏恶意指令

## 3. 集成路径

### 3.1 FileMemoryProvider 重构

```python
class FileMemoryProvider(MemoryProvider):
    def __init__(self, hermes_home: str):
        self._store = MemoryStore(Path(hermes_home) / "memory")

    def initialize(self, session_id: str, **kwargs) -> None:
        self._store.load_from_disk()

    def system_prompt_block(self) -> str:
        # 返回冻结快照，不再每轮重读文件
        parts = []
        for target in ("memory", "user"):
            block = self._store.format_for_system_prompt(target)
            if block:
                parts.append(block)
        return "\n\n".join(parts)

    def handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str:
        # 委托给 MemoryStore
        action = args.get("action", "")
        target = args.get("target", "memory")
        if action == "add":
            return json.dumps(self._store.add(target, args.get("content", "")))
        elif action == "replace":
            return json.dumps(self._store.replace(target, args.get("old_text", ""), args.get("content", "")))
        elif action == "remove":
            return json.dumps(self._store.remove(target, args.get("old_text", "")))
```

### 3.2 memory_tool.py 重构

```python
# memory_tool.py 不再直接操作文件
# 而是通过全局 MemoryStore 单例委托

_store: MemoryStore | None = None

def get_memory_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore(Path.home() / ".nanohermes" / "memory")
        _store.load_from_disk()
    return _store

def memory(action: str, target: str = "memory", content: str = "", old_text: str = "", **kwargs) -> str:
    store = get_memory_store()
    if action == "add":
        return json.dumps(store.add(target, content))
    elif action == "replace":
        return json.dumps(store.replace(target, old_text, content))
    elif action == "remove":
        return json.dumps(store.remove(target, old_text))
```

**单例 vs 注入？**

- `memory_tool.py` 通过全局单例访问 MemoryStore（工具注册时无法注入实例）
- `FileMemoryProvider` 通过构造函数注入 MemoryStore（由 TUIApp 创建并传递）
- 两者指向同一个 MemoryStore 实例（通过模块级缓存保证）

### 3.3 PromptAssembler 修改

```python
# 重构前：PromptAssembler 独立读取 MEMORY.md/USER.md
def _read_memory_file(self) -> str:
    # 直接读取 ~/.nanohermes/memory/MEMORY.md
    ...

# 重构后：通过 MemoryStore 获取冻结快照
def build_memory_context(self, memory_data=None) -> str:
    if self._memory_store:
        block = self._memory_store.format_for_system_prompt("memory")
        return block or ""
    # 降级：直接读取文件（向后兼容）
    ...
```

## 4. 数据流

### 会话启动

```
TUIApp.__init__()
  ├─ MemoryStore(memory_dir)
  ├─ MemoryStore.load_from_disk()
  │   ├─ 读取 MEMORY.md / USER.md
  │   ├─ 解析 § 分隔的条目
  │   ├─ 去重
  │   └─ 捕获冻结快照 → _system_prompt_snapshot
  ├─ FileMemoryProvider(store=memory_store)
  ├─ MemoryManager.add_provider(file_provider)
  └─ PromptAssembler.set_memory_store(memory_store)
```

### 工具调用

```
LLM → memory(action="add", target="memory", content="...")
  └─ memory_tool.py → MemoryStore.add()
      ├─ 内容扫描（威胁检测）
      ├─ 获取文件锁
      ├─ 重新加载磁盘状态（检测漂移 + 并行会话写入）
      ├─ 检查重复
      ├─ 检查字符限制
      ├─ 追加条目到 memory_entries
      ├─ 原子写入 MEMORY.md
      ├─ 释放锁
      └─ 返回成功响应（含使用量统计）
```

### 系统提示注入

```
conversation loop 每轮开始前
  └─ MemoryEventHandler._on_iteration_start()
      └─ MemoryManager.prefetch_all()
          └─ FileMemoryProvider.prefetch()
              └─ MemoryStore.format_for_system_prompt("memory")
                  └─ 返回冻结快照（不受会话内写入影响）
```

## 5. 测试策略

| 测试类别 | 覆盖内容 |
|----------|---------|
| 单元测试 | MemoryStore 每个公共方法 |
| 并发测试 | 多进程同时写入，验证锁机制 |
| 漂移测试 | 外部修改后拒绝写入、创建备份 |
| 集成测试 | FileMemoryProvider + memory_tool 端到端 |
| 快照测试 | 会话内写入不影响冻结快照 |
