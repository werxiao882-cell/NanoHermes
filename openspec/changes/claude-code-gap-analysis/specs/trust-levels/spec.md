## ADDED Requirements

### Requirement: CLAUDE.md 分级信任模型

系统 SHALL 实现四层信任模型，根据文件位置自动分配信任级别。高信任层指令不可被低信任层覆盖。

| 信任级别 | 文件位置 | 说明 |
|----------|----------|------|
| `managed` | 系统管理路径（如 `/etc/nanohermes/`） | IT 管理员控制的策略 |
| `user` | 用户全局路径（如 `~/.nanohermes/CLAUDE.md`） | 用户个人偏好 |
| `project` | 项目根目录（`CLAUDE.md` / `AGENTS.md`） | 项目级约定 |
| `local` | 子目录（`.nanohermes.md`） | 局部覆盖 |

#### Scenario: 高信任不可被低信任覆盖

- **WHEN** `managed` 层声明 `sandbox: required`
- **AND** `project` 层声明 `sandbox: disabled`
- **THEN** 最终生效 `sandbox: required`（managed 优先）
- **AND** 日志记录冲突警告

#### Scenario: 同层指令合并

- **WHEN** `project` 层声明 `language: python`
- **AND** `user` 层声明 `timezone: Asia/Shanghai`
- **THEN** 两个指令都生效（不冲突时合并）

### Requirement: @include 指令

CLAUDE.md 文件 SHALL 支持 `@include` 指令引用其他文件，实现模块化配置。

#### Scenario: 包含子文件

- **WHEN** CLAUDE.md 包含 `@include rules/testing.md`
- **THEN** 加载并注入 `rules/testing.md` 内容
- **AND** 子文件继承父文件的信任级别

### Requirement: @include 深度和循环保护

`@include` 解析 SHALL 实施深度上限和循环引用检测。

#### Scenario: 深度上限

- **WHEN** `@include` 链深度超过 5 层
- **THEN** 拒绝加载第 6 层
- **AND** 返回错误: `@include depth limit exceeded (max: 5)`

#### Scenario: 循环引用检测

- **WHEN** A.md `@include` B.md，B.md `@include` A.md
- **THEN** 检测到循环，拒绝加载
- **AND** 返回错误: `circular @include detected: A.md → B.md → A.md`
