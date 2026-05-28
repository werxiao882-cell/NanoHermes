# Context Compression Architecture

## Responsibility
上下文压缩引擎，当对话超出模型上下文窗口时自动压缩。
检测使用率、生成摘要、保护头部和尾部上下文、剪枝工具输出。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    Conversation Loop                          │
│                  needs_compression(tokens)                    │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   ContextCompressor                           │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Threshold Detection                                    │  │
│  │  - pre_compress: >50% context window                   │  │
│  │  - force_compress: >85% context window                 │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Summary Budget Calculation                             │  │
│  │  - 20% of available tokens                             │  │
│  │  - Min: 2000 tokens, Max: 12000 tokens                 │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Message Compression                                    │  │
│  │  - Preserve system messages                            │  │
│  │  - Protect head (first 2 messages)                     │  │
│  │  - Protect tail (last 20 messages)                     │  │
│  │  - Insert summary between head and tail                │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Tool Output Pruning                                    │  │
│  │  - Truncate long outputs to max_length                 │  │
│  │  - Add "[truncated]" marker                            │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 对话循环检查当前 token 数是否超过阈值
2. 如果超过预压缩阈值（50%），触发预压缩
3. 如果超过强制压缩阈值（85%），触发强制压缩
4. 计算摘要预算（20% 可用 token，最小 2000，最大 12000）
5. 分离 system 消息、头部消息、尾部消息
6. 使用辅助 LLM 生成中间消息的摘要
7. 构建压缩后的消息列表：system + head + summary + tail
8. 工具输出在发送给 LLM 前进行剪枝

## Design Decisions
- **Decision**: 头部保护 2 条消息，尾部保护 20 条消息
  - **Reason**: 头部包含重要上下文，尾部包含最近对话，都需要保留
- **Decision**: 摘要预算为 20% 可用 token
  - **Reason**: 平衡摘要质量和 token 使用效率
- **Decision**: 工具输出剪枝使用固定长度限制
  - **Reason**: 简单有效，避免过长输出占用上下文

## Dependencies
- Internal: src/auxiliary/client.py (辅助 LLM 用于生成摘要)
- External: None
