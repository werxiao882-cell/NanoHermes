# CLI 模块架构

## 概述

CLI 模块提供 NanoHermes 的终端用户界面。仅支持 TUI v2 现代化终端界面，从 `src/config/` 配置模块读取所有设置。

## 目录结构

```
src/cli/
├── __init__.py          # 模块初始化，导出所有公共接口
├── ARCHITECTURE.md      # 架构文档
├── tui.py               # TUI 主应用（合并 app.py + adapter.py）
├── state.py             # 状态管理器（TUIState, ToolCallRecord）
├── event_handler.py     # 事件处理器（用户输入、命令、工具事件）
├── completers.py        # 输入补全器（命令、文件路径、上下文感知）
├── history.py           # 输入历史（prompt_toolkit History 持久化）
├── streaming.py         # 流式输出（打字机效果、Markdown 渲染）
├── layout.py            # 响应式布局（LayoutManager, DynamicPanelManager）
└── widgets.py           # UI 组件（合并 ANSI 控制 + 面板 + 状态栏 + 工具显示）
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

## 启动方式

```bash
# 启动 TUI v2（唯一支持的方式）
python -m src.main

# 测试 API 连接
python -m src.main --test-api
```

## 已移除

- `streaming_cli.py` - 旧版流式 CLI（已移除）
- `tui_chat.py` - 旧版 TUI（已移除）
- `tui_v2/` 目录 - 已扁平化为当前结构（16 文件 → 9 文件）
- `--cli` 标志 - 旧版 CLI 回退（已移除）
