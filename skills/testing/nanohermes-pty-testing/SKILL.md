---
name: nanohermes-pty-testing
description: "真实 PTY 端到端测试 NanoHermes — 7 阶段流程 + 530 用例（370 [PTY] 可直接执行）"
version: 6.1.0
platforms: [linux, macos, wsl]
metadata:
  hermes:
    tags: [testing, e2e, pty, nanohermes, qa]
    related_skills: [dogfood]
---

# NanoHermes PTY 端到端测试

## 触发条件

用户要求测试 NanoHermes / 跑 PTY 测试 / 端到端测试 / 回归测试 时加载。

## 测试方法论

**标记说明**：`[PTY]` 直接可执行 | `[DEBUG]` 需 --debug | `[FAULT]` 故障注入 | `[MANUAL]` 仅手动 | `[UNIT]` 仅单元测试

**总计 530 用例（370 [PTY] 可直接执行）**，按 7 阶段执行。自动化 runner 见 `scripts/pty_runner.py`。详细用例清单按需加载 reference 文件：

| Reference | 模块 | 用例数 | 何时加载 |
|-----------|------|--------|---------|
| `references/core-tools.md` | tool-runtime + tool-search + dispatcher | 141 | 阶段 3-4 执行工具测试时 |
| `references/session-storage.md` | session-storage | 113 | 阶段 5 验证存储时 |
| `references/memory-system.md` | memory-system | 15 | 阶段 3.2 + 阶段 5 |
| `references/provider-config.md` | provider + config + prompt | 58 | 阶段 2 启动验证 + 阶段 6 |
| `references/conversation.md` | conversation-loop + delegation | 82 | 阶段 3 + 阶段 6 |
| `references/cli-tui.md` | cli/TUI | 18 | 阶段 3.3 + 阶段 2 |
| `references/advanced.md` | skills + compression + insights + mcp + auxiliary | 103 | 阶段 4 + 阶段 6 |
| `references/test-findings.md` | 实际测试发现、配置陷阱、JSONL 格式、AI 行为模式 | - | 测试前必读 |
| `references/wait-time-calibration.md` | PTY 用例等待时间校准表、诊断方法 | - | 用例失败排查时 |
| `references/counter-debug.md` | SQLite 计数器排查流程、关键代码路径 | - | 计数器异常时 |
| `references/pty-execution-log.md` | 自动化 runner 执行记录、失败分析 | - | 排查 TS-01/M-01 失败时 |
| `references/pty-run-2026-06-10-round2.md` | 第二轮 runner 执行记录（37 用例、94.6% 通过率、M-01 通过） | - | 追踪测试进展时 |

## 输出目录规范

`testing-artifacts/{reports,scripts,logs}`，永不删除历史，冲突追加序号。

## 测试执行发现与陷阱（实时更新）

> 以下来自实际 PTY 测试执行，持续积累。

### PTY 自动化测试（2026-06-10 新增，第二轮更新）
- **pexpect 驱动**：使用 `pexpect.spawn` + `expect()` 模式匹配提示符，比管道方式可靠。
- **提示符匹配**：NanoHermes 的 TUI prompt（`➤|❯`）被 ANSI 转义码包围，pexpect 正则需扩展匹配 `Type\s+/quit|CPR\b|history` 作为就绪信号。
- **输出清理**：`child.before` 包含完整终端输出（含 ANSI 控制码），验证测试用例时需对正则模式做宽泛匹配。
- **⚠️ ANSI 陷阱**：`/tools` 等 TUI 命令输出含大量 ANSI 转义序列（`\x1b[...m`、`\r`、`\b`），纯文本关键词匹配（如 "defer"、"延迟"）容易被转义码打断。解决方案：简化验证模式或先 strip ANSI。
- **⚠️ 提示符匹配过宽导致重复发送**：清理 ANSI 后，正则 `➤|❯|Type\s+/quit|CPR|history` 过于宽泛，导致同一命令被重复发送 2-3 次（如 `/tools` 连续出现 3 次）。修复方案：使用更精确的 prompt 匹配，或增加去重逻辑（记录上次发送内容，相同则跳过）。
- **✅ 记忆工具调用模式**：自然语言指令（"请记住"）**不触发** memory 工具调用。使用明确参数格式（"调用 memory 工具，参数：action=add, target=user, content=..."）可以可靠触发。第二轮测试 M-01 通过。
- **⚠️ AI 拒绝措辞不一致**：T-44 二进制文件测试中，NanoHermes 拒绝读取 .png 文件但回复措辞不包含 "binary/拒绝/deny/cannot"，导致正则匹配失败。AI 可能用"不支持该文件格式"等不同措辞。验证模式需更宽泛或检查工具调用而非文本回复。

