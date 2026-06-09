---
name: nanohermes-pty-testing
description: "真实 PTY 端到端测试 NanoHermes — 7 阶段流程 + 202 用例（按需加载 reference）"
version: 4.0.0
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

**标记说明**：`[PTY]` 直接可执行(120) | `[DEBUG]` 需 --debug(18) | `[FAULT]` 故障注入(12) | `[MANUAL]` 仅手动(8) | `[UNIT]` 仅单元测试(44)

**总计 202 用例**，按 7 阶段执行。详细用例清单按需加载 reference 文件：

| Reference | 模块 | 用例数 | 何时加载 |
|-----------|------|--------|---------|
| `references/core-tools.md` | tool-runtime(54) + tool-search(6) | 60 | 阶段 3-4 执行工具测试时 |
| `references/session-storage.md` | session-storage(20) | 20 | 阶段 5 验证存储时 |
| `references/memory-system.md` | memory-system(12) | 12 | 阶段 3.2 + 阶段 5 |
| `references/provider-config.md` | provider(15) + config(11) + prompt(8) | 34 | 阶段 2 启动验证 + 阶段 6 |
| `references/conversation.md` | conversation-loop(20) + delegation(8) | 28 | 阶段 3 + 阶段 6 |
| `references/cli-tui.md` | cli/TUI(18) | 18 | 阶段 3.3 + 阶段 2 |
| `references/advanced.md` | skills(11) + compression(10) + insights(7) + mcp(10) + auxiliary(6) | 44 | 阶段 4 + 阶段 6 |

## 输出目录规范

`testing-artifacts/{reports,scripts,logs}`，永不删除历史，冲突追加序号。

## 7 阶段测试流程

### 阶段 1: 环境准备 `[PTY]`

```bash
eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312
cd /mnt/d/code/NanoHermes
rm -rf ~/.nanohermes/sessions/* ~/.nanohermes/sessions.db* ~/.nanohermes/memory/*
mkdir -p testing-artifacts/{reports,scripts,logs}
```

**验证门**：`python -c "import openai, yaml, rich, sqlite3; print('OK')"` → 通过。
**覆盖**：CF-01, CF-04, CF-06, CF-09, CF-11

### 阶段 2: 启动验证 `[PTY]`

```python
terminal(command="eval \"$($HOME/miniconda3/bin/conda shell.bash hook)\" && conda activate py312 && cd /mnt/d/code/NanoHermes && python -m src.main", background=True, pty=True)
terminal(command="sleep 10")
process(action='poll', session_id='<id>')
```

**验证门**：进程 running | 工具列表(6 loaded + 11 deferred) | CPR 警告非阻塞 | 状态栏正常
**⚠️ 陷阱**：启动崩溃先清 `__pycache__`；`status_bar` 需在 `self.model` 赋值后创建
**覆盖**：CF-02, CF-03, CF-05, CF-07, CF-10, TUI-01, P-04, P-11, P-12, PA-01, PA-06, S-12, S-16, S-17

> 📖 完整 provider/config/prompt 用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/provider-config.md')`
> 📖 完整 cli/TUI 用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/cli-tui.md')`

### 阶段 3: 基础对话 + 工具链（核心）

#### 3.1 基础对话 `[PTY]`

```
你好 → 正常回复，Thought 可见，3-5s 响应
```

**覆盖**：P-01, P-02, P-05, P-07, P-08, C-01, TUI-02, TUI-03, TUI-13, TUI-14

#### 3.2 工具链 `[PTY]` — 严格按序

| 序号 | 测试输入 | 预期 | 覆盖 |
|------|---------|------|------|
| 1 | `运行 echo hello` | "hello" | T-02 |
| 2 | `运行 false` | exit code 1 | T-14 |
| 3 | `创建 /tmp/nanotest.txt 写入 "Hello NanoHermes"` | 16 bytes | T-05 |
| 4 | `读取 /tmp/nanotest.txt` | "Hello NanoHermes" | T-04 |
| 5 | `把 Hello 替换为 Hi` | 替换成功 | T-06, T-18 |
| 6 | `再读一次确认` | "Hi NanoHermes" | C-02 |
| 7 | `读第 1 行(offset=1,limit=1)` | 分页读取 | T-16 |
| 8 | `搜索含 class 的 Python 文件` | 匹配列表 | T-07, T-08, TS-02 |
| 9 | `计算 100 以内质数和` | 1060 | T-10 |
| 10 | `记住名字是测试员小王` | memory success | M-02, T-27 |
| 11 | `问我一个问题` | clarify 选择题 | T-12, T-36 |
| 12 | `创建 TODO：测试 PTY` | todo 成功 | T-33, T-34 |

