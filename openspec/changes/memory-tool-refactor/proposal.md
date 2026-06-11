# Proposal: Memory Tool 重构

## Why

当前 NanoHermes 的记忆系统存在 **三条并行的读写路径**，各自独立操作 MEMORY.md/USER.md，数据一致性无法保证：

| 路径 | 文件 | 问题 |
|------|------|------|
| LLM 工具调用 | `src/tools/impls/memory_tool.py` | 无锁、无边界、无漂移检测、无内容扫描 |
| MemoryManager 路由 | `src/memory/file_provider.py` | 原子写入但无边界、无漂移检测 |
| 系统提示组装 | `src/conversation/assembler.py` | 独立读取文件，第三个读者 |

具体问题：

1. **无边界控制** — 记忆文件可无限增长，占满 LLM 上下文窗口
2. **无并发保护** — 多会话同时写入可能数据丢失
3. **无漂移检测** — 外部修改（patch、手动编辑、并行会话）被静默覆盖
4. **无内容扫描** — 注入攻击可污染系统提示
5. **格式脆弱** — Markdown 列表格式，多行条目解析和替换容易出错
6. **无冻结快照** — 每轮重读文件，前缀缓存失效

参考 Hermes Agent `memory_tool.py`（734 行）的 `MemoryStore` 类。

## What Changes

### 核心：MemoryStore 作为唯一数据源

```
重构前（三条并行路径）：
  memory_tool.py ──→ MEMORY.md ←── FileMemoryProvider
                      ↑
                  PromptAssembler（独立读取）

重构后（单一数据源）：
  memory_tool.py ──→ MemoryStore ←── FileMemoryProvider
                      ↓
                  MEMORY.md / USER.md（持久化）
                      ↓
                  PromptAssembler（读冻结快照）
```

### MemoryStore 核心特性

- **§ 分隔符** — `\n§\n` 分隔条目，支持多行内容
- **字符数限制** — memory 2200 chars, user 1375 chars
- **冻结快照** — 系统提示使用加载时快照，工具响应反映实时状态
- **文件锁** — 跨平台（fcntl / msvcrt / 降级无锁）
- **原子写入** — tempfile + os.replace()
- **漂移检测** — 检测外部修改并拒绝覆盖，创建 .bak 备份
- **内容扫描** — 注入/渗出模式检测（10+ 威胁模式）
- **去重** — 拒绝完全重复的条目
- **使用量追踪** — 返回 `pct% — current/limit chars`

### 文件变更

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/memory/memory_store.py` | 新增 | MemoryStore 类 |
| `src/memory/file_provider.py` | 重构 | 委托 MemoryStore，移除自有读写逻辑 |
| `src/tools/impls/memory_tool.py` | 重构 | 委托 MemoryStore，移除自有读写逻辑 |
| `src/conversation/assembler.py` | 修改 | 记忆读取改为从 MemoryStore 获取冻结快照 |
| `src/memory/__init__.py` | 修改 | 导出 MemoryStore |
| `tests/memory/test_memory_store.py` | 新增 | 单元测试 |

## Impact

- **数据一致性** — 三条路径统一为一个数据源
- **前缀缓存稳定** — 冻结快照确保系统提示不变
- **安全性** — 内容扫描阻止注入攻击，漂移检测防止数据丢失
- **可观测性** — 使用量追踪让 LLM 知道剩余空间
