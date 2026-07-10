## 熔断器（Circuit Breaker）

### 需求

- **MUST** 实现三状态机：CLOSED → OPEN → HALF_OPEN → CLOSED
- **MUST** 连续失败 3 次后进入 OPEN 状态（冷却期 5 分钟）
- **MUST** 冷却期后进入 HALF_OPEN 状态（允许一次试探）
- **MUST** 试探成功则恢复 CLOSED，失败则回到 OPEN