**⚠️ 陷阱**：3→4→5→6 是依赖链必须按序；execute_code 预期 1060

> 📖 完整 60 个工具用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/core-tools.md')`
> 📖 完整 12 个记忆用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/memory-system.md')`

#### 3.3 TUI 命令 `[PTY]`

```
/tools → 工具列表(loaded/deferred) | /sessions → 当前会话 | /skills → 技能列表
/status → 状态 | /clear → 清屏
```

**覆盖**：T-01, TS-01, TUI-05, S-04, S-11, SK-01, SK-07, TUI-09~12

#### 3.4 上下文 + 错误 + 边界 `[PTY]`

```
刚才创建的文件内容是什么？  → 正确识别 /tmp/nanotest.txt
读取 /tmp/不存在的文件.txt  → 友好提示，对话不中断
测试特殊字符 🎉 <>&"'  → 正常处理
```

**覆盖**：C-04, S-09, S-10, T-09, C-05, PA-08, M-10

### 阶段 4: 高级场景 `[PTY]`

| 测试输入 | 预期 | 覆盖 |
|---------|------|------|
| `搜索含 "async def" 的文件` | BM25/Regex 结果 | TS-02, TS-03, TS-04 |
| `找不存在的工具 run_spell` | 友好提示 | TS-06, T-43 |
| `搜索只返回文件路径 *.py` | files_only | T-20 |
| `搜索统计含 class 的文件数` | count 模式 | T-21 |
| 大文件输出 | 自动截断 | T-11, CC-03, T-39 |
| `创建 /tmp/a/b/c/test.txt` | 自动创建目录 | T-17 |
| `搜索 async def 前后 3 行` | context 上下文 | T-22 |

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

**覆盖**：S-01~03, S-05~08, S-13, S-15~20, M-01, M-03~08, M-11, I-01, I-04, TUI-07, TUI-16, TUI-17

> 📖 完整 20 个会话用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/session-storage.md')`

### 阶段 6: 条件用例（可选）

| 类型 | 用例数 | 说明 |
|------|--------|------|
| `[DEBUG]` 需 --debug | 18 | PA-02/03/07, C-07/08/09/15~19, CC-04, TUI-08, I-02/03/05/06, M-09, AUX-01/03 |
| `[FAULT]` 故障注入 | 12 | P-03/06/09/10, C-13, AUX-04 |
| `[MANUAL]` 仅手动 | 8 | TUI-06, PA-04, TUI-15, TUI-18 |
| `[UNIT]` 仅单元测试 | 44 | D-01~08, CC-01/02/05~10, SK-01~11, MCP-01~10, SEC-01~05, PERF-01/04~06 等 |

> 📖 完整 conversation+delegation 用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/conversation.md')`
> 📖 完整 provider/config/prompt 用例加载 `skill_view(name='nanohermes-pty-testing', file_path='references/provider-config.md')`

### 阶段 7: 报告生成

使用 `templates/report-template.md`，保存到 `testing-artifacts/reports/report-YYYY-MM-DD-HHMM.md`。

## 已知问题

| 问题 | 影响 | 状态 |
|------|------|------|
| MEMORY.md 重复条目 | 低 | 待修复 |
| search_files 过度搜索 | 低 | 待优化 |
| PTY 不支持 CPR | TUI-06 不可测 | 技术限制 |

## 性能预期

| 指标 | 预期 | 方法 |
|------|------|------|
| 启动 | < 5s | time |
| 响应 | 2-5s | 状态栏 |
| 工具 | 3-10s | poll 时间差 |
