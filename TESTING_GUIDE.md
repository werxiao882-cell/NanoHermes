# NanoHermes Testing Guide

## AI Agent 集成测试设计原则

> 基于 `ai-agent-integration-testing` skill 的方法论，定义 NanoHermes 集成测试的核心原则。

### 核心理念

**真实 API，无 Mock**：集成测试必须使用真实 LLM API 请求。Mock 测试无法发现工具链集成 bug、API 签名不匹配、序列化错误等真实问题。

**PTY 驱动，模拟真实用户**：通过 PTY 启动 Agent，模拟真实用户对话流程。不直接调用内部函数，而是通过 TUI 交互验证端到端行为。

**OpenSpec 驱动用例设计**：每个完成的 OpenSpec 变更映射为一组测试用例，覆盖核心功能、边界情况和与其他模块的集成。

### 测试方法论

| 测试类型 | 示例输入 | 验证点 |
|----------|---------|--------|
| 基础对话 | "Hello, introduce yourself" | AI 正确响应 |
| 工具: 读取 | "Read pyproject.toml" | read_file 调用，内容正确 |
| 工具: 写入 | "Create /tmp/test.txt with X" | write_file 调用，文件存在 |
| 工具: 编辑 | "Change line 2 to Y" | patch 调用，文件已更新 |
| 工具: 搜索 | "Find all .py files" | search_files 调用，结果正确 |
| 工具: 执行 | "Calculate primes under 100" | execute_code 调用，结果正确 |
| 多轮上下文 | "What was the file I just created?" | AI 引用了前面的对话 |
| 错误处理 | "Read /tmp/not_exist.txt" | 友好的错误提示 |
| 记忆系统 | "Remember I prefer Python" | MEMORY.md 已更新 |
| TUI 命令 | /tools, /sessions, /skills | 输出正确 |

### PTY 交互模式

```
terminal(pty=True, background=True, command="cd /path && python -m src.main")
process(action='wait', session_id='...', timeout=20)     # 等待启动
process(action='submit', session_id='...', data="Hello") # 发送消息
process(action='wait', session_id='...', timeout=60)     # 等待响应
# ... 重复每个测试 ...
process(action='submit', session_id='...', data="/quit") # 优雅退出
```

**重要**：LLM 响应使用 60-120s 超时，较短的超时会返回不完整输出。

### 已知陷阱

1. **不要假设 API 签名**：始终用 `inspect.signature()` 检查，参数可能与预期不同。
2. **Mock vs 真实 API**：集成测试用真实 API，Mock 测试遗漏工具链集成 bug。
3. **PTY 缓冲**：完成后用 `process(action='log')` 查看完整输出。
4. **Memory 去重**：`add_entry` 不检查重复，MEMORY.md 中可能有重复条目。这是已知限制，不是测试失败。
5. **AI 过度搜索**：当要求"测试工具"时，AI 可能多次调用 search_files 而非使用 /tools。这是预期行为——AI 按字面理解请求。
6. **清理**：杀死进程前始终发送 `/quit`。

### 验证清单

- [ ] 环境搭建（conda、依赖、API Keys）
- [ ] Agent 在 PTY 模式下启动
- [ ] 基础对话工作
- [ ] 每种工具类型已测试（read/write/edit/search/execute）
- [ ] 多轮上下文已验证
- [ ] 错误处理已测试
- [ ] 记忆持久化已验证
- [ ] 会话存储已验证（SQLite + JSONL）
- [ ] TUI 命令已测试
- [ ] Agent 优雅退出
- [ ] 结果已文档化
