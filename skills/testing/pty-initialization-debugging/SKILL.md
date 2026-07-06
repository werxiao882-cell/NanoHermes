---
name: pty-initialization-debugging
description: "Debug initialization crashes in PTY-interactive Python applications — sentinel objects, attribute ordering, __init__ sequencing"
version: 1.0.0
platforms: [linux, macos, wsl]
metadata:
  hermes:
    tags: [debugging, pty, python, initialization, tui]
    related_skills: [nanohermes-pty-testing]
---

# PTY 初始化崩溃调试

## 触发条件

PTY 启动 Python 应用时立即崩溃，报错 `AttributeError: object has no attribute` 或 `NameError: name 'X' is not defined`，但 `python -c "import module"` 正常。

## 根因模式

### 模式 1: 哨兵对象缺失 (`NameError`)

```python
# __init__ 签名中使用了 _UNSET 哨兵，但从未定义
def __init__(self, session_db=_UNSET):  # NameError: _UNSET is not defined
```

**修复**：在类定义前添加 `_UNSET = object()`

### 模式 2: 属性使用顺序错误 (`AttributeError`)

```python
def __init__(self):
    self.status_bar = StatusBar(model=self.model)  # AttributeError: no 'model'
    # ... 50 lines later ...
    self.model = config.model.name  # model 赋值在 status_bar 之后
```

**修复**：将依赖 `self.model` 的对象创建延迟到 `self.model` 赋值之后。

### 模式 3: 条件分支跳过初始化

```python
def __init__(self):
    if some_flag:
        self.api_key = load_key()
    # ... 后面使用 self.api_key 但不检查 some_flag
```

**修复**：确保所有分支都初始化了后续需要的属性，或在使用前加防御性检查。

## 调试步骤

1. **确认是初始化崩溃还是运行时崩溃**：
   - 崩溃发生在 `__init__` 或模块导入期 → 初始化问题
   - 崩溃发生在用户交互后 → 运行时问题

2. **用 `python -B` 排除缓存**：
   ```bash
   python -B -m src.main
   ```
   如果 `-B` 能跑通但正常不行 → `__pycache__` 过期

3. **定位崩溃点**：
   ```bash
   python -c "from src.module import Class; Class()"
   ```
   逐步缩小到具体类和行。

4. **检查 `__init__` 中属性赋值顺序**：
   - 从上到下读 `__init__`，标记每个 `self.xxx = ...`
   - 标记每个 `self.yyy` 的使用点（包括方法调用、参数传递）
   - 找「使用前未赋值」的模式

## 预防措施

- **哨兵对象集中定义**：在模块顶部统一定义所有哨兵（如 `_UNSET = object()`）
- **依赖分组**：将 `__init__` 按依赖关系分组，用注释标注（如 `# ── 步骤 7: 配置加载 ──`）
- **类型检查**：启用 pyright/mypy 可提前发现 `Optional` 类型的属性访问问题
- **单元测试**：对 `__init__` 写简单的实例化测试（`assert MyClass()` 不抛异常）

## 与单元测试的关系

PTY 测试比单元测试更早暴露初始化顺序 bug，因为：
- 单元测试常传 mock 参数跳过部分初始化路径
- PTY 测试走完整初始化链路（配置→凭证→模型→工具→存储→提示词→TUI）
- **建议**：在 PTY 测试前，先跑 `python -c "from src.cli.tui import TUIApp; TUIApp()"` 做冒烟测试
