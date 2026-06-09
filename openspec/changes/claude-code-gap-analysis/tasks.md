# Tasks: Claude Code 能力差距补充

## 1. 工具并发分组 (tool-concurrency-partitioning)

- [ ] 1.1 `ToolEntry` 新增 `is_concurrency_safe: Callable` 字段
- [ ] 1.2 为所有已注册工具声明 `is_concurrency_safe`（只读=True，写入/执行=False）
- [ ] 1.3 实现 `partition_tool_calls()` 分组函数
- [ ] 1.4 实现 `dispatch_batch()` 批量执行函数
- [ ] 1.5 修改 `conversation/loop.py` 使用 `dispatch_batch()` 替代逐个 `dispatch()`
- [ ] 1.6 编写并发分组单元测试
- [ ] 1.7 编写 dispatch_batch 集成测试

## 2. 工具结果预算 (tool-result-budget)

- [ ] 2.1 实现 `apply_tool_result_budget()` 截断函数
- [ ] 2.2 配置项 `tool_result_budget` 加入 `nanohermes.json` schema
- [ ] 2.3 环境变量 `NANOHERMES_TOOL_RESULT_BUDGET` 支持
- [ ] 2.4 `ToolEntry` 新增 `max_result_tokens` 可选覆盖
- [ ] 2.5 在 `dispatch()` 和 `dispatch_batch()` 中应用预算
- [ ] 2.6 编写截断逻辑单元测试

## 3. Context Modifier (context-modifier)

- [ ] 3.1 实现 `ContextModifier` 类和注册表
- [ ] 3.2 定义 4 种修改类型枚举
- [ ] 3.3 `write_file`/`patch` 工具注册 `file_attachment_update`
- [ ] 3.4 `terminal` 工具检测 `cd` 命令并注册 `working_directory_change`
- [ ] 3.5 在 `dispatch_batch()` 完成后调用 `apply_all()`
- [ ] 3.6 修改日志记录
- [ ] 3.7 编写 ContextModifier 单元测试

## 4. Headless/SDK Mode (headless-sdk-mode)

- [ ] 4.1 创建 `src/sdk.py` 模块
- [ ] 4.2 实现 `NanoHermesSDK` 类
- [ ] 4.3 实现 `chat(message) -> str` 方法
- [ ] 4.4 实现 `run_conversation(messages) -> dict` 方法
- [ ] 4.5 实现 `chat_stream(message) -> AsyncGenerator` 方法
- [ ] 4.6 实现自动初始化逻辑
- [ ] 4.7 `--headless` CLI flag 支持
- [ ] 4.8 编写 SDK 集成测试

## 5. CLAUDE.md 分级信任 (trust-levels)

- [ ] 5.1 实现 `TrustLevel` 枚举（managed > user > project > local）
- [ ] 5.2 实现文件位置 → 信任级别自动推断
- [ ] 5.3 实现 `@include` 指令解析器
- [ ] 5.4 实现深度上限检测（max: 5）
- [ ] 5.5 实现循环引用检测
- [ ] 5.6 实现信任冲突检测和日志
- [ ] 5.7 修改 `prompt/assembler.py` 按信任级别排序注入
- [ ] 5.8 编写信任模型单元测试

## 6. MCP 工程细节 (mcp-engineering)

- [ ] 6.1 实现自定义 `setTimeout` 超时控制
- [ ] 6.2 实现 `MAX_MCP_DESCRIPTION_LENGTH = 2048` 截断
- [ ] 6.3 实现本地/远端并发限流器（Semaphore）
- [ ] 6.4 实现 15 分钟 Auth Cache
- [ ] 6.5 实现 HTTP 404 / JSON-RPC -32001 自动重连
- [ ] 6.6 编写 MCP 工程细节单元测试
