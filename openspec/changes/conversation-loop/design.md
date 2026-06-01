## 上下文

业界成熟的自进化 AI Agent 系统的对话循环模块 (~4300 LOC) 和错误分类器模块 (~1170 LOC) 实现了完整的对话循环和错误分类系统。核心设计决策包括：
- 同步对话循环，包含中断检查和迭代预算
- 错误分类学，提供结构化恢复策略
- 后台审查线程，fork Agent 评估对话
- 轨迹保存用于研究
- **EventBus 事件系统**：解耦循环逻辑与外部处理器（15 种事件类型）

## 技术方案

### 1. EventBus 事件系统

**设计理由：** 对话循环是 Agent 的核心枢纽，多个外部功能（UI 渲染、持久化存储、记忆同步、指标收集）需要感知循环内部状态。传统回调参数方式会导致循环接口膨胀且耦合严重。EventBus 提供发布-订阅模式，让外部功能按需订阅事件，循环内部只负责 emit 事件。

#### 事件类型体系

```python
class EventType(Enum):
    # === 生命周期事件 ===
    LOOP_START = "loop_start"          # 循环开始
    LOOP_END = "loop_end"              # 循环结束（含最终结果）
    ITERATION_START = "iteration_start"  # 每轮迭代开始
    ITERATION_END = "iteration_end"    # 每轮迭代结束

    # === 模型调用事件 ===
    MODEL_REQUEST = "model_request"    # 发送请求前（含完整请求体）
    MODEL_RESPONSE = "model_response"  # 收到响应后（含完整响应体）
    MODEL_ERROR = "model_error"        # 模型调用失败（含错误分类）
    MODEL_RETRY = "model_retry"        # 重试中（含重试次数）

    # === 工具事件 ===
    TOOL_START = "tool_start"          # 工具开始执行
    TOOL_END = "tool_end"              # 工具执行结束（含结果和耗时）
    TOOL_ERROR = "tool_error"          # 工具执行失败

    # === 消息事件 ===
    MESSAGE_APPEND = "message_append"  # 消息追加到历史

    # === 上下文事件 ===
    PRE_COMPRESS = "pre_compress"      # 上下文压缩前

    # === 控制事件 ===
    INTERRUPT = "interrupt"            # 循环被中断
    MAX_ITERATIONS = "max_iterations"  # 达到最大迭代次数
```

#### 事件数据规范

每个事件 emit 时携带标准化的 data 字典：

| 事件 | data 字段 |
|------|----------|
| `loop_start` | `messages`, `tools`, `max_iterations` |
| `loop_end` | `result`, `iterations`, `total_elapsed` |
| `iteration_start` | `iteration`, `messages` |
| `iteration_end` | `iteration`, `response` |
| `model_request` | `messages`, `tools`, `iteration` |
| `model_response` | `response`, `iteration`, `elapsed` |
| `model_error` | `error`, `classified`, `iteration` |
| `model_retry` | `error`, `attempt`, `iteration` |
| `tool_start` | `tool_name`, `tool_args`, `tool_call` |
| `tool_end` | `tool_name`, `tool_args`, `result`, `elapsed`, `tool_call` |
| `tool_error` | `tool_name`, `error`, `tool_call` |
| `message_append` | `message`, `messages` |
| `pre_compress` | `messages` |
| `interrupt` | `iteration` |
| `max_iterations` | `iterations` |

#### EventBus API

```python
class EventBus:
    def on(event_type, handler)       # 订阅事件
    def off(event_type, handler)      # 取消订阅
    def emit(event_type, data)        # 触发事件（异常隔离）
    def clear(event_type=None)        # 清除订阅
```

#### 使用示例

```python
# 创建循环
loop = ConversationLoop(model_call=caller, tool_dispatch=dispatch)

# 订阅事件（解耦方式）
loop.events.on(EventType.TOOL_START, ui.show_tool_start)
loop.events.on(EventType.TOOL_END, ui.show_tool_end)
loop.events.on(EventType.MODEL_RESPONSE, storage.save_turn)
loop.events.on(EventType.MESSAGE_APPEND, jsonl_store.append_message)
loop.events.on(EventType.MODEL_ERROR, metrics.record_error)

# 运行
result = loop.run(messages, tools)
```

### 2. 核心对话循环

