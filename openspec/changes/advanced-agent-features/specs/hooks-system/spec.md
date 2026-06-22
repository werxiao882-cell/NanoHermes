## ADDED Requirements

### Requirement: EventBus 责任链拦截机制
系统 SHALL 在现有 EventBus 的 emit() 中增加责任链（Chain of Responsibility）拦截器模式。
拦截器签名为 `(data, next) -> None`，通过调用 `next()` 将控制权传递给下一个拦截器。
不调用 `next()` 表示阻断后续拦截器。拦截器链完成后（无论是否被阻断），再触发原有观察者（on() 注册的 handler）。

#### Scenario: 拦截器修改 data 并放行
- **WHEN** 拦截器在 MODEL_REQUEST 事件中修改 `data["messages"]` 并调用 `next()`
- **THEN** 后续拦截器和观察者 SHALL 看到修改后的 messages，ConversationLoop 使用修改后的数据调用模型

#### Scenario: 拦截器阻断流程（不调用 next）
- **WHEN** 拦截器不调用 `next()`
- **THEN** emit() SHALL 返回 `ChainResult(blocked=True)`，后续拦截器不再执行，但观察者仍然触发

#### Scenario: 拦截器前后置逻辑（洋葱模型）
- **WHEN** 拦截器在 `next()` 前后分别执行逻辑
- **THEN** 前置逻辑在下游拦截器之前执行，后置逻辑在下游拦截器完成之后执行

#### Scenario: 向后兼容 - 无拦截器时行为不变
- **WHEN** 某事件类型没有注册任何拦截器
- **THEN** emit() SHALL 直接触发观察者，行为与现有逻辑完全一致

### Requirement: 事件按 block 语义分类
系统 SHALL 将 18 种 EventType 按 block 语义分为三类：

1. **可阻断事件**（3 种）：MODEL_REQUEST, TOOL_START, ITERATION_END
   - ConversationLoop 检查 ChainResult.blocked，决定是否跳过对应操作
2. **可修改事件**（7 种）：MODEL_RESPONSE, TOOL_END, MESSAGE_APPEND, ITERATION_START, PRE_COMPRESS
   - 拦截器可修改 data dict，ConversationLoop 从 data 读回修改后的值
   - block 信号无效（操作已发生）
3. **仅观察事件**（8 种）：LOOP_START, LOOP_END, INTERRUPT, MAX_ITERATIONS, MODEL_ERROR, MODEL_RETRY, TOOL_ERROR, DELEGATION_*
   - 拦截器可注册但 block 信号无效（已发生的事实）

#### Scenario: MODEL_REQUEST 拦截阻断模型调用
- **WHEN** MODEL_REQUEST 事件的拦截链返回 `blocked=True`
- **THEN** ConversationLoop SHALL 跳过模型调用，将 block_message 作为 assistant 响应注入

#### Scenario: TOOL_START 拦截阻断工具执行
- **WHEN** TOOL_START 事件的拦截链返回 `blocked=True`
- **THEN** ConversationLoop SHALL 跳过工具执行，将 block_message 作为工具错误结果返回

#### Scenario: ITERATION_END 拦截阻断下一轮（STOP 语义）
- **WHEN** ITERATION_END 事件的拦截链返回 `blocked=True`
- **THEN** ConversationLoop SHALL 触发 LOOP_END 事件并结束循环，将 block_message 作为最终响应

#### Scenario: 仅观察事件的 block 信号被忽略
- **WHEN** LOOP_END 事件的拦截器不调用 `next()`
- **THEN** emit() SHALL 返回 `ChainResult(blocked=True)`，但 ConversationLoop 忽略该信号

### Requirement: 拦截器阻断后观察者仍触发
系统 SHALL 保证拦截器链中某个拦截器阻断后，所有观察者（on() 注册的 handler）仍然触发。
观察者负责持久化、日志等副作用，不应因拦截器阻断而跳过。

#### Scenario: MODEL_REQUEST 被阻断后观察者仍记录
- **WHEN** 拦截器阻断 MODEL_REQUEST
- **THEN** ConversationEventHandler 和 DebugHandler 的 MODEL_REQUEST 观察者 SHALL 仍然触发

### Requirement: 拦截器优先级排序
系统 SHALL 支持拦截器注册时指定 `priority`（整数，默认 0），emit() 时按 priority 升序构建责任链。相同 priority 按注册顺序排列。

#### Scenario: 多拦截器按优先级执行
- **WHEN** 注册了 priority=10 的 A 和 priority=1 的 B
- **THEN** 责任链顺序 SHALL 为 B → A（priority 小的先执行）

### Requirement: 拦截器故障隔离
系统 SHALL 保证单个拦截器执行失败不影响其他拦截器和主流程。

