## ADDED Requirements

### Requirement: Sandbox runtime adapter
系统 SHALL 提供 SandboxManager 单例，负责将命令包装在受限执行环境中。基础层通过路径白名单和命令黑名单实现（全平台），增强层通过 OS 级沙盒实现（Linux bubblewrap / macOS sandbox-exec，可选）。

#### Scenario: 基础层沙盒拦截越权写入
- **WHEN** 工具尝试执行 `rm -rf /etc/passwd` 命令
- **THEN** SandboxManager SHALL 检测到目标路径不在 allowWrite 白名单中，拒绝执行并返回错误

#### Scenario: 基础层沙盒允许白名单内操作
- **WHEN** 工具执行 `echo hello > ./output.txt` 且 `.` 在 allowWrite 白名单中
- **THEN** SandboxManager SHALL 允许命令正常执行

#### Scenario: 增强层沙盒在 Linux 上使用 bubblewrap
- **WHEN** feature flag `sandbox.enhanced` 启用且平台为 Linux 且 bubblewrap 已安装
- **THEN** SandboxManager SHALL 使用 `bwrap` 命令包装执行，挂载 allowWrite 路径为可写，其余为只读

### Requirement: Filesystem whitelist configuration
系统 SHALL 从 settings 配置中解析文件系统白名单，包括 allowWrite、denyWrite、allowRead、denyRead 四个列表。settings 文件路径和 `.claude/skills/` 目录 SHALL 始终被加入 denyWrite。

#### Scenario: Settings 文件被自动保护
- **WHEN** 沙盒初始化时
- **THEN** `~/.nanohermes/config.json` 和项目级 `nanohermes.json` SHALL 被自动加入 denyWrite 列表

#### Scenario: Skills 目录被自动保护
- **WHEN** 沙盒初始化时
- **THEN** `.claude/skills/` 目录 SHALL 被自动加入 denyWrite 列表，防止技能投毒

### Requirement: Network domain whitelist
系统 SHALL 从 WebFetch 权限规则中提取允许的域名，转换为沙盒网络白名单。超出白名单的网络访问 SHALL 被拦截或弹出确认。

#### Scenario: 从权限规则提取域名
- **WHEN** 权限规则包含 `WebFetch(domain:example.com)` 的 allow 规则
- **THEN** `example.com` SHALL 被加入沙盒网络 allowDomains 列表

### Requirement: Git bare repo scrub
系统 SHALL 在每次沙盒命令执行完毕后，扫描并清除工作目录中可能被植入的 Git 裸仓库文件（HEAD、objects/、refs/、hooks/、config），防止 Git 逃逸攻击。

#### Scenario: 清除沙盒内植入的 Git 裸仓库
- **WHEN** 沙盒命令执行完毕且命令前工作目录不存在 HEAD 文件
- **THEN** SandboxManager SHALL 检查并删除命令执行后新出现的 HEAD、objects/、refs/ 文件

### Requirement: Sandbox config hot reload
系统 SHALL 监听 settings 配置文件变化，当权限或沙盒配置变更时，实时同步到沙盒 runtime，无需重启。

#### Scenario: 配置变更后沙盒规则即时生效
- **WHEN** 用户修改 settings 中的 sandbox.filesystem.allowWrite 列表
- **THEN** SandboxManager SHALL 在下次命令执行时使用新的白名单规则

### Requirement: Sandbox availability detection
系统 SHALL 检测沙盒是否可用（平台支持、依赖安装），并在不可用时给出明确原因。当 `failIfUnavailable` 启用时，沙盒不可用 SHALL 阻止命令执行。

#### Scenario: 沙盒不可用且 failIfUnavailable 启用
- **WHEN** 平台不支持沙盒且 `sandbox.failIfUnavailable = true`
- **THEN** 系统 SHALL 拒绝执行所有需要沙盒的命令，并显示不可用原因

#### Scenario: 沙盒不可用且 failIfUnavailable 未启用
- **WHEN** 平台不支持沙盒且 `sandbox.failIfUnavailable = false`
- **THEN** 系统 SHALL 退化为无沙盒模式，并在 TUI 中显示警告
