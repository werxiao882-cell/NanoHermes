# NanoHermes TUI 用户指南

## 概述

NanoHermes TUI 是基于 `prompt_toolkit` + `rich` + ANSI 转义码的现代化终端用户界面，提供：

- 🎨 **丰富的样式** - 颜色、面板、加载动画
- ⌨️ **智能补全** - 命令、文件路径、上下文感知
- 📝 **流式输出** - 打字机效果、增量 Markdown 渲染
- 🛠️ **工具可视化** - 实时显示工具调用状态和历史
- 📐 **响应式布局** - 自适应终端尺寸

## 启动

```bash
# 启动 TUI
python -m src.main
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

TUI 使用统一的配置系统（`src/config/`），支持多种配置来源。

### 配置优先级

配置按以下优先级加载（从高到低）：

1. **显式参数**：命令行参数 `--model`, `--provider`
2. **项目配置**：`./nanohermes.json`（项目根目录）
3. **全局配置**：`~/.nanohermes/config.json`
4. **环境变量**：`.env` 文件
5. **默认值**：内置默认配置

### 配置文件示例

**项目配置** (`nanohermes.json`)：

```json
{
  "model": {
    "provider": "openai",
    "name": "gpt-4o",
    "context_length": 128000
  },
  "tui": {
    "typing_speed": 15,
    "show_tool_panel": true,
    "tool_panel_position": "right"
  },
  "auxiliary": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "max_tokens": 2000
  }
}
```

**环境变量** (`.env`)：

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o
```

### TUI 配置选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `typing_speed` | int | 10 | 打字机效果速度（字符/秒） |
| `show_tool_panel` | bool | true | 显示工具面板 |
| `tool_panel_position` | str | "right" | 工具面板位置（left/right/bottom） |

### 配置模型

所有配置使用 Pydantic 模型定义，详见 `src/config/models.py`：

- `ModelConfig`：主模型配置
- `ProviderConfig`：提供商配置
- `TuiConfig`：TUI 配置
- `AuxiliaryConfig`：辅助 LLM 配置
- `McpConfig`：MCP 服务器配置

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

TUI 源码位于 `src/cli/`：

```
src/cli/
├── __init__.py
├── tui.py              # TUIApp 主类
├── state.py            # TUIState 状态管理
├── event_handler.py    # TUIEventHandler 事件处理
├── completers.py       # 补全器
├── history.py          # 输入历史
├── streaming.py        # 流式输出
├── layout.py           # 布局系统
├── widgets.py          # 面板、加载指示器、进度条、工具显示
└── ARCHITECTURE.md     # 架构文档
```

测试位于 `tests/cli/`。
