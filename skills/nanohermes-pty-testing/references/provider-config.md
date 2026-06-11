# Provider 运行时 + 配置系统 + 提示组装 — 56 用例

## provider-runtime (37 用例)

### API 调用基础 (8)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| P-01 | API 调用 | 发送消息 | 正常响应 | [PTY] |
| P-02 | 流式输出 | 观察 AI 回复 | 实时更新 | [PTY] |
| P-04 | 模型信息 | 状态栏显示 | 正确模型名 | [PTY] |
| P-05 | Token 计数 | 状态栏 token | 计数准确 | [PTY] |
| P-07 | 流式完整性 | 完整回复内容 | 流式包含全部文本 | [PTY] |
| P-16 | chat_completion 基础 | 标准聊天 | 返回 ChatResponse | [PTY] |
| P-17 | chat_completion tools | 传工具 schema | 工具调用返回 | [PTY] |
| P-20 | stream_completion | 流式调用 | 逐个 yield 增量 | [PTY] |

### 流式细节 (4)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| P-18 | chat_completion temperature | 传 temperature | 温度参数生效 | [UNIT] |
| P-19 | chat_completion max_tokens | 传 max_tokens | 最大 token 限制 | [UNIT] |
| P-21 | 流式最终响应 | 生成器最后 yield | ChatResponse | [PTY] |
| P-32 | finish_reason stop | 正常结束 | finish_reason='stop' | [PTY] |

### Token 与响应 (4)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| P-08 | Token 准确性 | 对比输入输出 token | 计数准确 | [PTY] |
| P-12 | 定价数据 | 检查定价模型 | 数据正确加载 | [PTY] |
| P-31 | Token 提取 | 从响应解析 usage | input/output/cache token | [PTY] |
| P-36 | TokenUsage total | total_tokens 属性 | input + output | [PTY] |

### finish_reason (3)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| P-32 | finish_reason stop | 正常结束 | finish_reason='stop' | [PTY] |
| P-33 | finish_reason tool_calls | 工具调用 | finish_reason='tool_calls' | [PTY] |
| P-34 | finish_reason length | 超出长度 | finish_reason='length' | [UNIT] |

### 错误分类 (8)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| P-23 | 错误分类 auth | 401/403 | ErrorCategory.AUTH | [FAULT] |
| P-24 | 错误分类 billing | 402 | ErrorCategory.BILLING | [FAULT] |
| P-25 | 错误分类 rate_limit | 429 | ErrorCategory.RATE_LIMIT, retryable | [FAULT] |
| P-26 | 错误分类 context_overflow | 超出上下文 | ErrorCategory.CONTEXT_OVERFLOW | [DEBUG] |
| P-27 | 错误分类 server_error | 5xx | ErrorCategory.SERVER_ERROR, retryable | [FAULT] |
| P-28 | 错误分类 network_error | 连接失败 | ErrorCategory.NETWORK_ERROR, retryable | [FAULT] |
| P-29 | 错误分类 format_error | 响应格式错误 | ErrorCategory.FORMAT_ERROR | [UNIT] |
| P-30 | 错误分类 unknown | 未知错误 | ErrorCategory.UNKNOWN | [UNIT] |

### 错误处理与可中断 (3)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| P-03 | 错误处理 | 模拟 API 失败 | 优雅处理 | [FAULT] |
| P-22 | interruptible_call | 可中断调用 | Ctrl+C 可中断 | [UNIT] |
| P-09 | 错误分类 | 各类 API 错误 | 正确分类 | [FAULT] |

### 凭证与配置 (3)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| P-11 | 凭证优先级 | 多层配置启动 | 显式>JSON>.env>默认 | [PTY] |
| P-13 | API 模式 | chat/extended 切换 | 正确切换 | [UNIT] |
| P-15 | 配置档案 | profile 配置加载 | 正确加载 | [UNIT] |

### Anthropic 适配 (1)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| P-14 | 缓存适配 | Anthropic prompt caching | 标记正确 | [MANUAL] |

### reasoning 与 debug (3)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| P-35 | reasoning 提取 | extended thinking | reasoning 字段提取 | [DEBUG] |
| P-37 | debug 模式 | _debug=True | 输出完整请求体 | [DEBUG] |
| P-06 | 回退链 | 主提供商失败 | 自动回退 | [FAULT] |
| P-10 | 回退链配置 | 检查回退配置 | 配置正确加载 | [FAULT] |

## config-system (11 用例)

### 配置加载 (5)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| CF-01 | .env 加载 | 检查 API Key | 正确读取 | [PTY] |
| CF-02 | JSON 配置 | nanohermes.json | 正确解析 | [PTY] |
| CF-03 | 配置优先级 | 多层配置验证 | 优先级正确 | [PTY] |
| CF-04 | 默认值回退 | 无配置启动 | 使用默认值 | [PTY] |
| CF-05 | Pydantic 验证 | 写无效 JSON 启动 | 验证错误 | [PTY] |

### 高级配置 (4)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| CF-06 | 多提供商 | dashscope/openai | 同时配置 | [PTY] |
| CF-08 | deep_merge | 嵌套配置合并 | 深度合并正确 | [UNIT] |
| CF-09 | 环境变量解析 | 配置中引用环境变量 | 自动解析 | [PTY] |
| CF-11 | 辅助配置 | auxiliary 配置 | 正确加载 | [PTY] |

### TUI 配置 (2)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| CF-07 | TUI 配置 | typing_speed 等 | 配置生效 | [PTY] |
| CF-10 | TUI 生效验证 | 观察界面行为 | 配置真正生效 | [PTY] |

## prompt-assembly (8 用例)

### 三层提示 (3)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| PA-01 | stable 层 | 身份和规则 | 稳定不变 | [PTY] |
| PA-02 | context 层 | 上下文文件 | 正确注入 | [DEBUG] |
| PA-03 | volatile 层 | 记忆快照 | 每轮更新 | [DEBUG] |

### 安全与优化 (4)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| PA-04 | 缓存控制 | Anthropic prompt caching | stable 适合缓存 | [MANUAL] |
| PA-05 | 工具指导 | AI 正确使用工具 | 提示注入正确 | [PTY] |
| PA-06 | 模型家族 | OpenAI 兼容模式 | 提示正确 | [PTY] |
| PA-07 | 威胁检测 | 10 种威胁模式 | 检测正常 | [DEBUG] |
| PA-08 | Unicode 检测 | 发送不可见字符 | 检测并拒绝 | [PTY] |

### 缓存优化 (1)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| PA-04 | 缓存断点 | stable 层标记 | 最后一个 stable 部分标记 | [DEBUG] |

## 测试优先级

**P0（阶段 2+3 必测）**：P-01, P-02, P-04, P-05, P-07, P-08, P-11, P-12, P-16, P-17, P-20, P-21, P-31, P-32, P-33, P-36, CF-01~07, CF-09, CF-10, CF-11, PA-01, PA-05, PA-06, PA-08

**P1（需 --debug）**：PA-02, PA-03, PA-07, P-26, P-35, P-37

**P2（需故障注入）**：P-03, P-06, P-09, P-10, P-23~25, P-27~28

**P3（仅手动/单元）**：P-13, P-14, P-15, P-18, P-19, P-22, P-29, P-30, P-34, CF-08, PA-04