```python
class ConversationLoop:
    def __init__(self, max_iterations=90, model_call=None, tool_dispatch=None, debug=False):
        self.max_iterations = max_iterations
        self._model_call = model_call
        self._tool_dispatch = tool_dispatch
        self._error_classifier = ErrorClassifier()
        self._interrupted = False
        self.debug = debug
        self.events = EventBus()  # 事件总线

    def run(self, messages, tools=None):
        iteration = 0
        start_time = time.time()

        self.events.emit(EventType.LOOP_START, {
            "messages": messages, "tools": tools, "max_iterations": self.max_iterations
        })

        while iteration < self.max_iterations:
            if self._interrupted:
                self.events.emit(EventType.INTERRUPT, {"iteration": iteration})
                break

            iteration += 1
            self.events.emit(EventType.ITERATION_START, {"iteration": iteration, "messages": messages})

            # 调用模型
            model_start = time.time()
            try:
                self.events.emit(EventType.MODEL_REQUEST, {"messages": messages, "tools": tools, "iteration": iteration})
                response = self._call_model(messages, tools)
                model_elapsed = time.time() - model_start
                self.events.emit(EventType.MODEL_RESPONSE, {"response": response, "iteration": iteration, "elapsed": model_elapsed})
            except Exception as e:
                classified = self._error_classifier.classify(getattr(e, "status_code", None), str(e))
                self.events.emit(EventType.MODEL_ERROR, {"error": e, "classified": classified, "iteration": iteration})
                if classified.retryable and iteration < self.max_iterations:
                    self.events.emit(EventType.MODEL_RETRY, {"error": e, "attempt": iteration, "iteration": iteration})
                    continue
                raise

            self.events.emit(EventType.ITERATION_END, {"iteration": iteration, "response": response})

            # 工具调用
            if response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    # ... 工具执行 + emit TOOL_START/TOOL_END/TOOL_ERROR ...
                    # ... emit MESSAGE_APPEND ...
                continue

            # 文本响应，结束循环
            total_elapsed = time.time() - start_time
            result = {"final_response": response.get("content", ""), "iterations": iteration, ...}
            self.events.emit(EventType.LOOP_END, {"result": result, "iterations": iteration, "total_elapsed": total_elapsed})
            return result

        # 达到最大迭代
        self.events.emit(EventType.MAX_ITERATIONS, {"iterations": iteration})
        return {"final_response": "[达到最大迭代次数]", ...}
```

### 3. 错误分类器

```python
class FailoverReason(Enum):
    auth = "auth"
    auth_permanent = "auth_permanent"
    billing = "billing"
    rate_limit = "rate_limit"
    overloaded = "overloaded"
    server_error = "server_error"
    timeout = "timeout"
    context_overflow = "context_overflow"
    payload_too_large = "payload_too_large"
    image_too_large = "image_too_large"
    model_not_found = "model_not_found"
    format_error = "format_error"
    unknown = "unknown"

class ErrorClassifier:
    def classify(self, status_code, message) -> ClassifiedError:
        msg = message.lower()

        # 认证错误
        if status_code in (401, 403):
            return ClassifiedError(reason=FailoverReason.auth, retryable=True, should_rotate_credential=True)

        # 计费/配额
        if status_code == 402 or any(p in msg for p in BILLING_PATTERNS):
            return ClassifiedError(reason=FailoverReason.billing, retryable=False, should_rotate_credential=True)

        # 速率限制
        if status_code == 429:
            return ClassifiedError(reason=FailoverReason.rate_limit, retryable=True, should_rotate_credential=True)

        # 上下文溢出
        if self._is_context_overflow(msg, status_code):
            return ClassifiedError(reason=FailoverReason.context_overflow, retryable=True, should_compress=True)

        return ClassifiedError(reason=FailoverReason.unknown, retryable=True)
```

### 4. 后台审查

```python
def spawn_background_review(parent_agent, conversation_snapshot):
    """在后台线程中 fork Agent 审查对话。"""
    def _review_task():
        review_agent = fork_agent(parent_agent, tool_whitelist=["memory", "skill_manage"], skip_memory=True)
        review_prompt = build_review_prompt(conversation_snapshot)
        result = review_agent.chat(review_prompt)
        logger.info("后台审查完成")

    thread = threading.Thread(target=_review_task, daemon=True)
    thread.start()
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| 错误分类不准确导致错误恢复策略 | 详细日志记录分类结果，便于调试 |
| 后台审查线程可能写入不正确的记忆 | 使用工具白名单，跳过共享记忆写入 |
| 对话循环中的重试可能导致无限循环 | 迭代预算和最大迭代次数限制 |
| EventBus 处理器异常可能影响循环 | emit 内部 try/except 隔离，处理器异常不传播 |
| 事件订阅过多导致性能下降 | 处理器应保持轻量，耗时操作异步化 |
| 事件数据字典过大导致内存压力 | 事件数据只包含必要字段，大对象传引用 |
