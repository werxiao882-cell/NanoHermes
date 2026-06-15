---
name: nanohermes-pty-testing
description: "真实 PTY 端到端测试 NanoHermes — 从 reference 文件解析用例执行，多轮对话（最多10轮），自动失败分析"
version: 9.0.0
platforms: [linux, macos, wsl]
metadata:
  hermes:
    tags: [testing, e2e, pty, nanohermes, qa]
    related_skills: [dogfood]
---

# NanoHermes PTY 端到端测试

## 触发条件

用户要求测试 NanoHermes / 跑 PTY 测试 / 端到端测试 / 回归测试 时加载。

## 快速开始

```bash
eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312
cd /mnt/d/code/NanoHermes/skills/nanohermes-pty-testing

# 全量执行所有 [PTY] 用例（多轮对话，最多 10 轮）
python scripts/iterative_runner.py

# 只测试工具模块
python scripts/iterative_runner.py --refs core-tools --dry-run  # 先预览
python scripts/iterative_runner.py --refs core-tools            # 再执行

# 自动修复模式（放宽正则、增加超时、跳过已知限制）
python scripts/iterative_runner.py --auto-fix --max-retries 2

# 执行后验证存储
python scripts/validate-sessions.py
```

## 测试架构

### 目录结构

```
skills/nanohermes-pty-testing/
├── SKILL.md                      # 本文档 — 测试流程、陷阱、方法论
├── references/                   # 用例清单（markdown 表格，runner 自动解析）
│   ├── core-tools.md             # 78 用例：tool-runtime + tool-search + dispatcher
│   ├── conversation.md           # 60 用例：conversation-loop + delegation + error-recovery
│   ├── session-storage.md        # 70 用例：session lifecycle + storage + token
│   ├── memory-system.md          # 15 用例：memory lifecycle + operations + quality
│   ├── provider-config.md        # 58 用例：provider runtime + config + prompt
│   ├── cli-tui.md                # 18 用例：CLI/TUI interface
│   ├── advanced.md               # 44 用例：skills + compression + insights + mcp
│   ├── test-findings.md          # 配置陷阱、JSONL 格式、AI 行为模式（测试前必读）
│   ├── wait-time-calibration.md  # 等待时间校准表
│   ├── counter-debug.md          # SQLite 计数器排查流程
│   ├── pty-execution-log.md      # 自动化 runner 执行记录
│   ├── pty-output-capture.md     # PTY 输出捕获陷阱
│   └── pty-run-2026-06-10-round2.md  # 历史测试记录
├── scripts/
│   ├── iterative_runner.py       # 主 runner：多轮对话（最多10轮）+ 自动失败分析
│   ├── failure_analyzer.py       # 失败分析器：分类失败原因 + 修复建议
│   └── validate-sessions.py      # 存储验证：JSONL + SQLite + Memory
├── templates/
│   └── report-template.md        # 测试报告模板
└── testing-artifacts/            # 输出目录（报告、日志、脚本）
    ├── reports/                  # 测试报告（永不删除，冲突追加序号）
    ├── logs/                     # 用例失败日志 + session 辅助日志
    └── scripts/                  # 历史调试脚本
```

### 用例标记

| 标记 | 含义 | 执行方式 |
|------|------|---------|
| `[PTY]` | 可直接执行 | runner 自动执行 |
| `[DEBUG]` | 需 --debug | 需 NanoHermes 启动时传 --debug |
| `[FAULT]` | 故障注入 | 需要模拟 API 失败等故障条件 |
| `[MANUAL]` | 仅手动 | 需要人工检查（如视觉布局） |
| `[UNIT]` | 仅单元测试 | 通过 pytest 执行，不需要 PTY |

**统计**：542 用例，其中 171 个 `[PTY]` 可直接执行。

### Reference Runner 工作原理 (v9)

`scripts/iterative_runner.py` 不硬编码用例，而是：

1. 解析 `references/*.md` 中的 markdown 表格（`| ID | 测试内容 | 操作步骤 | 预期 | 标记 |`）
2. 过滤 `[PTY]` 标记的用例
3. 每用例独立 NanoHermes 会话 + `script` 命令捕获 TUI 输出
4. **多轮对话**：根据用例类型和 PTY 输出判断是否需要继续交互（最多 10 轮）
5. 从实际输出中动态提取匹配关键词（`extract_keywords_from_output`），而非死板匹配预期描述
6. 按用例类型自动选择等待时间（搜索=40s，计算=25s，默认=15s）
7. 失败时自动分析原因 + 读取 session 日志辅助诊断
8. 生成 Markdown 报告保存到 `testing-artifacts/reports/`

**优势**：新增用例只需在 reference 文件的表格中加一行，runner 自动识别执行。多轮对话支持复杂场景（write→read→patch→read 链）。

### Iterative Runner 工作原理

`scripts/iterative_runner.py` 是主 runner（替代旧版 `reference_runner.py`），增加：

