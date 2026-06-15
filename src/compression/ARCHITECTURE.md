# Context Compression Architecture

## Responsibility
上下文压缩引擎，当对话超出模型上下文窗口时自动压缩。
检测使用率、生成摘要、保护头部和尾部上下文、剪枝工具输出。

### 压缩策略理论基础
- **首因效应（Primacy Effect）**：人类记忆倾向于记住开头的信息，因此保护头部消息
- **近因效应（Recency Effect）**：人类记忆倾向于记住最近的信息，因此保护尾部消息
- **情景记忆理论**：对话的初始意图和最近工作记忆最重要

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
│  │  Circuit Breaker (熔断器)                               │  │
│  │  - 防止压缩循环，连续失败后自动降级                      │  │
│  │  - 三状态：CLOSED → OPEN → HALF_OPEN → CLOSED          │  │
│  │  - 冷却期机制：失败后等待一段时间再尝试                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Budget Tracker (预算追踪器)                            │  │
│  │  - 监控压缩前后的 token 使用情况                         │  │
│  │  - 计算压缩效率、成功率、节省 token 数                   │  │
│  │  - 环形缓冲区存储最近 100 次压缩记录                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Compression Validator (压缩验证器)                     │  │
│  │  - 评估压缩质量：信息保留度、摘要长度、关键信息完整性    │  │
│  │  - 验证失败时提供警告，帮助优化压缩策略                  │  │
│  │  - 使用 Jaccard 相似度计算关键词保留率                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Compression Modes (压缩模式)                           │  │
│  │  - Reactive: 基于 token 阈值触发（默认）                 │  │
│  │  - Micro: 基于对话轮次触发（频繁小压缩）                 │  │
│  │  - Snip: 基于消息内容特征触发（精准裁剪）                │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Threshold Detection                                    │  │
│  │  - pre_compress: >50% context window                   │  │
│  │    触发时机：对话进行到一半，提前准备压缩                │  │
│  │  - force_compress: >85% context window                 │  │
│  │    触发时机：接近极限，必须压缩否则截断                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Summary Budget Calculation                             │  │
│  │  - 公式：max(2000, min(chars * 0.20 / 4, 12000))       │  │
│  │  - 20% of available tokens                             │  │
│  │  - Min: 2000 tokens (保证摘要质量)                     │  │
│  │  - Max: 12000 tokens (防止摘要过长)                    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Message Compression                                    │  │
│  │  - Preserve system messages (系统提示永不压缩)         │  │
│  │  - Protect head (first 3 messages)                     │  │
│  │    理论依据：首因效应，对话锚点                        │  │
│  │  - Protect tail (last 20 messages, token 预算)         │  │
│  │    理论依据：近因效应，工作记忆                        │  │
│  │  - Insert summary between head and tail                │  │
│  │    摘要格式：Goal/Progress/Key Decisions/Next Steps    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Session Splitting (终极手段)                           │  │
│  │  - 当压缩无法满足时的处理方式                          │  │
│  │  - 创建新 session 并建立血缘关系                       │  │
│  │  - 保留关键上下文到新会话                              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Tool Output Pruning                                    │  │
│  │  - Truncate long outputs to max_length                 │  │
│  │  - Add "[truncated]" marker                            │  │
│  │  - 在发送给 LLM 前剪枝，节省 token                     │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 对话循环检查当前 token 数是否超过阈值
2. 如果超过预压缩阈值（50%），触发预压缩
3. 如果超过强制压缩阈值（85%），触发强制压缩
4. 计算摘要预算（20% 可用 token，最小 2000，最大 12000）
5. 分离 system 消息、头部消息（3 条）、尾部消息（20 条或 token 预算）
6. 使用主对话的 model_caller 生成中间消息的摘要
7. 构建压缩后的消息列表：system + head + summary + tail
8. 工具输出在发送给 LLM 前进行剪枝
9. 如果压缩后仍超出限制，触发 Session Splitting

## Design Decisions

