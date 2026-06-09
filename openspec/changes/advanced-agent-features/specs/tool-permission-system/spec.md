## ADDED Requirements

### Requirement: Permission mode state machine
系统 SHALL 实现权限模式状态机，支持 default、acceptEdits、plan、auto、bypassPermissions 五种模式。每种模式定义不同的规则评估策略和用户交互行为。

#### Scenario: Default 模式下每次操作弹出确认
- **WHEN** 权限模式为 default 且工具执行非只读操作
- **THEN** 系统 SHALL 弹出确认提示，用户可选择 allow/deny/allow-always

#### Scenario: Auto 模式下安全操作自动放行
- **WHEN** 权限模式为 auto 且工具操作被分类为安全（只读或白名单匹配）
- **THEN** 系统 SHALL 自动允许执行，不弹出确认

#### Scenario: Plan 模式禁止写操作
- **WHEN** 权限模式为 plan
- **THEN** 系统 SHALL 拒绝所有非只读工具操作

### Requirement: Permission rule engine
系统 SHALL 实现声明式规则引擎，支持 allow/deny/ask 三种规则类型。规则格式为 `ToolName(pattern)`，如 `terminal(rm *)` → deny。规则按 source 分层（policy > user > project > local）。

#### Scenario: Deny 规则优先于 allow 规则
- **WHEN** 同一工具同时匹配 deny 和 allow 规则
- **THEN** deny 规则 SHALL 优先生效

#### Scenario: Ask 规则触发用户确认
- **WHEN** 工具匹配 ask 规则且无 deny 规则匹配
- **THEN** 系统 SHALL 弹出确认对话框

### Requirement: Dangerous Bash pattern detection
系统 SHALL 维护危险 Bash 模式黑名单（python、node、eval、sudo、ssh 等），在 Auto 模式下自动剥离匹配这些模式的宽泛权限规则。

#### Scenario: Auto 模式剥离危险的 Bash 权限
- **WHEN** 进入 auto 模式且权限规则包含 `terminal(python:*)` 的 allow 规则
- **THEN** 系统 SHALL 临时移除该规则，退出 auto 模式时恢复

#### Scenario: 空规则被视为极度危险
- **WHEN** 权限规则为 `terminal(*)` 或 `terminal()`
- **THEN** 系统 SHALL 将其标记为危险规则，在 auto 模式下剥离

### Requirement: Compound command splitting
系统 SHALL 将复合命令（`&&`、`||`、`;`、`|` 分隔）拆分为子命令，逐个检查 deny/ask 规则。任一子命令命中 deny SHALL 拒绝整个命令。

#### Scenario: 复合命令中一个子命令被 deny
- **WHEN** 命令为 `ls && rm -rf /` 且 `rm -rf` 匹配 deny 规则
- **THEN** 系统 SHALL 拒绝整个命令执行

### Requirement: Bypass permissions remote killswitch
系统 SHALL 支持通过远程策略（Statsig 或配置文件）禁用 bypassPermissions 模式，即使用户在命令行传了 `--dangerously-skip-permissions` 参数也 SHALL 被忽略。

#### Scenario: 远程策略禁用 bypass 模式
- **WHEN** 策略配置 `permissions.disableBypassPermissionsMode = true`
- **THEN** 系统 SHALL 忽略 `--dangerously-skip-permissions` 参数，通知用户该模式已被组织策略禁用

### Requirement: Path traversal protection
系统 SHALL 对所有文件路径操作进行防御性校验，resolve 后检查是否超出允许目录范围，防止 `../../etc/passwd` 类路径穿越攻击。

#### Scenario: 路径穿越被拦截
- **WHEN** 工具尝试操作 `../../etc/passwd` 路径
- **THEN** 系统 SHALL resolve 路径后检测其超出工作目录范围，拒绝操作
