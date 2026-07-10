## 上下文

业界成熟的自进化 AI Agent 系统的上下文压缩模块 (~1750 LOC) 实现了完整的上下文压缩系统。核心设计决策包括：
- **ContextEngine ABC**：可插拔上下文引擎，第三方引擎可替换内置压缩器
- 使用辅助（便宜/快速）LLM 模型进行摘要生成
- 保护头部和尾部上下文（情景记忆理论）
- 结构化摘要模板（目标、进展、关键决策、修改文件、下一步）
- 工具输出剪枝（旧结果替换、图像占位符、参数截断）
- 迭代摘要更新（保持多次压缩后的连贯性）
- 按比例缩放的摘要预算（20% 比例，最小 2000 token，最大 12000 token）
- Session Splitting + parent_session_id 血缘链
- `on_pre_compress` 钩子通知 Memory Provider 提取信息
- 熔断器模式防止压缩循环
- 动态预算追踪监控压缩效率
- 多种压缩触发模式（Reactive/Micro/Snip）
- 压缩质量验证器评估信息保留度

NanoHermes 使用 Python 实现相同的功能。

## 目标 / 非目标

**目标：**
- 实现 ContextEngine 抽象基类（可插拔扩展点）
- 实现完整的 ContextCompressor 压缩引擎
- 实现辅助 LLM 客户端配置和可行性检查
- 实现工具输出剪枝
- 实现会话分割和 ID 轮换（Session Splitting + parent_session_id 血缘链）
- 实现 `on_pre_compress` 钩子通知 Memory Provider
- 实现熔断器、预算追踪器、压缩模式、验证器

**非目标：**
- 不实现图像大小调整恢复（try_shrink_image_parts_in_messages）
- 不实现手动压缩反馈（manual_compression_feedback）
- 不实现外部 ContextEngine 插件（LCM、自定义摘要引擎）— 预留接口

## 技术方案

### 1. ContextEngine 抽象基类

使用 Python 抽象基类定义可插拔上下文引擎接口。内置的 `ContextCompressor` 完整实现这个 ABC。用户可以通过配置切换引擎，而编排层只面向 `ContextEngine` 接口编程。

### 2. ContextCompressor 上下文压缩引擎

```
消息列表: [sys, u1, a1, u2, a2, tool1, u3, a3, ..., u20, a20]
                |←  head 保护 →|                        |←  tail 保护  →|
                    (前 3 条)                              (最后 20 条)
                                  |←     middle 区域     →|
                                      ↓ 这部分被摘要
```

**分层压缩策略：**
1. Tool Output Pruning（廉价，无 LLM 调用）
2. Head/Tail 保护（情景记忆理论）
3. 结构化摘要生成（辅助 LLM）
4. Session Splitting（创建新 session，建立血缘链）

**参数配置：**

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `threshold_percent` | 0.50 | 使用达到 50% 上下文时触发压缩 |
| `protect_first_n` | 3 | 保护前 3 条消息（system + 第一轮对话） |
| `protect_last_n` | 20 | 保护最后 20 条消息 |
| `summary_target_ratio` | 0.20 | 尾部保护预算占阈值的 20% |

### 3. 辅助客户端可行性检查

验证辅助模型上下文窗口是否满足压缩需求：
- 小于最小要求（32K tokens）→ 不可行
- 小于主模型压缩阈值（80%）→ 可行但警告
- 否则 → 完全可行

### 4. 工具输出剪枝

- 旧工具结果（>200 字符）替换为占位符
- 工具调用参数截断：解析 JSON → 截断字符串叶子节点 → 重新序列化（保持 JSON 有效性）

### 5. 迭代摘要更新

`_previous_summary` 存储上次摘要。新压缩不是从零开始，而是更新已有摘要，保持多次压缩后的连贯性。

### 6. 熔断器模式（Circuit Breaker）

三状态机：CLOSED → OPEN → HALF_OPEN → CLOSED
- 连续失败 3 次 → OPEN（冷却期 5 分钟）
- 冷却期后 → HALF_OPEN（允许一次试探）
- 试探成功 → CLOSED，失败 → OPEN

### 7. 预算追踪器（Budget Tracker）

环形缓冲区存储压缩历史，提供：
- 平均压缩比
- 总节省 token 数
- 成功率
- 历史记录查询

### 8. 压缩模式（Compression Modes）

| 模式 | 触发条件 | 适用场景 |
|------|---------|---------|
| Reactive | token 超阈值 | 默认模式，平衡性能和质量 |
| Micro | 每 N 轮对话 | 高频小压缩，保持上下文紧凑 |
| Snip | 消息内容特征匹配 | 精准裁剪，只移除冗余内容 |

### 9. 压缩验证器（Validator）

评估维度：
- 信息保留率（Jaccard 相似度，阈值 0.60）
- 摘要长度（500-12000 字符）
- 关键信息完整性（文件变更、用户意图、工具调用）

### 10. Memory Provider 的 on_pre_compress 钩子

压缩发生前，`MemoryManager` 通知外部 memory provider 提取有价值信息，确保信息不会在压缩中丢失。

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| 辅助 LLM 调用增加成本 | 使用小型/快速模型，配置可调节压缩阈值 |
| 摘要丢失重要信息 | 结构化摘要模板跟踪目标/进展/关键决策 |
| 迭代摘要可能累积错误 | 每次压缩保留前次摘要内容并合并新信息 |
| 压缩触发 prompt cache miss | 可接受代价，远小于 context_length_exceeded 错误 |
| 工具参数截断破坏 JSON | 解析 JSON 后截断字符串叶子节点，重新序列化 |
| 压缩循环重试 | 熔断器自动降级，防止无限循环 |

## 设计哲学：情景记忆

压缩算法的 head/tail 保护揭示了一种特定的记忆理论：前几轮交互建立了上下文和意图（`protect_first_n=3`），最近的交互包含当前活跃的工作状态（`protect_last_n` 由 token 预算动态决定），中间的一切都是可替换的。这与人类的**情景记忆**一致——我们记住开头和结尾，不记得中间。中间部分可以被摘要，因为它的目的是**到达**当前状态，而不是**成为**当前状态。
