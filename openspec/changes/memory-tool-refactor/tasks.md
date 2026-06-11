# Tasks: Memory Tool 重构

## 1. MemoryStore 核心实现

- [ ] 1.1 创建 `src/memory/memory_store.py`，定义 `MemoryStore` 类和常量（ENTRY_DELIMITER, 威胁模式, 不可见字符）
- [ ] 1.2 实现 `_read_file()` — 按 `\n§\n` 分割、strip、过滤空条目
- [ ] 1.3 实现 `_write_file()` — 原子写入（tempfile + os.replace + fsync）
- [ ] 1.4 实现 `_file_lock()` — 跨平台文件锁（fcntl / msvcrt / 降级无锁）
- [ ] 1.5 实现 `load_from_disk()` — 加载条目 + 去重 + 捕获冻结快照
- [ ] 1.6 实现 `_scan_memory_content()` — 威胁模式 + 不可见字符扫描
- [ ] 1.7 实现 `_detect_external_drift()` — 往返检测 + 条目大小溢出检测 + .bak 备份
- [ ] 1.8 实现 `add()` — 内容扫描 + 锁 + 漂移检测 + 去重 + 字符限制
- [ ] 1.9 实现 `replace()` — 子串匹配 + 歧义检测 + 字符限制
- [ ] 1.10 实现 `remove()` — 子串匹配 + 歧义检测
- [ ] 1.11 实现 `format_for_system_prompt()` — 返回冻结快照（含标题和使用量）
- [ ] 1.12 实现辅助方法 — `_entries_for`, `_set_entries`, `_char_count`, `_char_limit`, `_success_response`, `_render_block`

## 2. 集成：FileMemoryProvider

- [ ] 2.1 重构 `src/memory/file_provider.py` — 构造函数接收 `MemoryStore` 实例
- [ ] 2.2 `initialize()` 委托给 `MemoryStore.load_from_disk()`
- [ ] 2.3 `system_prompt_block()` 返回冻结快照（不再每轮重读文件）
- [ ] 2.4 `prefetch()` 返回冻结快照
- [ ] 2.5 `handle_tool_call()` 委托给 `MemoryStore.add/replace/remove`
- [ ] 2.6 移除自有的 `_add_entry`, `_replace_entry`, `_remove_entry`, `_atomic_write`

## 3. 集成：memory_tool.py

- [ ] 3.1 重构 `src/tools/impls/memory_tool.py` — 使用全局 `MemoryStore` 单例
- [ ] 3.2 `memory()` 函数委托给 `MemoryStore.add/replace/remove`
- [ ] 3.3 移除自有的 `_add_entry`, `_replace_entry`, `_remove_entry`, `_view_memory`
- [ ] 3.4 确保 `memory_tool.py` 和 `FileMemoryProvider` 共享同一个 `MemoryStore` 实例

## 4. 集成：PromptAssembler

- [ ] 4.1 修改 `src/conversation/assembler.py` — `build_memory_context()` 优先从 `MemoryStore` 读取冻结快照
- [ ] 4.2 修改 `build_user_profile()` 优先从 `MemoryStore` 读取冻结快照
- [ ] 4.3 保留直接读取文件作为降级路径（MemoryStore 未初始化时）

## 5. 模块导出

- [ ] 5.1 更新 `src/memory/__init__.py` — 导出 `MemoryStore`

## 6. 测试

- [ ] 6.1 创建 `tests/memory/test_memory_store.py`
- [ ] 6.2 测试 `load_from_disk()` — 正常加载、空文件、去重
- [ ] 6.3 测试 `add()` — 成功、空内容、重复、超限、威胁内容
- [ ] 6.4 测试 `replace()` — 成功、无匹配、歧义、超限
- [ ] 6.5 测试 `remove()` — 成功、无匹配、歧义
- [ ] 6.6 测试文件锁 — 并发写入不丢失数据
- [ ] 6.7 测试漂移检测 — 外部修改后拒绝写入、创建备份
- [ ] 6.8 测试内容扫描 — 注入模式、不可见字符
- [ ] 6.9 测试冻结快照 — 会话内写入不影响 `format_for_system_prompt()` 输出

## 7. 验证

- [ ] 7.1 `pytest tests/memory/test_memory_store.py -v` 全部通过
- [ ] 7.2 `pytest tests/memory/ -v` 确认不影响现有记忆测试
- [ ] 7.3 `pytest tests/tools/test_memory_tool.py -v` 确认工具测试通过
- [ ] 7.4 `pytest tests/cli/ -v` 确认 TUI 集成不受影响
- [ ] 7.5 手动验证：启动 NanoHermes，调用 memory 工具添加/替换/删除条目