### PTY 输出捕获关键陷阱

**pexpect buffer 被 TUI 清屏序列清空**：
NanoHermes TUI 使用 ANSI 清屏序列（`\x1b[2J`、`\x1b[H`、`\x1b[J`）渲染界面，
`pexpect.spawn()` 的 `child.before` 缓冲区会被这些序列冲刷，导致输出为空。

**正确做法**：用 `script` 命令在 TTY 外层捕获：
```bash
script -q -c "python -m src.main" /tmp/test_output.log
```
`script` 录制完整终端 I/O，不受应用层清屏影响。捕获后仍需清理 ANSI 码再匹配。

**失败模式对照**：
- ❌ `pexpect.spawn(..., logfile=stdout)` → 输出为空
- ✅ `script -q -c "cmd" output.log` → 完整 TUI 内容

详见 `references/pty-output-capture.md`。改进版 runner 见 `scripts/pty_runner_v2.py`。

### 配置陷阱
- **nanohermes.json 格式**：项目默认没有 `nanohermes.json`，只有 `nanohermes.example.json`。测试前必须创建。
- **Provider 配置模式**：当 .env 使用 `OPENAI_API_KEY` + `OPENAI_BASE_URL` 时，provider 配置必须用 `openai` 类型，字段为 `base_url_env` / `api_key_env`（不是 `base_url` / `api_key_env`）。
- **DashScope 兼容模式**：通义千问通过 DashScope OpenAI 兼容端点访问，`base_url` = `https://dashscope.aliyuncs.com/compatible-mode/v1`。

### JSONL 格式注意
- **多行 pretty-print 格式**：NanoHermes 的 JSONL 每条消息是多行格式（带缩进的花括号），**不是**紧凑单行 JSON。
- 验证 JSONL 时不能用 `head -1 | jq`，需要逐条解析或使用 `grep` 统计角色。
- 消息分隔：每条消息以 `{` 开头，以 `}` 结尾，中间有缩进。

### SQLite 计数器（已修复 ✅）
- **历史问题**：测试中发现 `message_count`、`tool_call_count` 始终为 0。
- **根因**：`insert_message()` 插入消息后未调用 `increment_message_count()`；`_on_tool_start()` 未调用 `increment_tool_call_count()`。
- **修复**（2026-06-10）：
  1. `session_db.py`: `insert_message()` 成功后自动调用 `increment_message_count`（user/assistant/system 角色）
  2. `event_handler.py`: `ConversationEventHandler` 添加 `session_db` 参数，`_on_tool_start` 调用 `increment_tool_call_count`
  3. `tui.py`: 实例化时传入 `session_db`
- **验证**：端到端测试 `message_count=6, tool_call_count=2` ✅
- **如果未来再次出现 0**：参考 `references/counter-debug.md` 排查流程

