# Config 模块架构

## 概述

Config 模块提供 NanoHermes 的统一配置管理能力，从 JSON 配置文件、环境变量和显式参数中解析完整配置。

## 目录结构

```
src/config/
├── __init__.py      # 模块入口，导出 Config 和 load_config()
├── models.py        # Pydantic 数据模型定义
├── loader.py        # 配置加载、合并、解析逻辑
└── ARCHITECTURE.md  # 架构文档
```

## 数据模型

| 模型 | 说明 |
|------|------|
| `Config` | 根配置对象，包含所有配置段 |
| `ModelConfig` | 主模型配置（provider, name, context_length） |
| `ProviderConfig` | 提供商配置（base_url, api_key_env） |
| `McpConfig` | MCP 配置（servers 数组） |
| `McpServerConfig` | 单个 MCP 服务器（name, transport, command/args/url） |
| `TuiConfig` | TUI 配置（typing_speed, show_tool_panel, tool_panel_position） |
| `AuxiliaryConfig` | 辅助 LLM 配置（provider, model, max_tokens, temperature） |
| `ToolsConfig` | 工具 DFX 配置（max_tool_concurrency, tool_result_budget） |

## 配置优先级

```
显式参数 (load_config 调用时传入)
    ↓
项目配置 (./nanohermes.json)
    ↓
全局配置 (~/.nanohermes/config.json)
    ↓
环境变量 (.env)
    ↓
模块默认值 (Pydantic 字段默认值)
```

## 技术栈

- **Pydantic** - 数据模型定义和验证
- **json** - JSON 文件解析（Python 内置）
- **python-dotenv** - .env 文件加载

## 使用方式

```python
from src.config import load_config, Config

# 基础使用（自动加载配置文件）
config = load_config()

# 显式覆盖
config = load_config(model="gpt-4o", provider="openai")

# 获取解析后的凭证
from src.config import get_api_key, get_base_url
api_key = get_api_key(config)
base_url = get_base_url(config)
```
