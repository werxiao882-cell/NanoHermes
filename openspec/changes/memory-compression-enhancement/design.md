## Context

NanoHermes 的上下文压缩系统（`src/compression/compressor.py`）已实现基础的分层压缩策略：
- Tool Output Pruning（工具输出裁剪）
- Head/Tail Protection（首尾保护）
- Middle Summarization（中间摘要）
- Session Splitting（会话分裂）

当前系统存在以下问题：
1. **压缩失败无保护**：连续压缩失败时容易进入循环重试，缺乏熔断机制
2. **缺乏可观测性**：无法追踪压缩效率、token 使用趋势和历史统计
3. **触发模式单一**：仅支持阈值触发（50%），无法适应不同场景需求
4. **质量无验证**：压缩后无法评估信息保留度和摘要质量

## Goals / Non-Goals

**Goals:**
- 实现熔断器模式，防止压缩循环，支持自动降级和恢复
- 实现动态预算追踪，监控压缩效率和 token 使用情况
- 实现多种压缩触发模式（Reactive/Micro/Snip），适应不同场景
- 实现压缩质量验证，评估信息保留度和摘要质量
- 保持向后兼容，不破坏现有 API

**Non-Goals:**
- 不实现自适应压缩算法（如基于内容类型的智能压缩）
- 不实现分布式压缩（多节点协同压缩）
- 不实现压缩结果的持久化存储（仅内存追踪）
- 不实现压缩 UI 可视化（仅提供 API 接口）

## Decisions

### 1. 熔断器状态机设计

**决策**：采用三状态熔断器（CLOSED → OPEN → HALF_OPEN → CLOSED）

**理由**：
- CLOSED：正常状态，允许压缩
- OPEN：熔断状态，拒绝压缩请求，防止循环
- HALF_OPEN：探测状态，允许单次压缩尝试，成功则恢复，失败则继续熔断

**替代方案**：
- 简单计数器：无法区分临时故障和持续故障
- 时间窗口：实现复杂，需要维护滑动窗口

**关键参数**：
- `failure_threshold=3`：连续 3 次失败后熔断
- `cooldown_seconds=60`：熔断后 60 秒进入探测状态
- `success_threshold=1`：探测状态 1 次成功即恢复

### 2. 预算追踪数据结构

**决策**：使用环形缓冲区（Ring Buffer）存储压缩历史

**理由**：
- 固定内存占用（默认保留最近 100 次压缩记录）
- 自动淘汰旧数据，无需手动清理
- 支持快速计算滑动窗口统计（平均效率、成功率）

**替代方案**：
- 列表 + 定期清理：需要额外的清理逻辑
- 数据库持久化：增加复杂度，当前场景不需要

**关键指标**：
- `compression_ratio`：压缩比（压缩后 tokens / 压缩前 tokens）
- `tokens_saved`：节省的 token 数
- `success_rate`：压缩成功率
- `average_duration_ms`：平均压缩耗时

### 3. 压缩模式触发策略

**决策**：实现三种独立的触发模式，由配置选择

**模式设计**：

1. **Reactive（响应式）**：当前默认模式
   - 触发条件：`current_tokens >= threshold * max_tokens`
   - 适用场景：长对话，token 接近上限时触发
   - 优点：简单直观，节省计算资源
   - 缺点：可能突然触发，用户感知明显

2. **Micro（微压缩）**：频繁小压缩
   - 触发条件：每 N 轮对话后（默认 N=10）
   - 压缩范围：仅压缩中间部分，保留更多首尾
   - 适用场景：持续对话，保持上下文流畅
   - 优点：用户感知平滑，避免大压缩
   - 缺点：压缩频率高，增加计算开销

3. **Snip（裁剪）**：精准裁剪
   - 触发条件：检测到特定类型的长消息（如大段代码、日志）
   - 压缩范围：仅裁剪特定消息，不影响其他内容
   - 适用场景：工具输出过长，需要精准裁剪
   - 优点：精准控制，保留对话连贯性
   - 缺点：需要消息分类逻辑

