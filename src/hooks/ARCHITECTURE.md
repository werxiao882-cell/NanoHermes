# Hooks 模块架构

## 职责

提供 EventBus 责任链拦截器的具体实现，包括：
- 危险命令拦截器（复用 terminal.py 的 DANGEROUS_PATTERNS）
- ScriptHook 包装类（外部脚本封装为拦截器）
- 配置加载器（从 settings 自动注册 hook）

## 边界

| 包含 | 不包含 |
|------|--------|
| 拦截器实现 | EventBus 核心机制（在 conversation/events.py） |
| 外部脚本封装 | 事件触发逻辑（在 conversation/loop.py） |
| 配置解析 | 观察者 handler（通过 EventBus.on() 注册） |

## 组件

```
src/hooks/
├── __init__.py              # 模块导出
├── dangerous_command_guard.py # 危险命令拦截器
├── script_hook.py           # ScriptHook 包装类
├── config_loader.py         # 配置加载器
└── ARCHITECTURE.md          # 本文档
```

## 数据流

### 危险命令拦截器

```
TOOL_START emit
  │
  ├─ interceptors chain
  │    └─ dangerous_command_guard(data, next_fn)
  │         ├─ tool_name != "terminal" → next_fn() 放行
  │         ├─ 解析 command
  │         ├─ 匹配 DANGEROUS_PATTERNS → return 阻断
  │         └─ 无匹配 → next_fn() 放行
  │
  └─ observers (仍触发)
```

### ScriptHook

```
ScriptHook(script_path, timeout)
  │
  ├─ __call__(data, next_fn)
  │    ├─ subprocess.run(script_path, stdin=JSON(data), timeout)
  │    ├─ stdout → json.loads() → {"block": true/false}
  │    ├─ block=true → return 阻断
  │    └─ block=false/超时/失败 → next_fn() 放行
  │
  └─ 故障隔离：所有异常捕获后放行
```

### 配置加载

```
nanohermes.json
  │
  ├─ hooks.<event_name>: [{type, path/module, function, priority}]
  │
  ├─ load_hooks_from_config(config, event_bus)
  │    ├─ type="script" → ScriptHook(path, timeout)
  │    ├─ type="python" → importlib.import_module(module).function
  │    └─ event_bus.intercept(event_type, handler, priority)
  │
  └─ 故障隔离：单个 hook 加载失败不影响其他
```

## 关键设计决策

### 复用 DANGEROUS_PATTERNS 而非重复定义

**选择**：直接从 terminal.py import DANGEROUS_PATTERNS

**理由**：
- 单一数据源，避免重复维护
- terminal.py 已有 13 种危险命令模式
- 拦截器在事件层工作，terminal.py 在执行层工作，两者互补

### ScriptHook 故障隔离策略

**选择**：所有异常（超时/失败/非法 JSON/文件不存在）均放行

**理由**：
- 外部脚本不可控，失败不应阻断主流程
- 拦截器链的故障隔离原则：单个失败不影响其他
- 日志记录错误，便于排查

### 配置加载器动态导入

**选择**：使用 importlib.import_module 动态加载 Python hook

**理由**：
- 无需预注册，配置即生效
- 支持任意模块的任意函数
- 加载失败不影响主流程（异常捕获）

## 依赖

- Internal: src/conversation/events.py (EventBus, EventType, ChainResult)
- Internal: src/tools/impls/terminal.py (DANGEROUS_PATTERNS)
- External: subprocess (标准库), importlib (标准库)