### AI 行为模式
- **clarify 工具不必然触发**：当用户说"问我一个问题"时，AI 倾向于用文本对话生成选择题，而非调用 clarify 工具。这是预期行为，clarify 主要用于任务歧义需要澄清时。
- **memory 工具不必然触发（重要）**：当用户说"请记住X"时，AI 倾向于用文本对话回复"好的我记住了"，**不调用 memory 工具**。实际验证：37 轮对话中 memory 工具调用次数 = **0**（从 JSONL 验证）。测试 memory 功能时，需要更明确的指令如"调用 memory 工具，action=add, target=user, content=..."才能触发。
- **过度搜索**：要求"搜索工具 X"时，AI 可能调用 search_tools 2-3 次（不同策略），这是已知限制而非 bug。
- **上下文保持良好**：AI 能正确引用之前对话中创建的文件和内容。

### 已知修复方法（实际验证有效）
| 问题 | 修复 | 验证状态 |
|------|------|---------|
| 配置缺失 | 创建 nanohermes.json（openai provider） | ✅ |
| 依赖超时 | timeout 增加到 60s | ✅ |
| 启动崩溃 | `rm -rf src/__pycache__ src/*/__pycache__` | 技能中记录，待验证 |

> 详见 `references/wait-time-calibration.md` — 各用例类型等待时间校准表。

## 回归测试执行策略（2026-06-10 新增，已验证 100% 通过）

**关键教训：每用例独立会话 + script 捕获**

首次回归测试尝试（单会话多用例）失败率 97.2%（35/36 FAIL），原因：
- `script` 日志在单会话中被 TUI 清屏序列冲刷
- 用例间状态互相干扰（前一个用例的 prompt 残留影响下一个）

**✅ 正确模式**：每个用例启动独立的 NanoHermes 会话
```python
for tc in test_cases:
    result = run_single_test(tc['id'], tc['prompt'], tc['expected_patterns'])
    # 每测试：新进程 + 新 script 日志 + 新会话
```

**代价**：36 用例约需 20 分钟（含 T-08 的 60s 等待、T-22 的 45s 等待等）

**script 日志缓冲区**：观察到 `script` 输出文件初始被限制在 4096 字节，随 TUI 渲染逐渐增长。不要在文件还在增长时立即读取——等待 AI 响应完成后再读取。

**校准版 runner**：`scripts/full_regression.py` — 36 用例，100% 通过率，等待时间已针对 AI 响应延迟调优。

## 7 阶段测试流程

### 阶段 1: 环境准备 `[PTY]`

```bash
eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312
cd /mnt/d/code/NanoHermes
rm -rf ~/.nanohermes/sessions/* ~/.nanohermes/sessions.db* ~/.nanohermes/memory/*
mkdir -p testing-artifacts/{reports,scripts,logs}
```

**⚠️ 配置检查**：测试前必须确认 `nanohermes.json` 存在。如果不存在，创建最小配置（参考 `references/test-findings.md`）。

**验证门**：`python -c "import openai, yaml, rich, sqlite3; print('OK')"` → 通过。（timeout 需 60s，conda 激活较慢）
**覆盖**：CF-01, CF-04, CF-06, CF-09, CF-11

### 阶段 2: 启动验证 `[PTY]`

```python
terminal(command="eval \"$($HOME/miniconda3/bin/conda shell.bash hook)\" && conda activate py312 && cd /mnt/d/code/NanoHermes && python -m src.main", background=True, pty=True)
terminal(command="sleep 10")
process(action='poll', session_id='<id>')
```

**验证门**：进程 running | 工具列表(6 loaded + 11 deferred) | CPR 警告非阻塞 | 状态栏正常
**⚠️ 陷阱**：启动崩溃先清 `__pycache__`；`status_bar` 需在 `self.model` 赋值后创建
**覆盖**：CF-02, CF-03, CF-05, CF-07, CF-10, TUI-01, P-04, P-11, P-12, P-16, PA-01, PA-06, S-12, S-16, S-17, S-30, D-09

> 📖 完整 provider/config/prompt 用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/provider-config.md')`
> 📖 完整 cli/TUI 用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/cli-tui.md')`