**配置方式**：
```python
compressor = ContextCompressor(
    mode="reactive",  # or "micro", "snip"
    reactive_threshold=0.5,
    micro_interval=10,
    snip_patterns=["```", "logs:", "output:"]
)
```

### 4. 压缩质量验证策略

**决策**：实现轻量级验证器，基于关键词匹配和长度检查

**验证维度**：

1. **信息保留度**（Information Retention）
   - 提取原始消息和摘要的关键词集合
   - 计算 Jaccard 相似度：`|A ∩ B| / |A ∪ B|`
   - 阈值：保留率 >= 0.6（60%）

2. **摘要长度**（Summary Length）
   - 最小长度：500 字符（避免过度压缩）
   - 最大长度：12000 字符（避免摘要过长）

3. **关键信息完整性**（Key Information）
   - 检查是否包含文件变更（"file", "修改", "create"）
   - 检查是否包含用户意图（最近 5 条用户消息）
   - 检查是否包含工具调用（"tool", "function"）

**替代方案**：
- LLM 评估：准确但成本高，增加延迟
- 语义相似度：需要嵌入模型，增加依赖

**验证时机**：压缩完成后立即验证，失败则回滚

### 5. 集成方式

**决策**：在 `ContextCompressor` 中组合使用各组件

**集成点**：

```python
class ContextCompressor(ContextEngine):
    def __init__(self, ...):
        self._circuit_breaker = CircuitBreaker()
        self._budget_tracker = BudgetTracker()
        self._validator = CompressionValidator()
    
    def compress(self, messages, current_tokens=None, **kwargs):
        # 1. 检查熔断器
        if not self._circuit_breaker.can_compress():
            return {"messages": messages, "skipped": True, "reason": "circuit_breaker_open"}
        
        # 2. 执行压缩
        try:
            before_tokens = current_tokens or self._estimate_tokens(messages)
            result = self._do_compress(messages, current_tokens, **kwargs)
            after_tokens = self._estimate_tokens(result["messages"])
            
            # 3. 追踪预算
            self._budget_tracker.track_compression(before_tokens, after_tokens)
            
            # 4. 验证质量
            validation = self._validator.validate(messages, result["messages"], result["summary"])
            if not validation["is_valid"]:
                # 质量不达标，回滚
                self._circuit_breaker.record_failure()
                return {"messages": messages, "rolled_back": True, "validation": validation}
            
            # 5. 记录成功
            self._circuit_breaker.record_success()
            result["compression_efficiency"] = self._budget_tracker.get_compression_efficiency()
            result["circuit_breaker_state"] = self._circuit_breaker.state
            result["validation"] = validation
            return result
            
        except Exception as e:
            self._circuit_breaker.record_failure()
            return {"messages": messages, "error": str(e)}
```

## Risks / Trade-offs

### 1. 熔断器误判风险
- **风险**：临时网络问题导致熔断器开启，后续压缩请求被拒绝
- **缓解**：冷却期机制（60 秒）自动进入探测状态，单次成功即可恢复

### 2. 预算追踪内存占用
- **风险**：长时间运行的会话积累大量压缩历史
- **缓解**：环形缓冲区固定大小（100 条），自动淘汰旧数据

### 3. 压缩模式选择复杂度
- **风险**：用户不知道选择哪种模式
- **缓解**：提供默认配置（Reactive），文档说明各模式适用场景

### 4. 质量验证准确性
- **风险**：关键词匹配可能误判（如代码注释包含"file"但不是文件变更）
- **缓解**：验证失败时记录警告而非强制回滚，允许用户配置阈值

### 5. 性能开销
- **风险**：验证器和追踪器增加压缩耗时
- **缓解**：验证器使用轻量级关键词匹配（< 10ms），追踪器使用 O(1) 环形缓冲区

## Migration Plan

### 部署步骤
1. 新增组件文件（`circuit_breaker.py`、`budget_tracker.py`、`validator.py`）
2. 修改 `compressor.py` 集成各组件
3. 更新 `__init__.py` 导出新组件
4. 添加单元测试
5. 更新文档（ARCHITECTURE.md）

### 回滚策略
- 各组件独立实现，可通过配置禁用（如 `enable_circuit_breaker=False`）
- 保持 `compress()` 方法签名不变，仅扩展返回字段
- 新增字段为可选，不影响现有调用方

## Open Questions

（无待解决问题）