### 熔断器模式（Circuit Breaker）
- **Decision**: 实现三状态熔断器防止压缩循环
- **Reason**: 
  - 连续压缩失败可能表明系统性问题（如 LLM 服务不可用）
  - 熔断器在连续 3 次失败后自动"断开"，拒绝后续压缩请求
  - 冷却期（60 秒）后进入探测状态，允许单次尝试
  - 成功则恢复，失败则继续熔断
  - 这种模式借鉴了电路保险丝的设计理念，保护系统免受级联故障影响

### 预算追踪器（Budget Tracker）
- **Decision**: 使用环形缓冲区监控压缩效率
- **Reason**: 
  - 提供可观测性，帮助优化压缩策略和配置
  - 环形缓冲区固定大小（100 条记录），自动淘汰旧数据，避免内存泄漏
  - 统计指标：平均压缩比、总节省 token、成功率、平均耗时
  - 压缩效率 = (1 - 平均压缩比) × 成功率，综合评估压缩效果

### 压缩模式（Compression Modes）
- **Decision**: 实现三种独立的触发模式，由配置选择
- **Reason**: 
  - **Reactive（响应式）**：基于 token 阈值触发，适合长对话
    - 触发条件：`current_tokens >= threshold × max_tokens`
    - 优点：简单直观，节省计算资源
    - 缺点：可能突然触发，用户感知明显
  - **Micro（微压缩）**：基于对话轮次触发，适合持续对话
    - 触发条件：每 N 轮对话后（默认 N=10）
    - 优点：频繁小压缩，用户感知平滑
    - 缺点：压缩频率高，增加计算开销
  - **Snip（裁剪）**：基于消息内容特征触发，适合精准裁剪
    - 触发条件：检测到代码块、日志、traceback 等长内容
    - 优点：精准控制，保留对话连贯性
    - 缺点：需要消息分类逻辑

### 压缩验证器（Compression Validator）
- **Decision**: 实现轻量级验证器评估压缩质量
- **Reason**: 
  - 验证三个维度：信息保留度、摘要长度、关键信息完整性
  - 信息保留度使用 Jaccard 相似度计算关键词集合的交集/并集
  - 摘要长度限制在 500-12000 字符，避免过度压缩或摘要过长
  - 关键信息检查：文件变更、用户意图、工具调用
  - 验证失败时提供警告，但不强制回滚（避免压缩循环）

### 头部保护（3 条消息）
- **Decision**: 保护前 3 条消息
- **Reason**: 
  - 基于情景记忆理论的"首因效应"
  - 第 1 条通常是 system prompt，定义 AI 身份和行为
  - 第 2-3 条通常包含用户的初始意图和任务描述
  - 这些是对话的"锚点"，删除会导致模型迷失上下文

### 尾部保护（token 预算）
- **Decision**: 保护尾部消息使用动态 token 预算而非固定条数
- **Reason**: 
  - 基于"近因效应"，最近的工作记忆最重要
  - 动态预算确保工作记忆在可控空间内最大化
  - 公式：`max(2000, min(chars * 0.20 / 4, 12000))`
  - 20% 比例平衡摘要质量和 token 使用效率
  - 上下限保护防止极端情况（摘要太短或太长）

### 中间摘要生成
- **Decision**: 使用主对话的 model_caller 生成结构化摘要
- **Reason**: 
  - 摘要格式：Goal/Progress/Key Decisions/Modified Files/Next Steps
  - 结构化格式便于模型理解历史上下文
  - 迭代更新保持连贯性（追加而非覆盖）
  - 复用主对话客户端，简化架构，无需独立的辅助 LLM 管理

### Session Splitting
- **Decision**: 当压缩无法满足时创建新 session
- **Reason**: 
  - 这是终极手段，避免对话完全失败
  - 建立血缘关系（parent_session_id）便于追踪
  - 保留关键上下文到新会话，减少信息丢失

### 分层压缩策略
- **Decision**: 平衡"保留重要信息"和"控制 token 消耗"
- **Reason**: 
  - 头部和尾部保护重要信息
  - 中间摘要压缩冗余内容
  - 工具输出剪枝节省 token
  - 多层策略确保压缩效果

