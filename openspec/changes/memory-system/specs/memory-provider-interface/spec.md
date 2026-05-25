## ADDED Requirements

### Requirement: 系统 SHALL 定义 MemoryProvider 抽象基类
系统 SHALL 提供 MemoryProvider 抽象类，定义标准生命周期钩子。核心方法 SHALL 为抽象方法：isAvailable、initialize、getToolSchemas。可选方法 SHALL 有默认空实现。

#### Scenario: 实现核心方法
- **WHEN** 创建新的记忆提供者
- **THEN** 必须实现 isAvailable、initialize、getToolSchemas 方法

#### Scenario: 覆盖可选钩子
- **WHEN** 提供者需要会话结束处理
- **THEN** 覆盖 onSessionEnd 方法

### Requirement: MemoryProvider SHALL 支持标准生命周期钩子
提供者 SHALL 实现：initialize（会话初始化）、systemPromptBlock（系统提示块）、prefetch（背景回忆）、syncTurn（同步轮次）、shutdown（清理关闭）。

#### Scenario: 初始化会话
- **WHEN** Agent 启动时
- **THEN** MemoryManager 调用所有提供者的 initialize 方法

#### Scenario: 背景预取
- **WHEN** 新轮次开始前
- **THEN** MemoryManager 调用 prefetch 获取相关上下文

### Requirement: MemoryProvider SHALL 支持可选钩子
提供者 SHALL 可选择实现：onTurnStart、onSessionEnd、onSessionSwitch、onPreCompress、onDelegation、onMemoryWrite。

#### Scenario: 会话切换通知
- **WHEN** Agent 切换 session_id（/resume、/branch、压缩）
- **THEN** 调用 onSessionSwitch 更新提供者内部状态

#### Scenario: 委托观察
- **WHEN** 子 agent 完成任务
- **THEN** 调用父 agent 提供者的 onDelegation 方法
