## ADDED Requirements

### Requirement: Hook registry with 8 hook points
系统 SHALL 实现 HookRegistry，支持 8 种生命周期钩子点：PreSampling、PostSampling、PreCompact、PostCompact、SessionStart、FileChanged、SubagentStart、Stop。每种钩子点可配置多个 handler。

#### Scenario: PostSampling 钩子在模型回答后执行
- **WHEN** 模型完成一轮回答
- **THEN** 系统 SHALL 执行所有注册的 PostSampling 钩子 handler

#### Scenario: PreCompact 钩子在压缩前执行
- **WHEN** 系统即将执行 auto-compact
- **THEN** 系统 SHALL 先执行所有 PreCompact 钩子 handler，允许自定义压缩策略

### Requirement: Hook configuration via settings
系统 SHALL 支持通过 settings 配置 hook 脚本路径。配置格式为 `hooks.<hookPoint> = [<script_path>, ...]`。

#### Scenario: 从 settings 加载 hook 配置
- **WHEN** settings 包含 `hooks.postSampling = ["./scripts/lint-check.sh"]`
- **THEN** 系统 SHALL 在 PostSampling 钩子点注册该脚本

### Requirement: Hook execution with fault isolation
系统 SHALL 以 subprocess 方式执行外部 hook 脚本，单个 hook 失败不影响其他 hook 和主流程。执行超时默认为 30 秒。

#### Scenario: 单个 hook 失败不影响主流程
- **WHEN** PostSampling 注册了 3 个 hook，第 2 个执行失败
- **THEN** 系统 SHALL 记录错误日志，继续执行第 3 个 hook，不影响主对话流程

#### Scenario: Hook 执行超时
- **WHEN** hook 脚本执行超过 30 秒
- **THEN** 系统 SHALL 终止该 hook 进程，记录超时错误

### Requirement: Hook input/output protocol
系统 SHALL 通过 stdin 向 hook 脚本传入 JSON 格式的上下文信息（当前消息、工具结果等），通过 stdout 接收 hook 输出。Stop 钩子的输出可阻止模型继续。

#### Scenario: Stop 钩子阻止继续
- **WHEN** Stop 钩子脚本输出 `{"block": true, "message": "Lint check failed"}`
- **THEN** 系统 SHALL 将 message 作为错误消息注入对话，阻止模型继续下一轮

### Requirement: FileChanged hook with glob patterns
系统 SHALL 支持 FileChanged 钩子配置 glob pattern，只有匹配的文件变更才触发 hook 执行。

#### Scenario: 匹配的文件变更触发 hook
- **WHEN** FileChanged 钩子配置 `paths: ["src/**/*.py"]` 且用户编辑了 `src/main.py`
- **THEN** 系统 SHALL 触发该 hook 执行