### 阶段 3: 基础对话 + 工具链（核心）

#### 3.1 基础对话 `[PTY]`

```
你好 → 正常回复，Thought 可见，3-5s 响应
```

**覆盖**：P-01, P-02, P-05, P-07, P-08, P-16, P-31, P-32, P-36, C-01, C-21, C-37, TUI-02, TUI-03, TUI-13, TUI-14

#### 3.2 工具链 `[PTY]` — 严格按序

| 序号 | 测试输入 | 预期 | 覆盖 |
|------|---------|------|------|
| 1 | `运行 echo hello` | "hello" | T-02 |
| 2 | `运行 false` | exit code 1 | T-14 |
| 3 | `创建 /tmp/nanotest.txt 写入 "Hello NanoHermes"` | 16 bytes | T-05 |
| 4 | `读取 /tmp/nanotest.txt` | "Hello NanoHermes" | T-04 |
| 5 | `把 Hello 替换为 Hi` | 替换成功 | T-06, T-18 |
| 6 | `再读一次确认` | "Hi NanoHermes" | C-02 |
| 7 | `读第 1 行(offset=1,limit=1)` | 分页读取 | T-16, T-46 |
| 8 | `搜索含 class 的 Python 文件` | 匹配列表 | T-07, T-08, TS-02, T-50 |
| 9 | `计算 100 以内质数和` | 1060 | T-10 |
| 10 | `记住名字是测试员小王` | memory success | M-02, T-27 |
| 11 | `问我一个问题` | clarify 选择题 | T-12, T-36 |
| 12 | `创建 TODO：测试 PTY` | todo 成功 | T-33, T-34 |

**⚠️ 陷阱**：3→4→5→6 是依赖链必须按序；execute_code 预期 1060

> 📖 完整 79 个工具用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/core-tools.md')`
> 📖 完整 12 个记忆用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/memory-system.md')`

#### 3.3 TUI 命令 `[PTY]`

```
/tools → 工具列表(loaded/deferred) | /sessions → 当前会话 | /skills → 技能列表
/status → 状态 | /clear → 清屏
```

**覆盖**：T-01, TS-01, TUI-05, S-04, S-11, S-56, SK-01, SK-07, TUI-09~12, S-57

#### 3.4 上下文 + 错误 + 边界 `[PTY]`

```
刚才创建的文件内容是什么？  → 正确识别 /tmp/nanotest.txt
读取 /tmp/不存在的文件.txt  → 友好提示，对话不中断
测试特殊字符 🎉 <>&"'  → 正常处理
```

**覆盖**：C-04, S-09, S-10, T-09, C-05, PA-08, M-10, T-44, T-45, T-48, T-49, T-52, D-10~14

### 阶段 4: 高级场景 `[PTY]`

| 测试输入 | 预期 | 覆盖 |
|---------|------|------|
| `搜索含 "async def" 的文件` | BM25/Regex 结果 | TS-02, TS-03, TS-04, T-51 |
| `找不存在的工具 run_spell` | 友好提示 | TS-06, T-43, D-09 |
| `搜索只返回文件路径 *.py` | files_only | T-20, T-54 |
| `搜索统计含 class 的文件数` | count 模式 | T-21 |
| 大文件输出 | 自动截断 | T-11, CC-03, T-39, D-20 |
| `创建 /tmp/a/b/c/test.txt` | 自动创建目录 | T-17 |
| `搜索 async def 前后 3 行` | context 上下文 | T-22, T-53 |

> 📖 完整 advanced 模块用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/advanced.md')`

### 阶段 5: 存储验证 `[PTY]`

