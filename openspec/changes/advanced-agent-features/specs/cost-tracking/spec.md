## ADDED Requirements

### Requirement: Real-time cost accumulation
系统 SHALL 在每次 API 调用后，根据模型定价和 token 使用量（input/output/cache_read/cache_write）计算成本，累加到当前会话的总成本中。

#### Scenario: API 调用后累加成本
- **WHEN** API 调用返回 usage 信息（input_tokens: 5000, output_tokens: 1000）
- **THEN** 系统 SHALL 根据当前模型的定价计算成本，累加到会话总成本

#### Scenario: 多模型分别计价
- **WHEN** 会话中使用了主模型（对话）和辅助模型（压缩摘要）
- **THEN** 系统 SHALL 分别记录每个模型的成本，并在总成本中汇总

### Requirement: StatusBar cost display
系统 SHALL 在 TUI StatusBar 中实时显示当前会话的累计成本，格式为 `$X.XX`。

#### Scenario: StatusBar 显示会话成本
- **WHEN** 当前会话累计成本为 $0.15
- **THEN** StatusBar SHALL 显示 `$0.15` 标识

### Requirement: Per-model usage breakdown
系统 SHALL 记录每个模型的使用明细（调用次数、input tokens、output tokens、成本），支持通过 `/cost` 命令查看详细分类。

#### Scenario: 查看模型使用明细
- **WHEN** 用户执行 `/cost` 命令
- **THEN** 系统 SHALL 显示每个模型的调用次数、token 使用量和成本明细

### Requirement: Budget limit warning
系统 SHALL 支持通过配置设置会话预算上限（`maxBudgetUsd`），当累计成本接近或超过预算时发出警告。

#### Scenario: 成本超过预算发出警告
- **WHEN** 累计成本超过 `maxBudgetUsd` 的 90%
- **THEN** 系统 SHALL 在 StatusBar 显示预算警告，并在下次 API 调用前提示用户

### Requirement: Cost persistence across resume
系统 SHALL 将会话成本数据持久化到 SessionDB，恢复会话时自动加载历史成本。

#### Scenario: 恢复会话时加载历史成本
- **WHEN** 用户通过 `--resume` 恢复之前的会话
- **THEN** 系统 SHALL 从 SessionDB 加载该会话的历史成本数据，StatusBar 显示累计成本
