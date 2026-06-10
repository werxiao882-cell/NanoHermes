## ADDED Requirements

### Requirement: Headless SDK interface

系统 SHALL 提供 `NanoHermesSDK` 类，支持无 UI 的编程式交互。使用者无需启动 TUI 即可与 Agent 对话。

#### Scenario: 简单聊天

- **WHEN** 调用 `sdk.chat("Hello")`
- **THEN** 返回 Agent 的文本回复
- **AND** 会话自动创建或恢复

#### Scenario: 完整对话循环

- **WHEN** 调用 `sdk.run_conversation(messages, tools=...)`
- **THEN** 执行完整对话循环（模型调用 → 工具分发 → 重试 → 后处理）
- **AND** 返回包含 `final_response`, `messages`, `tool_calls` 的字典

#### Scenario: 流式输出

- **WHEN** 调用 `sdk.chat_stream("Hello")`
- **THEN** 返回 AsyncGenerator，逐块产出回复内容
- **AND** 使用者可实时渲染流式输出

### Requirement: SDK auto-initialization

`NanoHermesSDK` 的构造函数 SHALL 自动初始化所有必要依赖，无需手动注入。

#### Scenario: 零配置初始化

- **WHEN** `NanoHermesSDK()` 无参数调用
- **THEN** 自动加载配置（`nanohermes.json` + `.env`）
- **AND** 自动初始化 SessionDB, ToolRegistry, Provider, Memory 等
- **AND** 使用默认 home 路径 `~/.nanohermes/`

#### Scenario: 自定义配置初始化

- **WHEN** `NanoHermesSDK(config_path="/path/to/config.json")`
- **THEN** 使用指定配置文件初始化
- **AND** 覆盖默认行为

### Requirement: Headless mode CLI flag

`python -m src.main` SHALL 支持 `--headless` 标志，以无 UI 模式运行。

#### Scenario: headless 模式

- **WHEN** `python -m src.main --headless -m "What files are in the current directory?"`
- **THEN** 执行对话并打印最终回复到 stdout
- **AND** 不渲染任何 TUI 组件
- **AND** 退出码 0 表示成功
