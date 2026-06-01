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

**为什么长对话是个工程问题：** LLM 上下文窗口有限（128K-200K tokens），30 次工具调用可能消耗 80K+ tokens，超限会返回 `context_length_exceeded` 错误。

NanoHermes 使用 Python 实现相同的功能。

## 目标 / 非目标

**目标：**
- 实现 ContextEngine 抽象基类（可插拔扩展点）
- 实现完整的 ContextCompressor 压缩引擎
- 实现辅助 LLM 客户端配置和可行性检查
- 实现工具输出剪枝
- 实现会话分割和 ID 轮换（Session Splitting + parent_session_id 血缘链）
- 实现 `on_pre_compress` 钩子通知 Memory Provider

**非目标：**
- 不实现图像大小调整恢复（try_shrink_image_parts_in_messages）
- 不实现手动压缩反馈（manual_compression_feedback）
- 不实现外部 ContextEngine 插件（LCM、自定义摘要引擎）— 预留接口

## 技术方案

### 1. ContextEngine 抽象基类

**技术方案：** 使用 Python 抽象基类定义可插拔上下文引擎接口。

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class ContextEngine(ABC):
    """可插拔上下文引擎抽象基类。

    第三方引擎（如 LCM、自定义摘要引擎）可替换内置压缩器，
    只需在配置中指定 context.engine。
    """

    @abstractmethod
    def update_from_response(self, response: Dict[str, Any]) -> None:
        """在每次模型响应后更新引擎内部状态（如 token 使用量追踪）。"""
        ...

    @abstractmethod
    def should_compress(self) -> bool:
        """判断当前上下文是否需要压缩。"""
        ...

    @abstractmethod
    def compress(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行实际的压缩操作。

        Args:
            messages: 当前对话消息列表。

        Returns:
            压缩结果，包含压缩后的消息列表、摘要文本等。
        """
        ...

    # 可选生命周期钩子
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回引擎定义的工具 schema（如 recall_context 工具）。"""
        return []

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        """处理引擎定义的工具调用。"""
        raise NotImplementedError(f"Engine does not handle tool {tool_name}")
```

**设计决策：** 内置的 `ContextCompressor` 完整实现这个 ABC。用户可以通过配置切换引擎，而编排层（`AIAgent`）只面向 `ContextEngine` 接口编程。

### 2. ContextCompressor 上下文压缩引擎

```python
class ContextCompressor(ContextEngine):
    def __init__(self, model: str, threshold_percent: float = 0.50,
                 protect_first_n: int = 3, protect_last_n: int = 20,
                 summary_target_ratio: float = 0.20, ...):
        self.context_length = get_model_context_length(model, ...)
        self.threshold_tokens = int(self.context_length * threshold_percent)
        self.tail_token_budget = int(self.threshold_tokens * summary_target_ratio)
        self._previous_summary: Optional[str] = None  # 迭代更新
```

**参数配置：**

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `threshold_percent` | 0.50 | 使用达到 50% 上下文时触发压缩 |
| `protect_first_n` | 3 | 保护前 3 条消息（通常是 system + 第一轮对话） |
| `protect_last_n` | 20 | 保护最后 20 条消息 |
| `summary_target_ratio` | 0.20 | 尾部保护预算占阈值的 20% |

**触发时机：**
1. **预飞行**（`run_agent.py:7000-7049`）：进入主循环前，估算 token 数，如超阈值立即压缩
2. **响应后**（主循环内）：API 返回 `context_length_exceeded` 或 `usage.prompt_tokens` 超阈值时压缩

### 3. 分层压缩策略

```
消息列表: [sys, u1, a1, u2, a2, tool1, u3, a3, ..., u20, a20]
                |←  head 保护 →|                        |←  tail 保护  →|
                    (前 3 条)                              (最后 20 条)
                                  |←     middle 区域     →|
                                      ↓ 这部分被摘要
```

**第 1 步：Tool Output Pruning（廉价，无 LLM 调用）**
```python
def _prune_old_tool_results(self, messages, protect_tail_count):
    """Replace old tool result contents with a short placeholder."""
    pruned = 0
    for i in range(len(messages) - protect_tail_count):
        msg = messages[i]
        if msg.get("role") == "tool" and len(msg.get("content", "")) > 200:
            msg["content"] = "[Tool result pruned — original too large]"
            pruned += 1
    return messages, pruned
```

**第 2 步：Head/Tail 保护**
- Head 保护前 3 条消息（system prompt + 第一轮对话——建立上下文的关键）
- Tail 保护最后 20 条消息（最近的对话上下文）
- Middle 区域是压缩目标

**第 3 步：结构化摘要**
```python
# 摘要模板关键字段
# Goal: 对话的主要目标
# Progress: 完成了什么
# Key Decisions: 做出的重要决策
# Modified Files: 修改过的文件及原因
# Next Steps: 下一步计划
```

**第 4 步：Session Splitting**
1. 新 session 的 `parent_session_id` 指向旧 session（建立血缘链）
2. 摘要作为新 session 的第一条消息
3. 尾部保护的消息搬到新 session
4. 新 session 获得新的 IterationBudget

### 4. 迭代摘要更新

```python
self._previous_summary: Optional[str] = None
```

如果之前已经有过一次压缩，`_previous_summary` 存储了上一次的摘要。新一次压缩不是从零开始，而是**更新**已有摘要：

```python
def _build_summary_prompt(self, middle_messages, previous_summary):
    if previous_summary:
        # 更新已有摘要
        return f"Previous summary:\n{previous_summary}\n\nUpdate with new information..."
    else:
        # 首次摘要
        return "Summarize the following conversation..."
```

这让多次压缩后的摘要仍然保持连贯——不会丢失早期的重要信息。

### 5. 工具输出剪枝

```python
def prune_tool_outputs(self, messages: List[Dict]) -> List[Dict]:
    pruned = []
    for msg in messages:
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > 200:
                msg = {**msg, "content": "[Tool result pruned — original too large]"}
        pruned.append(msg)
    return pruned

def truncate_tool_call_args(args_json: str, head_chars: int = 200) -> str:
    """截断工具调用参数，保持 JSON 有效性。"""
    try:
        parsed = json.loads(args_json)
        truncated = _truncate_object_strings(parsed, head_chars)
        return json.dumps(truncated)
    except json.JSONDecodeError:
        return args_json  # 不是有效 JSON，返回原始字符串

def _truncate_object_strings(obj: Any, max_chars: int) -> Any:
    """递归截断对象中的字符串叶子节点。"""
    if isinstance(obj, str):
        return obj[:max_chars] + "...[truncated]" if len(obj) > max_chars else obj
    elif isinstance(obj, list):
        return [_truncate_object_strings(item, max_chars) for item in obj]
    elif isinstance(obj, dict):
        return {k: _truncate_object_strings(v, max_chars) for k, v in obj.items()}
    return obj
```

**关键设计决策：** 工具调用参数截断必须保持 JSON 有效性。早期实现直接切片原始 JSON 字符串，导致未终止的字符串和缺失的闭合括号，使 MiniMax 等提供商返回 400 错误。新实现解析 JSON，截断字符串叶子节点，重新序列化。

### 6. 辅助客户端可行性检查

```python
def check_compression_model_feasibility(agent_config: Dict) -> Dict:
    aux_model = resolve_aux_model("compression")
    aux_context_length = get_model_context_length(aux_model)
    main_compression_threshold = agent_config["context_length"] * 0.8

    if aux_context_length < MINIMUM_CONTEXT_LENGTH:
        return {
            "feasible": False,
            "reason": f"辅助模型上下文窗口 ({aux_context_length}) 小于最小要求 ({MINIMUM_CONTEXT_LENGTH})"
        }

    if aux_context_length < main_compression_threshold:
        return {
            "feasible": True,
            "warning": f"辅助模型上下文窗口 ({aux_context_length}) 小于主模型压缩阈值 ({main_compression_threshold})，压缩可能失败"
        }

    return {"feasible": True}
```

### 7. Memory Provider 的 on_pre_compress 钩子

压缩发生前，`MemoryManager` 会通知外部 memory provider：

```python
def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
    """Extract information from messages before they are compressed away."""
    return ""
```

Provider 可以在消息被压缩丢弃前提取有价值的信息——比如 Honcho 可以从即将被压缩的对话中提取用户偏好变更，确保信息不会在压缩中丢失。

### 8. 压缩对 Prompt Cache 的影响

压缩触发 session splitting 后，system prompt 需要重建（因为新 session 的 system prompt 需要包含摘要）。这意味着 Anthropic 的 prompt cache 会 miss 一次。

但这是可接受的代价——压缩本身就意味着对话已经很长（消耗了 50%+ 上下文窗口），此时一次 cache miss 的成本远小于 `context_length_exceeded` 错误导致的对话中断。

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| 辅助 LLM 调用增加成本 | 使用小型/快速模型，配置可调节压缩阈值 |
| 摘要丢失重要信息 | 结构化摘要模板跟踪目标/进展/关键决策 |
| 迭代摘要可能累积错误 | 每次压缩保留前次摘要内容并合并新信息 |
| 压缩触发 prompt cache miss | 可接受代价，远小于 context_length_exceeded 错误 |
| 工具参数截断破坏 JSON | 解析 JSON 后截断字符串叶子节点，重新序列化 |

## 设计启示

上下文压缩展示了"渐进式降级"的设计哲学：

1. **先做廉价操作**：tool output pruning 不需要 LLM 调用，可能就够了
2. **保护两端**：Head（建立上下文）和 Tail（最近对话）比 Middle 更重要
3. **摘要而非截断**：LLM 生成的结构化摘要保留了关键决策和上下文
4. **迭代更新**：多次压缩不会丢失早期信息

### 设计哲学：情景记忆——首次印象和当前状态是神圣的

压缩算法的 head/tail 保护揭示了一种特定的记忆理论：前几轮交互建立了上下文和意图（`protect_first_n=3`，硬编码），最近的交互包含当前活跃的工作状态（`protect_last_n` 由 token 预算动态决定），中间的一切都是可替换的。这与人类的**情景记忆**一致——我们记住开头和结尾，不记得中间。中间部分可以被摘要，因为它的目的是**到达**当前状态，而不是**成为**当前状态。

这些策略让 Hermes 可以维持超过 100 轮的长对话而不崩溃，也不丢失关键上下文。
