## ADDED Requirements

### Requirement: Reactive 压缩模式
系统 SHALL 支持 Reactive（响应式）压缩模式，基于 token 阈值触发。

#### Scenario: 达到阈值触发压缩
- **WHEN** 模式为 "reactive" 且 `current_tokens >= threshold * max_tokens`
- **THEN** `should_compress()` 返回 `True`

#### Scenario: 未达阈值不触发
- **WHEN** 模式为 "reactive" 且 `current_tokens < threshold * max_tokens`
- **THEN** `should_compress()` 返回 `False`

#### Scenario: 默认阈值
- **WHEN** 未指定 `reactive_threshold`
- **THEN** 默认阈值为 0.5（50%）

#### Scenario: 自定义阈值
- **WHEN** 指定 `reactive_threshold=0.8`
- **THEN** token 使用达到 80% 时触发压缩

### Requirement: Micro 压缩模式
系统 SHALL 支持 Micro（微压缩）模式，基于对话轮次触发。

#### Scenario: 达到轮次间隔触发压缩
- **WHEN** 模式为 "micro" 且当前轮次是 `micro_interval` 的倍数
- **THEN** `should_compress()` 返回 `True`

#### Scenario: 未达轮次间隔不触发
- **WHEN** 模式为 "micro" 且当前轮次不是 `micro_interval` 的倍数
- **THEN** `should_compress()` 返回 `False`

#### Scenario: 默认轮次间隔
- **WHEN** 未指定 `micro_interval`
- **THEN** 默认每 10 轮触发一次

#### Scenario: 自定义轮次间隔
- **WHEN** 指定 `micro_interval=5`
- **THEN** 每 5 轮触发一次压缩

### Requirement: Snip 压缩模式
系统 SHALL 支持 Snip（裁剪）模式，基于消息内容特征触发。

#### Scenario: 检测到长代码块触发压缩
- **WHEN** 模式为 "snip" 且消息包含匹配 `snip_patterns` 的内容
- **THEN** `should_compress()` 返回 `True`

#### Scenario: 未检测到特征不触发
- **WHEN** 模式为 "snip" 且消息不匹配任何 `snip_patterns`
- **THEN** `should_compress()` 返回 `False`

#### Scenario: 默认裁剪模式
- **WHEN** 未指定 `snip_patterns`
- **THEN** 默认模式为 ["```", "logs:", "output:", "traceback:"]

#### Scenario: 自定义裁剪模式
- **WHEN** 指定 `snip_patterns=["ERROR:", "WARNING:"]`
- **THEN** 检测到这些模式时触发压缩

### Requirement: 压缩模式配置
系统 SHALL 支持通过配置选择压缩模式。

#### Scenario: 初始化时指定模式
- **WHEN** 初始化 `ContextCompressor(mode="micro")`
- **THEN** 使用 Micro 压缩模式

#### Scenario: 默认模式
- **WHEN** 未指定 `mode`
- **THEN** 默认使用 "reactive" 模式

#### Scenario: 无效模式报错
- **WHEN** 指定 `mode="invalid"`
- **THEN** 抛出 `ValueError` 异常

### Requirement: 压缩模式查询
系统 SHALL 提供当前压缩模式查询接口。

#### Scenario: 查询当前模式
- **WHEN** 调用 `mode` 属性
- **THEN** 返回当前模式名称（"reactive"、"micro" 或 "snip"）
