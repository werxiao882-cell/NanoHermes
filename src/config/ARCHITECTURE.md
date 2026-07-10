# Config 模块架构

## 模块概述

NanoHermes 的统一配置管理模块。从多种来源（JSON 配置文件、.env 环境变量、显式参数）加载配置，通过优先级合并生成完整的 `Config` 对象。采用 Pydantic 模型在入口处快速验证，确保后续模块接收到类型安全的配置。

## 文件职责

```
src/config/
├── __init__.py      # 模块入口，re-export 所有公开符号
├── models.py        # Pydantic 数据模型定义（7 个配置段 + 根 Config）
├── loader.py        # 配置加载链：文件读取 → 深度合并 → 凭证解析 → 验证
└── ARCHITECTURE.md  # 本文件
```

- **models.py** — 定义所有配置段的 Pydantic 模型，提供类型验证和默认值。
- **loader.py** — 实现配置文件加载、多层优先级合并、环境变量凭证解析和 API Key/URL 查找。

## 数据模型

| 模型 | 说明 |
|------|------|
| `Config` | 根配置对象，聚合所有配置段 |
| `ModelConfig` | 主模型（provider, name, context_length） |
| `ProviderConfig` | 单个提供商（base_url, api_key_env） |
| `McpConfig` / `McpServerConfig` | MCP 服务器列表及单个服务器配置 |
| `TuiConfig` | TUI 界面（typing_speed, show_tool_panel, tool_panel_position） |
| `AuxiliaryConfig` | 辅助 LLM（provider, model, max_tokens, temperature） |
| `ToolsConfig` | 工具 DFX 配置（max_tool_concurrency, tool_result_budget） |
| `BackgroundTasksConfig` | 后台任务总控（enabled, max_concurrent, task_timeout_seconds） |
| `MemoryFlushConfig` | 记忆刷写子任务（enabled, min_messages） |
| `SkillReviewConfig` | 技能审查子任务（enabled, min_turns, min_interval_minutes, curator_enabled） |

## 核心数据流

```
load_config(model=, provider=, api_key=, base_url=, config_file=)
    │
    ├── load_json_file(GLOBAL_CONFIG)      → global_data
    ├── load_json_file(PROJECT_CONFIG)     → project_data
    ├── load_env_defaults()                → env_data    (.env → 已知变量自动检测)
    │
    ├── deep_merge(env_data, global_data)  → merged      (全局覆盖 env)
    ├── deep_merge(merged, project_data)   → merged      (项目覆盖全局)
    │
    ├── 注入显式参数 (model/provider/api_key/base_url)   (最高优先级)
    │
    ├── resolve_env_credentials(merged)    → merged      (*_env 字段 → 环境变量值)
    │
    ├── Config.from_dict(merged)           → Config      (Pydantic 验证，快速失败)
    │
    └── _resolve_api_key(config)           → 验证凭证可达性
```

API Key 解析优先级：`__explicit_api_key__` → provider 的 `api_key_env` → 常见环境变量回退（DASHSCOPE > OPENAI > ANTHROPIC）

Base URL 解析优先级：`__explicit_base_url__` → provider 的 `base_url` → `src.provider.profile` 注册表默认值

## 关键设计决策

1. **深度合并而非浅合并** — `deep_merge` 对嵌套 dict 递归合并，保留 base 中未被覆盖的键；列表和标量则完全覆盖。列表不合并是因为有序集合（如工具列表）合并可能导致重复或顺序混乱。

2. **`api_key_env` 延迟解析** — `resolve_env_credentials` 不替换 `api_key_env` 字段的值（保留环境变量名），由 `_resolve_api_key` 在运行时从 `os.environ` 动态读取，支持运行时环境变量变化。

3. **显式参数通过特殊键注入** — `__explicit_api_key__` 和 `__explicit_base_url__` 作为临时键存入 providers dict，不污染 Config 模型字段，仅在解析凭证时读取。

4. **Pydantic 快速失败** — 配置在加载入口即完成类型验证，避免无效配置在运行时才暴露难以调试的错误。

5. **provider profile 懒加载** — `get_base_url` 中对 `src.provider.profile` 的导入放在函数内部，避免循环依赖，同时允许 provider 注册表提供默认端点。

6. **常见环境变量自动检测** — `load_env_defaults` 自动识别 OPENAI_API_KEY、DASHSCOPE_API_KEY、ANTHROPIC_API_KEY 等业界标准变量，零配置即可启动。

## 对外接口

### 公开函数

| 函数 | 签名 | 用途 |
|------|------|------|
| `load_config` | `(model?, provider?, api_key?, base_url?, config_file?) → Config` | 加载完整配置（主入口） |
| `get_api_key` | `(config) → str \| None` | 获取解析后的 API Key |
| `get_base_url` | `(config) → str \| None` | 获取解析后的 Base URL |
| `load_json_file` | `(path) → dict \| None` | 安全加载 JSON 文件 |
| `deep_merge` | `(base, override) → dict` | 深度合并两个字典 |

### 公开模型

`Config`, `ModelConfig`, `ProviderConfig`, `McpConfig`, `McpServerConfig`, `TuiConfig`, `AuxiliaryConfig`

## 依赖关系

### 外部依赖

- **pydantic** — 数据模型定义与验证
- **python-dotenv** — .env 文件加载

### 对 src/ 模块的依赖

- `src.provider.profile.get_provider_profile` — 懒导入，用于 `get_base_url` 回退到 provider 注册表默认 URL

### 被依赖方

本模块是基础模块，被 `src/main.py`（入口注入）、`src/provider/`（凭证获取）、`src/conversation/`（配置读取）等模块广泛依赖。