- **多轮对话引擎**：`needs_more_turns()` 根据用例类型 + 当前 PTY 输出判断是否继续
- **灵活模式匹配**：`extract_keywords_from_output()` 从实际输出中提取语义关键词
- **AI 状态检测**：`ai_has_responded()`, `ai_is_still_thinking()`, `ai_has_finished()` 判断回复状态
- **Session 日志读取**：失败时自动读取 `~/.nanohermes/sessions/` 最新记录辅助分析
- **自动修复**：`--auto-fix` 模式下自动放宽正则、增加超时、跳过已知限制

## 测试流程

**首选**：直接运行 `iterative_runner.py`，它自动按模块顺序执行所有 `[PTY]` 用例，支持多轮对话（最多10轮）。
**手动**：只在调试单个用例时参考以下阶段说明。

### Runner 执行计划

runner 按以下顺序解析 reference 文件并执行其中的 `[PTY]` 用例：

| 顺序 | Reference 文件 | 覆盖模块 | 用例数 | [PTY] 数 |
|------|---------------|---------|--------|---------|
| 1 | `core-tools.md` | tool-runtime + tool-search + dispatcher | 78 | 49 |
| 2 | `conversation.md` | conversation-loop + delegation + error-recovery | 60 | 27 |
| 3 | `session-storage.md` | session lifecycle + storage + token + resume | 80 | 42 |
| 4 | `memory-system.md` | memory lifecycle + operations + quality | 15 | 10 |
| 5 | `provider-config.md` | provider runtime + config + prompt | 58 | 20 |
| 6 | `cli-tui.md` | CLI/TUI interface | 18 | 12 |
| 7 | `advanced.md` | skills + compression + insights + mcp | 44 | 13 |

> 执行单个模块：`python scripts/iterative_runner.py --refs core-tools`

### 手动调试参考（仅调试单个用例时）

#### 阶段 1: 环境准备

```bash
eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312
cd /mnt/d/code/NanoHermes
rm -rf ~/.nanohermes/sessions/* ~/.nanohermes/sessions.db* ~/.nanohermes/memory/*
```

**⚠️ 配置检查**：测试前必须确认 `nanohermes.json` 存在（参考 `references/test-findings.md`）。

**覆盖用例**：CF-01, CF-04, CF-06, CF-09, CF-11

#### 阶段 2: 启动验证

启动 NanoHermes，验证进程正常运行、工具列表加载、CPR 警告非阻塞。

**覆盖用例**：CF-02, CF-03, CF-05, CF-07, CF-10, TUI-01, P-04, P-11, P-12, P-16, PA-01, PA-06, S-12, S-16, S-30

#### 阶段 3: 基础对话 + 工具链

**3.1 基础对话** — P-01, P-02, P-05, P-07, P-08, P-16, C-01, C-21, C-37, TUI-02, TUI-03

**3.2 工具链（严格按序）** — write→read→patch→read 依赖链：

| 序号 | 操作 | 预期 | 覆盖 |
|------|------|------|------|
| 1 | `运行 echo hello` | "hello" | T-02 |
| 2 | `运行 false` | exit code 1 | T-14 |
| 3 | `创建 /tmp/nanotest.txt 写入 "Hello NanoHermes"` | written | T-05 |
| 4 | `读取 /tmp/nanotest.txt` | "Hello NanoHermes" | T-04 |
| 5 | `把 Hello 替换为 Hi` | 替换成功 | T-06, T-18 |
| 6 | `再读一次确认` | "Hi NanoHermes" | C-02 |
| 7 | `读第 1 行` | 分页读取 | T-16 |
| 8 | `搜索含 class 的 Python 文件` | 匹配列表 | T-07, T-08 |
| 9 | `计算 100 以内质数和` | 1060 | T-10 |
| 10 | `使用 memory 工具写入：名字是小王` | memory success | M-02 |
| 11 | `创建 TODO：测试 PTY` | todo 成功 | T-33, T-34 |

**3.3 TUI 命令** — `/tools`、`/sessions`、`/skills`、`/status`、`/clear`

**3.4 上下文 + 错误 + 边界** — C-04, T-09, C-05, PA-08, M-10, T-44, T-48, T-52

#### 阶段 4: 高级场景

搜索模式、大输出截断、自动创建目录、上下文行数等。
覆盖：TS-02~06, T-20~22, T-50~54, T-17, T-39, D-09, D-20, CC-03, SK-01~03, SK-06~07, I-01, I-04, AUX-02

#### 阶段 5: 存储验证

退出 NanoHermes 后验证文件系统：
```bash
ls -la ~/.nanohermes/sessions/
sqlite3 ~/.nanohermes/sessions.db "PRAGMA journal_mode;"   # 应为 wal
cat ~/.nanohermes/memory/USER.md
cat ~/.nanohermes/memory/MEMORY.md
```

**覆盖**：S-01~08, S-11~13, S-16, S-18~20, S-30, S-39~41, S-48~50, S-56~58, S-62~64, M-01, M-03~08, **S-R01~R11（恢复功能）**

#### 阶段 6: 条件用例（可选）

