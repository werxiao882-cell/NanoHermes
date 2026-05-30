# CLI 模块架构

## 概述

CLI 模块提供 NanoHermes 的终端用户界面。仅支持 TUI v2 现代化终端界面。

## 目录结构

```
src/cli/
├── __init__.py          # 模块初始化
├── ARCHITECTURE.md      # 架构文档
└── tui_v2/              # TUI v2 现代化界面
    ├── __init__.py
    ├── app.py           # TUI 主应用类
    ├── adapter.py       # 系统适配器（模型调用、工具分发）
    ├── state.py         # 状态管理器
    ├── event_handler.py # 事件处理器
    ├── completers.py    # 输入补全器
    ├── history.py       # 输入历史
    ├── streaming.py     # 流式输出
    ├── layout.py        # 响应式布局
    ├── components/      # UI 组件
    │   ├── widgets.py   # 面板、加载指示器、进度条
    │   ├── status_bar.py# 状态栏
    │   ── tool_display.py # 工具可视化
    └── utils/
        └── ansi.py      # ANSI 转义码控制
```

## 技术栈

- **prompt_toolkit** - 核心终端 UI 库（输入、补全、历史记录）
- **rich** - Markdown 渲染和面板
- **ANSI 转义码** - 底层终端控制

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
- `--cli` 标志 - 旧版 CLI 回退（已移除）