#### Scenario: 拦截器抛出异常
- **WHEN** 某个拦截器抛出异常
- **THEN** 系统 SHALL 捕获异常，记录 warning 日志，跳过该拦截器继续执行下一个

#### Scenario: 拦截器调用 next() 后抛出异常
- **WHEN** 拦截器调用 `next()` 后在后续逻辑中抛出异常
- **THEN** 系统 SHALL 捕获异常，链已正常执行完毕，不影响观察者触发

### Requirement: 危险命令拦截 Hook 实现
系统 SHALL 提供危险命令拦截 Hook 实现，复用 terminal.py 已有的 DANGEROUS_PATTERNS 检测逻辑，
在 TOOL_START 事件上注册为拦截器，阻断危险命令执行。

#### Scenario: 危险命令被拦截
- **WHEN** 模型调用 terminal 工具执行 `rm -rf /tmp/test`
- **THEN** dangerous_command_guard 拦截器 SHALL 匹配危险模式，不调用 `next()`
- **AND** emit() SHALL 返回 `ChainResult(blocked=True, message="危险命令被拦截: 递归删除 (rm -rf)")`
- **AND** ConversationLoop SHALL 跳过工具执行，返回错误结果

#### Scenario: 安全命令放行
- **WHEN** 模型调用 terminal 工具执行 `ls -la`
- **THEN** dangerous_command_guard 拦截器 SHALL 不匹配任何危险模式，调用 `next()`
- **AND** 工具正常执行

#### Scenario: 非 terminal 工具不拦截
- **WHEN** 模型调用 read_file 工具
- **THEN** dangerous_command_guard 拦截器 SHALL 直接调用 `next()`，不进行检测

#### Scenario: 拦截后观察者仍触发
- **WHEN** dangerous_command_guard 拦截了 terminal 工具
- **THEN** ConversationEventHandler._on_tool_start 观察者 SHALL 仍然触发
- **AND** TUI SHALL 显示工具执行记录（含拦截标识）

### Requirement: ScriptHook 外部脚本执行
系统 SHALL 提供 ScriptHook 包装类，将外部脚本封装为 EventBus 拦截器。

#### Scenario: 脚本 hook 正常执行并放行
- **WHEN** 脚本 stdout 输出 `{}` 或 `{"block": false}`
- **THEN** ScriptHook SHALL 调用 `next()` 继续责任链

#### Scenario: 脚本 hook 阻断
- **WHEN** 脚本 stdout 输出 `{"block": true, "message": "Lint check failed"}`
- **THEN** ScriptHook SHALL 不调用 `next()`，设置 `blocked=True`

#### Scenario: 脚本 hook 执行超时
- **WHEN** 脚本执行超过配置的 timeout（默认 30 秒）
- **THEN** 系统 SHALL 终止脚本进程，记录超时错误，调用 `next()` 放行

#### Scenario: 脚本 hook 执行失败或输出非法 JSON
- **WHEN** 脚本返回非零退出码或 stdout 非法 JSON
- **THEN** 系统 SHALL 记录错误日志，调用 `next()` 放行

### Requirement: Hook 配置加载
系统 SHALL 支持从 settings（nanohermes.json）加载 hook 配置，自动注册到 EventBus。

#### Scenario: 从 settings 加载脚本 hook
- **WHEN** settings 包含 `hooks.model_request = [{"type": "script", "path": "./validate.sh", "timeout": 30}]`
- **THEN** 系统 SHALL 创建 ScriptHook 并注册为 MODEL_REQUEST 事件的拦截器

#### Scenario: 从 settings 加载 Python hook
- **WHEN** settings 包含 `hooks.tool_start = [{"type": "python", "module": "my_hooks", "function": "check", "priority": 5}]`
- **THEN** 系统 SHALL 动态导入模块函数并注册为 TOOL_START 事件的拦截器

### Requirement: 委托架构中的拦截器作用域
系统 SHALL 保证拦截器仅作用于其注册的 EventBus 实例。

#### Scenario: 父级拦截器不影响子 Agent 内部流程
- **WHEN** 父级 EventBus 注册了 TOOL_START 拦截器
- **THEN** 子 Agent 内部的 TOOL_START（在子 Agent 独立 EventBus 上）SHALL 不受影响
- **AND** 从子 Agent 转发到父级 EventBus 的 TOOL_START（含 child_task_id）SHALL 触发父级拦截器

#### Scenario: 子 Agent 转发事件被父级拦截
- **WHEN** 父级拦截器阻断了转发的 TOOL_START
- **THEN** 父级观察者（TUI）SHALL 仍触发（看到子 Agent 工具执行），但拦截器链中后续拦截器不执行
