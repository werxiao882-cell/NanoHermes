# 上下文压缩模块 (src/compression)

## 模块概述

可插拔的上下文管理系统，解决 LLM 上下文窗口有限的核心问题。采用分层压缩策略：
工具输出剪枝（廉价）→ 头尾保护（情景记忆理论）→ 中间摘要（LLM 生成）→ Session Splitting（终极手段）。

## 文件职责

| 文件 | 职责 |
|------|------|
| `__init__.py` | 模块导出，统一公共 API |
| `engine.py` | `ContextEngine` 抽象基类，定义可插拔引擎接口（3 个抽象方法 + 可选工具接口） |
| `compressor.py` | `ContextCompressor` 分层压缩引擎，继承 ContextEngine，协调所有子组件 |
| `auxiliary.py` | `get_model_context_length()` 模型上下文窗口查询（硬编码映射表） |
| `pruning.py` | `prune_tool_outputs()` 工具输出剪枝 + `truncate_tool_call_args()` 参数截断（保持 JSON 有效性） |
| `feasibility.py` | `check_compression_model_feasibility()` 压缩可行性检查 |
| `circuit_breaker.py` | `CircuitBreaker` 熔断器，CLOSED→OPEN→HALF_OPEN 三状态，防止压缩循环 |
| `budget_tracker.py` | `BudgetTracker` 环形缓冲区记录压缩历史，计算效率/成功率/节省 token |
| `validator.py` | `CompressionValidator` 压缩质量验证（Jaccard 相似度 + 摘要长度 + 关键信息检查） |
| `modes.py` | 三种压缩触发策略：`ReactiveMode`（token 阈值）、`MicroMode`（轮次间隔）、`SnipMode`（内容特征匹配） |

## 核心数据流

```
ConversationLoop
    │
    ├── should_compress(messages, current_tokens)
    │       │
    │       ├── CircuitBreaker.can_compress() ── OPEN → 拒绝
    │       └── CompressionMode.should_compress() ── 根据模式判断
    │
    └── compress(messages, model_caller)
            │
            ├── on_pre_compress 回调 → MemoryProvider 提取关键信息
            │
            ├── _protect_head(messages)          → 前 3 条（首因效应）
            ├── _protect_tail(messages)          → 尾部 token 预算内（近因效应）
            ├── _get_middle(head, tail)          → 中间可压缩部分
            │
            ├── prune_tool_outputs(middle)       → 替换长工具输出为占位符
            ├── _calculate_summary_budget(chars) → max(2000, min(chars*0.20/4, 12000))
            ├── _generate_summary(pruned, budget, model_caller) → 结构化摘要
            │
            ├── CompressionValidator.validate()  → 信息保留率 + 长度 + 关键信息
            ├── BudgetTracker.track_compression()→ 记录压缩统计
            ├── CircuitBreaker.record_success/failure() → 更新熔断状态
            │
            └── 返回: [head] + [summary system msg] + [tail]
```

## 关键设计决策

### 分层压缩而非简单截断
截断会丢失关键信息。分层策略按成本递增执行：剪枝（无 LLM 调用）→ 头尾保护 → LLM 摘要 → Session Splitting，每层平衡信息保留与 token 消耗。

### 头尾保护基于情景记忆理论
- 头部 3 条：system prompt + 初始意图，是对话"锚点"（首因效应）
- 尾部用 token 预算而非固定条数：消息长度差异大，固定条数可能导致预算失控

### 复用主对话 model_caller 生成摘要
无需独立辅助 LLM 客户端和凭证管理，保证摘要与主对话使用相同模型的理解能力。失败时返回占位符而非抛异常——压缩是优化而非必需。

### 熔断器防止级联故障
连续 3 次失败后自动断开（OPEN），60 秒冷却后进入探测（HALF_OPEN），单次成功即恢复（CLOSED）。借鉴电路保险丝理念，避免压缩循环消耗资源。

### 环形缓冲区追踪预算
`deque(maxlen=100)` 固定内存占用，自动淘汰旧数据。提供压缩效率综合指标：`(1 - 平均压缩比) × 成功率`。

### 三种压缩模式适应不同场景
- **Reactive**：token 使用率达阈值触发，简单直观，适合长对话；含 80% 紧急阈值
- **Micro**：每 N 轮触发，频繁小压缩，用户感知平滑，适合持续对话
- **Snip**：正则匹配代码块/日志/traceback 等长内容时触发，精准裁剪

### 工具调用参数截断保持 JSON 有效性
早期实现直接切片 JSON 字符串导致 400 错误。现改为：解析 JSON → 截断字符串叶子节点 → 重新序列化。

### 验证失败不回滚
验证失败仅记录警告，不回滚压缩结果。原因：回滚会导致压缩循环，验证失败仍比不压缩好。

## 对外接口

### 公共类
- `ContextEngine` — 抽象基类，第三方引擎可替换内置压缩器
- `ContextCompressor` — 主压缩引擎，提供 `should_compress()` / `compress()` / `split_session()`
- `CircuitBreaker` / `CircuitState` — 熔断器及状态枚举
- `BudgetTracker` / `CompressionRecord` — 预算追踪器及记录数据类
- `CompressionValidator` / `ValidationResult` — 压缩验证器及结果数据类
- `CompressionMode` / `BaseCompressionMode` / `ReactiveMode` / `MicroMode` / `SnipMode` — 压缩模式体系

### 公共函数
- `get_model_context_length(model)` — 查询模型上下文窗口
- `prune_tool_outputs(messages)` — 剪枝工具输出
- `truncate_tool_call_args(args_json, max_chars)` — 截断工具调用参数
- `check_compression_model_feasibility(model, main_context_length)` — 压缩可行性检查
- `create_mode(mode_name, ...)` — 压缩模式工厂函数

### 回调接口（ContextCompressor 实例方法）
- `compressor.set_session_split_callback(callback)` — Session Splitting 通知回调
- `compressor.set_pre_compress_callback(callback)` — 压缩前信息提取回调（MemoryProvider 钩子）

## 依赖关系

- **src/ 内部**：无直接导入其他 src/ 模块（自包含模块）
- **外部**：仅依赖 Python 标准库（`json`, `re`, `time`, `uuid`, `collections`, `dataclasses`, `enum`, `abc`, `logging`）
