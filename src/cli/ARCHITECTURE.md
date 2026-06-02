# CLI 模块架构

## 概述

CLI 模块提供 NanoHermes 的终端用户界面。从 `src/config/` 配置模块读取所有设置。

## 目录结构

```
src/cli/
├── __init__.py          # 模块初始化，导出所有公共接口
├── ARCHITECTURE.md      # 架构文档
├── tui.py               # TUI 主应用
├── state.py             # 状态管理器（TUIState, ToolCallRecord）
├── event_handler.py     # 事件处理器（用户输入、命令、工具事件）
├── completers.py        # 输入补全器（命令、文件路径、上下文感知）
├── history.py           # 输入历史（prompt_toolkit History 持久化）
├── streaming.py         # 流式输出（打字机效果、Markdown 渲染）
├── layout.py            # 响应式布局（LayoutManager, DynamicPanelManager）
└── widgets.py           # UI 组件（面板、状态栏、工具显示、ANSI 控制）
```

## 技术栈

- **prompt_toolkit** - 核心终端 UI 库（输入、补全、历史记录）
- **rich** - Markdown 渲染和面板
- **Pydantic** - 配置数据模型（通过 config 模块）
- **ANSI 转义码** - 底层终端控制

## 配置集成

TUI 从 `src/config/` 模块读取配置：

```python
from src.config import load_config

config = load_config()
typing_speed = config.tui.typing_speed
show_panel = config.tui.show_tool_panel
```

### 配置优先级

配置加载遵循以下优先级（从高到低）：

1. **显式参数**：命令行传入的 `--model`, `--provider` 等
2. **项目配置**：`./nanohermes.json`（项目根目录）
3. **全局配置**：`~/.nanohermes/config.json`
4. **环境变量**：`.env` 文件（`OPENAI_API_KEY`, `MODEL_NAME` 等）
5. **默认值**：Pydantic 模型定义的默认值

### 配置数据模型

所有配置使用 Pydantic 模型定义（`src/config/models.py`）：

- `ModelConfig`：主模型配置（provider, name, context_length）
- `ProviderConfig`：提供商配置（base_url, api_key_env）
- `TuiConfig`：TUI 配置（typing_speed, show_tool_panel, tool_panel_position）
- `AuxiliaryConfig`：辅助 LLM 配置（provider, model, max_tokens, temperature）
- `McpConfig`：MCP 服务器配置

### Provider 注册表集成

配置模块与 `src/provider/builtins.py` 注册表集成：

- 当 `base_url` 未在配置中指定时，从 ProviderProfile 获取默认值
- 支持 OpenAI、Anthropic、OpenRouter、Custom 等内置提供商

## 启动方式

```bash
# 启动 TUI
python -m src.main

# 测试 API 连接
python -m src.main --test-api

# 指定模型和提供商
python -m src.main --model gpt-4o --provider openai
```
