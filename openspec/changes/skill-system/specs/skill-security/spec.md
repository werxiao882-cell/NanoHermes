## ADDED Requirements

### Requirement: 系统 SHALL 实现安全扫描器
系统 SHALL 提供 SkillGuard 类，使用正则静态分析检测外部来源技能中的安全风险。检测类别包括：
- **exfiltration**：数据泄露（curl/wget 外发敏感数据）
- **injection**：代码注入（eval/exec 动态执行）
- **destructive**：破坏性命令（rm -rf /、mkfs）
- **persistence**：持久化后门（crontab、systemctl enable）

#### Scenario: 检测数据泄露
- **WHEN** 技能文件包含 `curl.*${API_KEY}` 或 `wget --post-file` 模式
- **THEN** 标记为 exfiltration 风险，severity=critical

#### Scenario: 检测代码注入
- **WHEN** 技能文件包含 `eval(` 或 `exec(` 模式
- **THEN** 标记为 injection 风险，severity=high

#### Scenario: 检测破坏性命令
- **WHEN** 技能文件包含 `rm -rf /` 或 `mkfs.` 模式
- **THEN** 标记为 destructive 风险，severity=critical

#### Scenario: 检测持久化后门
- **WHEN** 技能文件包含 `crontab -` 或 `systemctl enable` 模式
- **THEN** 标记为 persistence 风险，severity=high/medium

### Requirement: 系统 SHALL 实现信任级别策略
安全扫描 SHALL 根据技能来源应用不同的信任级别：
- **builtin**：内置技能，跳过扫描
- **trusted**：可信来源，仅警告
- **community**：社区来源，拒绝安装或要求用户确认

#### Scenario: 内置技能跳过扫描
- **WHEN** 技能来源为 bundled 时
- **THEN** 跳过安全扫描

#### Scenario: 社区技能检测到 critical 风险
- **WHEN** 社区来源技能检测到 severity=critical 的风险
- **THEN** 拒绝安装并报告风险详情

#### Scenario: 社区技能检测到 high 风险
- **WHEN** 社区来源技能检测到 severity=high 的风险
- **THEN** 要求用户确认后才允许安装

### Requirement: 系统 SHALL 扫描技能目录中的所有文件
安全扫描 SHALL 递归扫描技能目录中的所有文件，包括：
- SKILL.md 主文件
- references/ 目录下的文档
- scripts/ 目录下的脚本
- templates/ 目录下的模板

#### Scenario: 扫描 SKILL.md
- **WHEN** 扫描技能目录时
- **THEN** 检查 SKILL.md 文件内容

#### Scenario: 扫描脚本文件
- **WHEN** 技能目录包含 scripts/ 子目录时
- **THEN** 递归扫描所有 .py/.sh/.js 文件

#### Scenario: 忽略二进制文件
- **WHEN** 技能目录包含二进制文件时
- **THEN** 跳过二进制文件，只扫描文本文件

### Requirement: 系统 SHALL 追踪技能来源
系统 SHALL 区分技能的创建来源，用于 Curator 管理和权限控制：
- **bundled**：内置技能（从仓库 skills/ 目录同步）
- **hub-installed**：从技能中心安装的技能
- **agent-created**：Agent 在对话中创建的技能
- **manual**：用户手动创建的技能

#### Scenario: 标记 agent-created
- **WHEN** Agent 通过 skill_manage 工具创建技能时
- **THEN** 在 .usage.json 中标记 created_by: "agent"

#### Scenario: 区分 hub-installed
- **WHEN** 从技能中心安装技能时
- **THEN** 在 .hub/lock.json 中记录来源和版本

#### Scenario: 识别 bundled 技能
- **WHEN** 技能从仓库 skills/ 目录同步时
- **THEN** 在 .bundled_manifest 中记录 origin_hash

### Requirement: 系统 SHALL 使用 ContextVar 追踪写入来源
系统 SHALL 使用 Python contextvars.ContextVar 追踪技能写入的来源上下文：
- 默认值："user"（用户前台操作）
- 后台审查时设置为："background_review"

#### Scenario: 前台用户写入
- **WHEN** 用户在对话中调用 skill_manage 时
- **THEN** write_origin ContextVar 为 "user"

#### Scenario: 后台审查写入
- **WHEN** Curator fork 的 AIAgent 调用 skill_manage 时
- **THEN** write_origin ContextVar 为 "background_review"