## Dependencies
- Internal: src/config/ (配置模块)
- External: None

## Usage Examples

### 基本使用（默认配置）

```python
from src.compression import ContextCompressor

# 使用默认配置：Reactive 模式，启用所有增强组件
compressor = ContextCompressor(model="qwen-turbo")

# 检查是否需要压缩
if compressor.should_compress(messages=messages, current_tokens=5000):
    result = compressor.compress(messages=messages, current_tokens=5000)
    print(f"压缩效率: {result['compression_efficiency']:.2%}")
    print(f"熔断器状态: {result['circuit_breaker_state']}")
```

### 自定义压缩模式

```python
# Micro 模式：每 5 轮对话触发一次压缩
compressor = ContextCompressor(
    model="qwen-turbo",
    compression_mode="micro",
    micro_interval=5,
)

# 在对话循环中增加轮次计数
for turn in conversation:
    # ... 处理对话 ...
    compressor.increment_turn_count()
    
    if compressor.should_compress(messages=messages):
        result = compressor.compress(messages=messages)
```

### Snip 模式：精准裁剪

```python
# Snip 模式：检测到代码块或日志时触发压缩
compressor = ContextCompressor(
    model="qwen-turbo",
    compression_mode="snip",
    snip_patterns=["```", "ERROR:", "WARNING:", "traceback:"],
)

if compressor.should_compress(messages=messages):
    result = compressor.compress(messages=messages)
```

### 自定义熔断器参数

```python
# 自定义熔断器：更严格的失败阈值和更长的冷却期
compressor = ContextCompressor(
    model="qwen-turbo",
    circuit_breaker_threshold=5,  # 连续 5 次失败后熔断
    circuit_breaker_cooldown=120.0,  # 冷却期 120 秒
)
```

### 查询预算追踪统计

```python
# 查询压缩统计信息
tracker = compressor._budget_tracker

print(f"历史记录数: {tracker.history_count}")
print(f"平均压缩比: {tracker.get_average_compression_ratio():.2f}")
print(f"总节省 token: {tracker.get_total_tokens_saved()}")
print(f"压缩成功率: {tracker.get_success_rate():.1%}")
print(f"压缩效率: {tracker.get_compression_efficiency():.2%}")

# 获取最近 10 条记录
recent_history = tracker.get_history(limit=10)
for record in recent_history:
    print(f"  {record.timestamp}: {record.before_tokens} → {record.after_tokens} tokens")
```

### 禁用特定组件

```python
# 禁用熔断器（不推荐，仅用于调试）
compressor = ContextCompressor(
    model="qwen-turbo",
    enable_circuit_breaker=False,
)

# 禁用预算追踪器（减少内存占用）
compressor = ContextCompressor(
    model="qwen-turbo",
    enable_budget_tracker=False,
)

# 禁用验证器（跳过质量检查，加快压缩速度）
compressor = ContextCompressor(
    model="qwen-turbo",
    enable_validator=False,
)
```

### 自定义验证器参数

```python
# 自定义验证器：更严格的质量要求
compressor = ContextCompressor(
    model="qwen-turbo",
    validator_min_retention=0.7,  # 要求 70% 信息保留率
    validator_min_length=800,  # 摘要至少 800 字符
    validator_max_length=10000,  # 摘要最多 10000 字符
)
```

### 处理压缩结果

```python
result = compressor.compress(messages=messages, current_tokens=5000)

# 检查是否跳过压缩（熔断器 OPEN）
if result.get("skipped"):
    print(f"压缩被跳过: {result.get('reason')}")
else:
    # 使用压缩后的消息
    compressed_messages = result["messages"]
    
    # 检查验证结果
    validation = result.get("validation")
    if validation and not validation["is_valid"]:
        print(f"压缩质量警告: {validation['warnings']}")
    
    # 检查压缩效率
    efficiency = result.get("compression_efficiency", 0.0)
    print(f"压缩效率: {efficiency:.2%}")
```
