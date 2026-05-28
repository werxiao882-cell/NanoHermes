# CLI Architecture

## Responsibility
现代化聊天界面实现，支持传统 CLI 和 TUI 两种模式。
提供用户交互、斜杠命令处理、工具调用显示、对话循环集成。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    User Input                                 │
│                  (prompt_toolkit)                             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Slash Command Handler                      │
│                                                              │
│  /clear, /status, /sessions, /title, /skills, /tools         │
│  Auto-completion via SlashCommandCompleter                   │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Conversation Loop                          │
│                                                              │
│  model_caller(messages, tools) → response                    │
│  tool_dispatch(name, args) → result                          │
│  Tool result summary display                                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    TUI Chat (tui_chat.py)                     │
│                                                              │
│  Banner: Model, Tools, Skills, Session info                  │
│  Conversation: User/Assistant/Tool messages                  │
│  Tool Progress: preparing → executing → complete             │
│  Tool Summary: read_file (N lines), write_file (N bytes)     │
│  Input: prompt_toolkit with slash command completion         │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 用户输入消息或斜杠命令
2. 斜杠命令由 TUI/CLI 直接处理（/clear, /status 等）
3. 普通消息传递给 ConversationLoop
4. ConversationLoop 调用 model_caller 获取模型响应
5. 如果响应包含 tool_calls，调用 tool_dispatch 执行工具
6. 显示工具调用进度和简要结果
7. 将工具结果返回给模型，继续循环
8. 最终文本响应显示给用户

## Design Decisions
- **Decision**: 使用 prompt_toolkit 作为输入库
  - **Reason**: 支持历史记录、自动补全、样式定制
- **Decision**: TUI 和传统 CLI 共享相同的对话循环逻辑
  - **Reason**: 代码复用，行为一致
- **Decision**: 工具调用显示简要结果而非完整输出
  - **Reason**: 避免冗长输出干扰用户，保持界面清晰

## Dependencies
- Internal: src/conversation/loop.py, src/tools/dispatcher.py
- External: prompt_toolkit, rich