### Requirement: Curator SHALL 只管理 agent-created 技能
Curator 的自动转换和审查 SHALL 只作用于 agent-created 来源的技能。以下来源受保护，Curator 不可触碰：
- bundled 技能（.bundled_manifest 记录）
- hub-installed 技能（.hub/lock.json 记录）
- manual 技能（无 created_by: "agent" 标记）

#### Scenario: Curator 跳过 bundled 技能
- **WHEN** Curator 运行时遇到 bundled 来源的技能
- **THEN** 跳过该技能，不进行状态转换或审查

#### Scenario: Curator 跳过 hub-installed 技能
- **WHEN** Curator 运行时遇到 hub-installed 来源的技能
- **THEN** 跳过该技能，不进行状态转换或审查

#### Scenario: Curator 管理 agent-created 技能
- **WHEN** Curator 运行时遇到 agent-created 来源的技能
- **THEN** 执行正常的生命周期管理和审查流程

### Requirement: 系统 SHALL 提供来源查询接口
系统 SHALL 提供 get_provenance(skill_name) 方法，返回技能的来源类型。

#### Scenario: 查询 bundled 技能来源
- **WHEN** 调用 get_provenance("bundled-skill") 时
- **THEN** 返回 "bundled"

#### Scenario: 查询 agent-created 技能来源
- **WHEN** 调用 get_provenance("agent-skill") 时
- **THEN** 返回 "agent-created"

#### Scenario: 查询未知技能
- **WHEN** 调用 get_provenance("unknown-skill") 时
- **THEN** 返回 "manual"（默认值）

### Requirement: 系统 SHALL 实现 AST 深度审计
系统 SHALL 提供 SkillAstAuditor 类，使用 Python AST 解析检测技能 Python 文件中的潜在安全风险。

#### Scenario: 审计技能目录
- **WHEN** 调用 audit(skill_dir) 方法时
- **THEN** 递归扫描目录中的所有 .py 文件

#### Scenario: 生成审计报告
- **WHEN** 审计完成时
- **THEN** 返回包含所有发现问题的审计报告

### Requirement: 系统 SHALL 检测动态 import
AST 审计 SHALL 检测以下动态 import 模式：
- `__import__("module")`
- `importlib.import_module("module")`
- `exec("import module")`

#### Scenario: 检测 __import__
- **WHEN** Python 文件包含 `__import__("os")`
- **THEN** 标记为 dynamic_import 风险

#### Scenario: 检测 importlib
- **WHEN** Python 文件包含 `importlib.import_module("subprocess")`
- **THEN** 标记为 dynamic_import 风险

#### Scenario: 检测 exec import
- **WHEN** Python 文件包含 `exec("import os")`
- **THEN** 标记为 dynamic_import 风险

### Requirement: 系统 SHALL 检测动态属性访问
AST 审计 SHALL 检测以下动态属性访问模式：
- `getattr(obj, "attr")`
- `setattr(obj, "attr", value)`
- `delattr(obj, "attr")`

#### Scenario: 检测 getattr
- **WHEN** Python 文件包含 `getattr(module, "dangerous_func")`
- **THEN** 标记为 dynamic_attribute 风险

#### Scenario: 检测 setattr
- **WHEN** Python 文件包含 `setattr(obj, "__class__", new_class)`
- **THEN** 标记为 dynamic_attribute 风险

### Requirement: AST 审计 SHALL 为可选诊断
AST 审计 SHALL 作为可选的诊断功能，默认不启用，需要用户显式触发。

#### Scenario: 手动触发审计
- **WHEN** 用户调用 `hermes skills audit <skill-name>` 时
- **THEN** 执行 AST 深度审计并输出报告

#### Scenario: 审计不影响安装
- **WHEN** 从技能中心安装技能时
- **THEN** 不自动执行 AST 审计（只执行 SkillGuard 正则扫描）

### Requirement: 审计报告 SHALL 包含详细信息
审计报告 SHALL 包含以下信息：
- 文件路径
- 行号
- 风险类型（dynamic_import / dynamic_attribute）
- 代码片段
- 建议操作

#### Scenario: 报告格式
- **WHEN** 检测到风险时
- **THEN** 输出格式：`[风险类型] 文件:行号 - 代码片段`

#### Scenario: 无风险时输出
- **WHEN** 审计未发现风险时
- **THEN** 输出 `No issues found.`
