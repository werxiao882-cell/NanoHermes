## 修改需求

### 需求：对话循环发出 LOOP_END 事件

系统应在对话循环完成时发出 `LOOP_END` 事件，启用后台任务触发。

#### 场景：成功完成时发出 LOOP_END 事件
- **当** `ConversationLoop.run()` 成功完成
- **则** 系统发出 `LOOP_END` 事件，包含结果数据
- **则** 事件包含：`result`、`iterations`、`total_elapsed`
- **则** `BackgroundTaskScheduler` 接收事件并评估触发条件

#### 场景：达到最大迭代次数时发出 LOOP_END 事件
- **当** `ConversationLoop.run()` 达到 max_iterations 限制
- **则** 系统发出 `LOOP_END` 事件，包含部分结果
- **则** 事件包含：`result`、`iterations`、`total_elapsed`
- **则** `BackgroundTaskScheduler` 接收事件

#### 场景：中断时发出 LOOP_END 事件
- **当** 用户中断对话（Ctrl+C）
- **则** 系统发出 `INTERRUPT` 事件
- **则** 系统发出 `LOOP_END` 事件，包含中断结果
- **则** `BackgroundTaskScheduler` 接收事件，但可能因中断标志跳过任务

**理由**：此修改使后台任务系统能够挂钩到对话生命周期，而无需修改核心循环逻辑。事件驱动的方法保持了关注点分离。

**迁移**：无需迁移。现有事件处理器继续工作。新处理器可以订阅 `LOOP_END` 以触发后台任务。
