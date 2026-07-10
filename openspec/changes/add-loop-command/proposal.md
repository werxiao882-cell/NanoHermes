## Why

NanoHermes 当前的对话循环是单次触发的：用户输入 → AI 响应 → 等待下一次输入。对于需要持续监控、轮询或迭代改进的场景（如等待 CI 通过、监控部署状态、持续改进代码），用户必须手动重复输入相同指令。参考 Claude Code 的 `/loop` 命令，增加循环执行能力可以让 AI Agent 在会话内自动重复执行任务，减少用户干预。

## What Changes

- 新增 `/loop` 斜杠命令，支持 4 种使用模式：
  - `/loop <interval> <prompt>` — 按固定间隔重复执行指定提示
  - `/loop <prompt>` — 按 AI 动态选择的间隔重复执行
  - `/loop <interval>` — 按固定间隔执行内置维护提示
  - `/loop` — 按动态间隔执行内置维护提示
- 新增 `loop.md` 文件支持，用户可自定义默认维护提示
- 新增 `/stop-loop` 命令停止当前循环
- 新增 `src/loop/` 模块管理循环生命周期
- 复用现有 `cronjob` 工具作为底层调度引擎
- 循环作用域限定在当前会话，`--resume` 可恢复未过期循环（7 天内）

## Capabilities

### New Capabilities

- `loop-command`: `/loop` 和 `/stop-loop` 斜杠命令处理，支持间隔解析和提示提取
- `loop-manager`: 循环生命周期管理（创建、执行、停止、恢复），包括间隔调度和提示执行
- `loop-prompt`: 内置维护提示（继续未完成工作、检查 PR 状态、清理优化），支持 `loop.md` 覆盖
- `loop-integration`: 与现有 `cronjob` 工具的集成，复用调度能力

### Modified Capabilities

- `cronjob-tool`: 增强调度引擎，支持循环任务的会话内执行（非独立会话）
- `tui`: 新增循环状态指示器，显示当前循环信息

## Impact

- 新增模块：`src/loop/`（manager.py, prompt.py, interval_parser.py）
- 修改文件：`src/cli/tui.py`（新增 `/loop`、`/stop-loop` 命令处理）
- 修改文件：`src/cli/completers.py`（新增命令补全）
- 修改文件：`src/tools/impls/cronjob_tool.py`（增强调度执行能力）
- 不影响现有工具系统、对话循环、会话存储
- 新增用户文件约定：`.nanohermes/loop.md`（用户级）、`.claude/loop.md`（项目级）