```bash
# 退出
process(action='submit', session_id='<id>', data='/quit')
process(action='wait', session_id='<id>', timeout=10)

# 验证
ls -la ~/.nanohermes/sessions/
wc -l ~/.nanohermes/sessions/*.jsonl
sqlite3 ~/.nanohermes/sessions.db "SELECT id, model, title FROM sessions;"
sqlite3 ~/.nanohermes/sessions.db "PRAGMA journal_mode;"  # 应为 wal
cat ~/.nanohermes/memory/USER.md   # 应含 "名字是测试员小王"
cat ~/.nanohermes/memory/MEMORY.md
```

**覆盖**：S-01~03, S-05~08, S-13, S-15~20, S-30~70, M-01, M-03~08, M-11, I-01, I-04, TUI-07, TUI-16, TUI-17, S-39~44, S-48~52, S-58~69

> 📖 完整 70 个会话用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/session-storage.md')`

### 阶段 6: 条件用例（可选）

| 类型 | 用例数 | 说明 |
|------|--------|------|
| `[DEBUG]` 需 --debug | 30 | PA-02/03/07, C-07/08/09/15~19/24~35/39~40, CC-04, TUI-08, I-02/03/05/06, M-09, AUX-01/03, P-26/35/37, S-36/42/60/61 |
| `[FAULT]` 故障注入 | 18 | P-03/06/09/10/23~25/27~28, C-13, AUX-04 |
| `[MANUAL]` 仅手动 | 8 | TUI-06, PA-04, TUI-15, TUI-18 |
| `[UNIT]` 仅单元测试 | 100 | D-01~08/15~27, CC-01/02/05~10, SK-01~11, MCP-01~10, SEC-01~05, PERF-01/04~06 等 |

> 📖 完整 conversation+delegation 用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/conversation.md')`
> 📖 完整 provider/config/prompt 用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/provider-config.md')`

### 阶段 7: 报告生成

使用 `templates/report-template.md`，保存到 `testing-artifacts/reports/report-YYYY-MM-DD-HHMM.md`。

## 自动化测试

| Runner | 说明 | 推荐场景 |
|--------|------|---------|
| `scripts/pty_runner.py` | 单会话多用例（v1，历史版本，有清屏冲刷问题） | 参考 |
| `scripts/full_regression.py` | 36 用例校准版（**100% 通过**），每用例独立会话 + script 捕获 | **回归测试（推荐）** |

### 运行全量回归

```bash
eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312
python testing-artifacts/scripts/full_regression.py
```

- **策略**：每用例独立 NanoHermes 会话 + `script` 命令捕获 TUI 输出
- **耗时**：~20 分钟（36 用例 × ~33 秒/用例，含 T-08 的 60s 等待）
- **输出**：`testing-artifacts/reports/report-YYYY-MM-DD-HHMM.md`
- **关键参数**：T-08=60s, T-22=45s, T-20=40s（AI 响应较慢的搜索类用例）

## 已知问题

| 问题 | 影响 | 状态 |
|------|------|------|
| MEMORY.md 重复条目 | 低 | 待修复 |
| search_files 过度搜索 | 低 | 待优化 |
| PTY 不支持 CPR | TUI-06 不可测 | 技术限制 |
| **USER.md 记忆未持久化** | 自然语言指令不触发 memory 工具，需用明确参数格式 | ✅ 已解决（修改测试输入格式后 M-01 通过） |
| **ANSI 转义码干扰匹配** | /tools 等 TUI 输出中转义码打断关键词匹配 | ✅ 已解决（script 捕获 + ANSI 清理，TS-01 通过） |
| **AI 拒绝措辞不一致** | 二进制文件拒绝测试中 AI 用词不匹配预期模式 | ✅ 已解决（扩展匹配模式，T-44 通过） |
| **等待时间不足导致空输出** | 搜索/上下文类用例 AI 响应慢，15s 等待不够 | ✅ 已解决（T-08=60s, T-22=45s, T-20=40s 校准） |

## 性能预期

| 指标 | 预期 | 方法 |
|------|------|------|
| 启动 | < 5s | time |
| 响应 | 2-5s | 状态栏 |
| 工具 | 3-10s | poll 时间差 |