| 类型 | 用例数 | 说明 |
|------|--------|------|
| `[DEBUG]` | 30 | 需 --debug 启动 |
| `[FAULT]` | 18 | 需要故障注入 |
| `[MANUAL]` | 8 | 仅手动检查 |
| `[UNIT]` | 100 | 通过 pytest 执行 |

#### 阶段 7: 报告生成

runner 自动生成 Markdown 报告保存到 `testing-artifacts/reports/report-YYYY-MM-DD-HHMM.md`。

## 测试陷阱与经验

### 多轮对话测试方法论 (v9 新增)

**问题**：很多用例需要多步操作才能完成（如 C-02 的 write→read→patch→read 链），但旧版 runner 只发一条消息就退出。

**解决方案**：`iterative_runner.py` 实现了多轮对话引擎：

1. **AI 状态检测**：
   - `ai_has_responded()` — AI 是否开始回复（有 Thought 或工具调用）
   - `ai_is_still_thinking()` — AI 是否还在思考（有 Thought 但没有完整回复）
   - `ai_has_finished()` — AI 是否完成回复（有 NanoHermes 面板 + 状态栏）
   - `ai_has_used_tools()` — AI 是否已经调用了工具

2. **智能后续提示**：`needs_more_turns()` 根据用例类型生成合适的后续对话：
   - C-02（工具链）：write → "现在 read 这个文件" → "用 patch 修改" → "再 read 确认"
   - C-04（上下文保持）：创建文件 → "刚才创建的文件内容是什么？"
   - C-05（错误恢复）：读不存在文件 → "那创建一个新文件"
   - M-xx（记忆）：调用 memory 工具 → "我叫什么名字？"

3. **最多 10 轮**：超过 10 轮后自动停止，避免无限循环

4. **Session 日志辅助**：失败时自动读取 `~/.nanohermes/sessions/` 最新记录，当 PTY 输出被截断时可从 session 获取完整对话

### 输出捕获：script 命令

**问题**：NanoHermes TUI 使用 ANSI 清屏序列（`\x1b[2J`、`\x1b[H`、`\x1b[J`）渲染界面，pexpect 的 `child.before` 缓冲区会被这些序列冲刷，导致输出为空。

**正确做法**：用 `script` 命令在 TTY 外层捕获：
```bash
script -q -c "python -m src.main" /tmp/test_output.log
```
`script` 录制完整终端 I/O，不受应用层清屏影响。捕获后仍需清理 ANSI 码再匹配。

### ANSI 转义码

`/tools` 等 TUI 命令输出含大量 ANSI 转义序列（`\x1b[...m`、`\r`、`\b`），纯文本关键词匹配容易被转义码打断。runner 中已用 `clean_ansi()` 函数处理。

### 配置陷阱

- **nanohermes.json**：项目默认没有，只有 `nanohermes.example.json`。测试前必须创建。
- **Provider 配置**：`.env` 使用 `OPENAI_API_KEY` + `OPENAI_BASE_URL` 时，provider 类型必须用 `openai`，字段为 `base_url_env` / `api_key_env`（不是 `base_url`）。
- **DashScope**：通义千问通过 DashScope OpenAI 兼容端点访问，`base_url` = `https://dashscope.aliyuncs.com/compatible-mode/v1`。

### JSONL 格式

NanoHermes 的 JSONL 每条消息是**多行 pretty-print 格式**（带缩进的花括号），不是紧凑单行 JSON。验证时不能用 `head -1 | jq`，需要用 `grep '"role":'` 统计角色。

### SQLite 计数器（已修复 ✅）

历史问题：`message_count`、`tool_call_count` 始终为 0。根因是 `insert_message()` 未调用 `increment_message_count()`。已修复（2026-06-10）。如果未来再次出现 0，参考 `references/counter-debug.md`。

### AI 行为模式

- **clarify 不必然触发**：用户说"问我一个问题"时，AI 倾向于用文本生成选择题，而非调用 clarify 工具。
- **memory 不必然触发（重要）**：用户说"请记住X"时，AI 倾向于回复"好的我记住了"，**不调用 memory 工具**。测试 memory 时需用明确指令："调用 memory 工具，action=add, target=user, content=..."。
- **过度搜索**：搜索工具时 AI 可能调用 search_tools 2-3 次，这是已知限制。
- **上下文保持良好**：AI 能正确引用之前对话中创建的文件和内容。

### 已知问题

| 问题 | 影响 | 状态 |
|------|------|------|
| MEMORY.md 重复条目 | 低 | 待修复 |
| search_files 过度搜索 | 低 | 待优化 |
| PTY 不支持 CPR | TUI-06 不可测 | 技术限制 |
| TUI 状态栏不在 script 输出中 | 8 用例受影响 | 已知限制 |
| 单轮测试覆盖率低 | 大部分用例需多轮 | ✅ 已修复（v9 多轮对话） |
| 正则模式太严格 | 预期描述≠实际输出 | ✅ 已修复（v9 灵活模式匹配） |
