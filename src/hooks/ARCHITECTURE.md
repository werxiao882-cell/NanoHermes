# Hooks 模块架构

## 模块概述

提供 EventBus 责任链拦截器的具体实现。模块本身不包含事件触发机制（由 `conversation/events.py` 负责），而是提供可注册到 EventBus 的拦截器函数/类，以及从配置自动注册 hook 的加载器。所有拦截器遵循 `(data, next_fn)` 签名：调用 `next_fn()` 放行，不调用则阻断。

## 文件职责

| 文件 | 职责 |
|------|------|
| `__init__.py` | 模块导出入口，暴露 `dangerous_command_guard`、`ScriptHook`、`load_hooks_from_config` |
| `dangerous_command_guard.py` | 拦截 TOOL_START 事件，复用 terminal.py 的 DANGEROUS_PATTERNS 检测危险命令并阻断 |
| `script_hook.py` | 将外部脚本封装为拦截器，通过 subprocess 执行，stdin 传入 JSON 上下文，stdout 解析阻断信号 |
| `config_loader.py` | 从 nanohermes.json 的 hooks 配置加载并自动注册到 EventBus，支持 script 和 python 两种类型 |

## 核心数据流

### 危险命令拦截

```
ConversationLoop emit TOOL_START
  → dangerous_command_guard(data, next_fn)
      → tool_name != "terminal" → next_fn() 放行
      → 解析 tool_args 中的 command
      → 匹配 DANGEROUS_PATTERNS → return（阻断，不调用 next_fn）
      → 无匹配 → next_fn() 放行
  → observers 仍触发（阻断后观察者不受影响）
```

### 外部脚本拦截

```
EventBus emit(event_type, data)
  → ScriptHook.__call__(data, next_fn)
      → subprocess.run(script_path, stdin=JSON(data), timeout)
      → 非零退出码 / 超时 / 异常 → next_fn() 放行（故障隔离）
      → stdout 解析 JSON → {"block": true} → return 阻断
      → {"block": false} / 空输出 → next_fn() 放行
```

### 配置自动注册

```
nanohermes.json → hooks.{event_name}: [handler_cfg, ...]
  → load_hooks_from_config(config, event_bus)
      → _EVENT_TYPE_MAP 映射事件名 → EventType
      → type="script"  → ScriptHook(path, timeout)
      → type="python"  → importlib.import_module(module).function
      → event_bus.intercept(event_type, handler, priority)
```

## 关键设计决策

### 复用 DANGEROUS_PATTERNS 而非重复定义

直接从 `terminal.py` import `DANGEROUS_PATTERNS`（13 种危险命令正则模式）。单一数据源避免维护不一致；拦截器在事件层工作，terminal.py 在执行层工作，两者互补。

### ScriptHook 全面故障隔离

所有异常（超时、非零退出码、非法 JSON、文件不存在）均放行而非阻断。外部脚本不可控，失败不应阻断主流程；日志记录错误供排查。

### 配置加载器动态导入

使用 `importlib.import_module` 动态加载 Python hook，无需预注册，配置即生效。单个 hook 加载失败通过 try/except 隔离，不影响其他 hook 注册。

### 事件名映射采用 value 而非 name

`_EVENT_TYPE_MAP` 使用 `e.value`（如 `"model_request"`）而非 `e.name`，与配置文件中的小写下划线风格一致。

## 对外接口

其他模块使用的公共 API：

```python
# 函数：直接作为拦截器注册到 EventBus
dangerous_command_guard(data: dict[str, Any], next_fn) -> None

# 类：实例化后作为拦截器注册
class ScriptHook:
    def __init__(self, script_path: str, timeout: int = 30)
    def __call__(self, data: dict[str, Any], next_fn) -> None

# 函数：从配置批量注册 hook
load_hooks_from_config(config: dict[str, Any], event_bus: EventBus) -> None
```

## 依赖关系

| 类型 | 模块 | 用途 |
|------|------|------|
| Internal | `src.conversation.events` | EventBus、EventType、ChainResult |
| Internal | `src.tools.impls.terminal` | DANGEROUS_PATTERNS（危险命令正则列表） |
| External | `subprocess`（标准库） | ScriptHook 执行外部脚本 |
| External | `importlib`（标准库） | config_loader 动态导入 Python hook |
