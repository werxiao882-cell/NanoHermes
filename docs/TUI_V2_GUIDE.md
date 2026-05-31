# NanoHermes TUI v2 用户指南

## 概述

NanoHermes TUI v2 是基于 `prompt_toolkit` + `rich` + ANSI 转义码的现代化终端用户界面，提供：

- 🎨 **丰富的样式** - 颜色、面板、加载动画
- ⌨️ **智能补全** - 命令、文件路径、上下文感知
- 📝 **流式输出** - 打字机效果、增量 Markdown 渲染
- 🛠️ **工具可视化** - 实时显示工具调用状态和历史
- 📐 **响应式布局** - 自适应终端尺寸

## 启动

```bash
# 默认启动 TUI v2
python -m src.main

# 使用旧版 CLI（fallback）
python -m src.main --cli
```

## 基本操作

### 输入消息

- 直接输入消息，按 **Enter** 发送
- 按 **Shift+Enter** 插入换行（多行输入）
- 按 **Ctrl+U** 清空当前输入
- 按 **Ctrl+D** 或输入 `/quit` 退出

### 命令

所有命令以 `/` 开头：

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/clear` | 清空屏幕 |
| `/quit` | 退出 TUI |
| `/resume <id>` | 恢复会话 |
| `/status` | 显示当前状态 |
| `/tools` | 显示工具调用历史 |

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 发送消息 |
| `Shift+Enter` | 插入换行 |
| `Ctrl+D` | 退出 |
| `Ctrl+C` | 中断当前操作 |
| `Ctrl+U` | 清空输入 |
| `Tab` | 触发补全 |
| `↑/↓` | 浏览历史记录 |
| `Ctrl+R` | 搜索历史 |

## 智能补全

### 命令补全

输入 `/` 后按 **Tab**，显示可用命令列表：

```
/ → /help, /clear, /quit, /resume, /status, /tools
```

### 文件路径补全

输入路径片段后按 **Tab**，自动补全文件和目录：

```
./src → ./src/main.py, ./src/cli/, ./src/tools/
```

## 工具调用可视化

当 Agent 调用工具时，TUI 会实时显示：

```
⏳ read_file (path=test.txt)  # 开始
🔄 read_file - 执行中...      # 运行中
✅ read_file - 读取 10 行，256 字符  # 成功
❌ read_file - 文件不存在     # 失败
```

输入 `/tools` 查看完整的工具调用历史。

## 流式输出

Agent 响应时使用打字机效果：

- 逐字符显示，模拟思考过程
- 按任意键跳过，立即显示完整内容
- 支持增量 Markdown 渲染（标题、列表、代码块等）

## 响应式布局

TUI 自动适应终端尺寸：

- **垂直分割** - 工具面板在左侧/右侧
- **水平分割** - 工具面板在底部
- **全屏模式** - 隐藏工具面板

调整终端窗口时自动重新布局。

## 配置

在 `~/.nanohermes/tui/state.json` 中保存配置：

```json
{
  "layout": {
    "show_tool_panel": true,
    "tool_panel_position": "right",
    "typing_speed": 10
  }
}
```

## 故障排除

### 终端尺寸过小

如果终端宽度 < 80 或高度 < 24，会显示警告。请调整窗口大小。

### 补全不工作

确保输入路径包含 `/` 或 `\` 或以 `.` 开头。

### 流式输出闪烁

启用双缓冲渲染（默认启用）。如仍有问题，尝试增大刷新间隔。

## 技术栈

- **prompt_toolkit** - 核心终端 UI 库
- **rich** - Markdown 渲染和表格
- **pygments** - 语法高亮
- **ANSI 转义码** - 底层终端控制

## 开发者

TUI v2 源码位于 `src/cli/tui_v2/`：

```
src/cli/tui_v2/
├── __init__.py
├── app.py              # TUIApp 主类
├── state.py            # TUIState 状态管理
├── event_handler.py    # TUIEventHandler 事件处理
├── completers.py       # 补全器
├── history.py          # 输入历史
├── streaming.py        # 流式输出
├── layout.py           # 布局系统
├── components/
│   ├── __init__.py
│   ├── widgets.py      # 面板、加载指示器、进度条
│   └── tool_display.py # 工具调用可视化
└── utils/
    ├── __init__.py
    └── ansi.py         # ANSI 控制码
```

测试位于 `tests/cli/tui_v2/`。
