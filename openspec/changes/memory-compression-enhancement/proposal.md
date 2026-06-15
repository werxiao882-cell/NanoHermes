## Why

NanoHermes 的上下文压缩系统已实现基础的分层压缩策略，但缺乏生产级稳定性和可观测性。当前系统在压缩失败时容易进入循环重试，无法追踪压缩效率，且只支持单一的阈值触发模式。需要增强压缩系统的健壮性、可观测性和灵活性。

## What Changes

- 新增熔断器模式（Circuit Breaker）防止压缩循环，连续失败后自动降级
- 新增动态预算追踪（Budget Tracker）监控压缩效率和 token 使用情况
- 新增多种压缩触发模式：Reactive（响应式）、Micro（微压缩）、Snip（裁剪）
- 新增压缩质量验证器（Validator）评估信息保留度和摘要质量
- 修改 `src/compression/compressor.py` 集成熔断器和预算追踪
- 新增 `src/compression/circuit_breaker.py` 实现熔断器状态机
- 新增 `src/compression/budget_tracker.py` 实现预算追踪
- 新增 `src/compression/validator.py` 实现压缩质量评估

## Capabilities

### New Capabilities

- `circuit-breaker`: 熔断器模式实现，防止压缩循环，支持 CLOSED/OPEN/HALF_OPEN 状态转换和冷却期机制
- `budget-tracker`: 动态预算追踪，监控压缩前后 token 使用量、压缩效率和历史统计
- `compression-modes`: 多种压缩触发模式，包括 Reactive（阈值触发）、Micro（频繁小压缩）、Snip（精准裁剪）
- `compression-validator`: 压缩质量验证，评估信息保留度、摘要长度和关键信息完整性

### Modified Capabilities

（无现有能力需要修改）

## Impact

- 修改文件：`src/compression/compressor.py`（集成熔断器和预算追踪）
- 新增文件：`src/compression/circuit_breaker.py`、`src/compression/budget_tracker.py`、`src/compression/validator.py`
- 测试文件：`tests/compression/test_circuit_breaker.py`、`tests/compression/test_budget_tracker.py`、`tests/compression/test_validator.py`
- 依赖：无新增外部依赖
- API：`ContextCompressor.compress()` 返回结果新增 `compression_efficiency` 和 `circuit_breaker_state` 字段
