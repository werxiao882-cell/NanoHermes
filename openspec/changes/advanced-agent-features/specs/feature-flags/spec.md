## ADDED Requirements

### Requirement: Feature flag manager
系统 SHALL 实现 FeatureFlagManager 单例，管理所有运行时特性开关。Flag 值从两个来源加载：配置文件（`featureFlags` 字段）和环境变量（`NANOHERMES_FLAG_<NAME>`）。环境变量优先级高于配置文件。

#### Scenario: 从配置文件加载 flag
- **WHEN** 配置文件包含 `featureFlags.sandbox = true`
- **THEN** `is_enabled('sandbox')` SHALL 返回 True

#### Scenario: 环境变量覆盖配置文件
- **WHEN** 配置文件 `sandbox = true` 但环境变量 `NANOHERMES_FLAG_SANDBOX = false`
- **THEN** `is_enabled('sandbox')` SHALL 返回 False

### Requirement: Feature flag stages
系统 SHALL 支持 flag 的三个阶段：alpha（默认关闭，需显式启用）、beta（默认关闭，文档可见）、ga（默认启用，可显式关闭）。

#### Scenario: Alpha flag 默认关闭
- **WHEN** flag `reactive_compact` 阶段为 alpha 且未显式配置
- **THEN** `is_enabled('reactive_compact')` SHALL 返回 False

#### Scenario: GA flag 默认启用
- **WHEN** flag `cost_tracking` 阶段为 ga 且未显式配置
- **THEN** `is_enabled('cost_tracking')` SHALL 返回 True

### Requirement: Feature flag listing
系统 SHALL 提供 `/flags` 命令，列出所有已注册的 feature flag 及其当前值和阶段。

#### Scenario: 列出所有 flag
- **WHEN** 用户执行 `/flags` 命令
- **THEN** 系统 SHALL 显示所有 flag 的名称、阶段、当前值和来源（config/env/default）

### Requirement: Conditional module loading
系统 SHALL 在模块加载时检查 feature flag，未启用的功能模块不加载，不占用内存和工具 schema 空间。

#### Scenario: 未启用的功能不加载工具
- **WHEN** feature flag `streaming_tool_execution` 为 false
- **THEN** StreamingToolExecutor 模块 SHALL 不被加载，相关工具不出现在 schema 中
