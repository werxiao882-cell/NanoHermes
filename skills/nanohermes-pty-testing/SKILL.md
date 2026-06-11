---
name: nanohermes-pty-testing
description: "真实 PTY 端到端测试 NanoHermes — 7 阶段流程 + 530 用例（370 PTY 可直接执行）"
version: 5.2.0
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

**标记说明**：`[PTY]` 直接可执行(370) | `[DEBUG]` 需 --debug(34) | `[FAULT]` 故障注入(11) | `[MANUAL]` 仅手动(5) | `[UNIT]` 仅单元测试(110)

**总计 530 用例**，按 7 阶段执行。详细用例清单按需加载 reference 文件：

| Reference | 模块 | 用例数 | 何时加载 |
|-----------|------|--------|---------|
| `references/core-tools.md` | tool-runtime(141) | 141 | 阶段 3-4 执行工具测试时 |
| `references/session-storage.md` | session-storage(113) | 113 | 阶段 5 验证存储时 |
| `references/memory-system.md` | memory-system(12) | 12 | 阶段 3.2 + 阶段 5 |
| `references/provider-config.md` | provider(37) + config(11) + prompt(8) | 56 | 阶段 2 启动验证 + 阶段 6 |
| `references/conversation.md` | conversation-loop(70) + delegation(12) | 82 | 阶段 3 + 阶段 6 |
| `references/cli-tui.md` | cli/TUI(18) | 18 | 阶段 3.3 + 阶段 2 |
| `references/advanced.md` | skills(18) + compression(16) + insights(14) + mcp(10) + auxiliary(10) | 103 | 阶段 4 + 阶段 6 |

## 输出目录规范

`testing-artifacts/{reports,scripts,logs}`，永不删除历史，冲突追加序号。

## 错误自动修复策略

**核心原则**：测试执行中碰到错误不要停止，自动分析原因并修复，修复后继续执行。

### 修复流程

```
1. 检测错误（命令失败/输出不符/进程崩溃）
   ↓
2. 分析错误原因（查看完整日志、检查状态）
   ↓
3. 尝试修复（清缓存/改配置/重试/跳过）
   ↓
4. 验证修复是否成功
   ↓
5. 成功 → 继续执行下一阶段
   失败 → 记录错误，标记用例为"修复失败"，继续后续用例
```

### 常见错误及自动修复方法

| 错误类型 | 症状 | 自动修复方法 |
|---------|------|-------------|
| 启动崩溃 | 进程启动后立即退出 | 1. `rm -rf src/__pycache__ src/*/__pycache__`<br>2. 检查 Python 语法 `python -m py_compile src/main.py`<br>3. 检查依赖 `python -c "import openai, yaml, rich"`<br>4. 重试启动 |
| 依赖缺失 | ImportError/ModuleNotFoundError | `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <missing_package>` |
| 配置错误 | 启动报配置验证失败 | 检查 `nanohermes.json` 格式，修复 JSON 语法错误 |
| API Key 无效 | 401/403 认证错误 | 检查 `.env` 文件中 API Key 是否正确，跳过需真实 API 的用例 |
| 端口占用 | Address already in use | `lsof -ti:8000 | xargs kill -9` 或换端口 |
| 数据库锁定 | database is locked | 1. 等待 5 秒重试<br>2. `rm -f ~/.nanohermes/sessions.db-journal`<br>3. 检查是否有其他进程占用 |
| 文件权限 | Permission denied | `chmod +rw <file>` 或使用 `/tmp/` 目录替代 |
| 输出不符预期 | 工具返回与预期不同 | 1. 使用 `process(action='log')` 查看完整输出<br>2. 检查是否缓冲截断<br>3. 调整等待时间 `sleep` 参数 |
| PTY 渲染问题 | CPR 序列乱码 | PTY 不支持 CPR 是技术限制，标记 TUI-06 为不可测，继续其他用例 |
| 超时 | 命令执行超过预期时间 | 1. 增加 timeout 参数<br>2. 检查是否死循环<br>3. 强制终止并标记用例 |

### 修复约束

1. **最大修复次数**：同一错误最多尝试修复 3 次，超过则标记为"修复失败"并继续
2. **修复日志**：每次修复操作记录到 `testing-artifacts/logs/fix-log.md`
3. **不要回退**：修复后不要回到阶段开头，从失败点继续执行
4. **记录状态**：修复后更新用例状态（通过/失败/跳过）
5. **批量修复**：同类错误一次性修复所有相关用例

### 修复日志格式

```markdown
## 修复记录 [时间]
- **错误用例**: [ID]
- **错误类型**: [类型]
- **错误详情**: [完整错误信息]
- **修复操作**: [执行的修复命令]
- **修复结果**: 成功/失败
- **后续动作**: 继续执行 [下一个用例 ID]
```

## 进度汇报规范（强制执行）

**测试执行期间，必须每 30 秒向用户汇报一次进度！**
- 首次启动后立刻告知用户
- 每 30 秒轮询一次进度并发送
- 汇报内容：当前阶段、已跑用例数、日志行数、正在执行的测试
- 禁止闷头跑超过 30 秒不汇报
- 用户说"什么情况了"说明汇报频率不够，立刻加频
- 汇报方式：直接用消息告诉用户当前状态

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
| test_integration.py 导入失败 | 中 | `src.tools.toolsets` 模块不存在，需修复测试 |

## 修复历史

| 日期 | 问题 | 修复内容 | 状态 |
|------|------|---------|------|
| 2026-06-10 | SQLite 计数器为 0 | insert_message 自动 increment_message_count；_on_tool_start 调用 increment_tool_call_count | ✅ 已修复 |
| 2026-06-10 | TUI 测试失败（16 个） | TUIApp 添加 session_db/jsonl_store/memory_manager/skill_manager 注入参数 | ✅ 已修复 |
| 2026-06-10 | TS-01 `/tools` 匹配失败 | 改用 `script` 命令捕获终端输出 + 增强 ANSI 清理逻辑 | ✅ 已修复 |
| 2026-06-10 | T-44 二进制措辞不匹配 | 放宽正则：`binary|二进制|非文本|无法读取|不支持|拒绝|deny|cannot|image|图片|png` | ✅ 已修复 |
| 2026-06-10 | T-16 行号格式不匹配 | AI 用自然语言回复，改用 `第.*1.*行|1\||行.*1` 宽松匹配 | ✅ 已修复 |
| 2026-06-10 | T-08/T-20/T-22/S-03 等待超时 | 增加等待时间：T-08=60s, T-20=40s, T-22=45s, S-03=20s | ✅ 已修复 |

## PTY 验证最佳实践（重要！）

### 核心陷阱：TUI 输出捕获

NanoHermes 的 TUI 使用 Rich 框架渲染，会产生大量 ANSI 转义序列（清屏、光标控制、颜色）。
**pexpect 的 `child.before` / `child.after` 不可靠**——TUI 清屏后输出被清空，导致捕获内容为空。

**✅ 正确方案：使用 `script` 命令捕获**

```python
import pexpect

child = pexpect.spawn(
    'bash',
    args=['-c', 'eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312 && cd /mnt/d/code/NanoHermes && script -q -c "python -m src.main" /tmp/test_output.log'],
    encoding='utf-8',
    timeout=120,
)

time.sleep(12)  # 等待启动 + TUI 渲染
child.sendline("/tools")
time.sleep(15)  # 等待 AI 响应
child.close(force=True)

# 从 script 输出文件读取
with open('/tmp/test_output.log', 'r', encoding='utf-8', errors='replace') as f:
    raw_output = f.read()
```

### ANSI 清理（必须在正则匹配前执行）

```python
import re

def clean_ansi(text):
    """移除所有 ANSI 转义序列，保留纯文本。"""
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)       # CSI 序列（颜色、光标）
    text = re.sub(r'\x1b\[\?[0-9]+[a-z]', '', text)          # DEC 私有模式
    text = re.sub(r'\x1b\][0-9];.*?\x07', '', text)          # OSC 序列
    text = re.sub(r'\x08', '', text)                          # 退格符
    text = re.sub(r'\r\n', '\n', text)                        # 统一换行符
    return text
```

### 等待时间指南

| 阶段 | 等待时间 | 说明 |
|------|---------|------|
| 启动 + TUI 渲染 | 12 秒 | Rich 需要时间渲染工具列表面板 |
| 发送命令后 | 15-25 秒 | AI 思考 + 工具调用 + 响应 |
| 复杂工具（execute_code） | 25-40 秒 | 代码执行需要额外时间 |
| 获取提示符返回 | +3 秒 | 发送空行后等待 |

### 验证模式指南

**TS-01（deferred 标记）**：
```python
# 预期输出包含：
r'deferred'        # 延迟加载标记
r'loaded'          # 已加载标记
r'memory.*deferred' # memory 是 deferred
r'terminal.*loaded' # terminal 是 loaded
```

**T-44（二进制文件拒绝）**：
```python
# AI 可能用多种措辞拒绝，匹配要宽泛：
r'binary|二进制|非文本|无法读取|不支持|拒绝|deny|cannot|image|图片|png'
```

**M-01（memory 工具调用）**：
```python
# 必须显式指令 AI 调用工具，否则 AI 倾向文本回复
# 测试输入："请使用 memory 工具，在 user 记忆中写入：测试用户偏好"
# 验证：检查 ~/.nanohermes/memory/USER.md 文件内容
```

### 已知不可靠的捕获方式

| 方式 | 问题 | 替代方案 |
|------|------|---------|
| `child.before` / `child.after` | TUI 清屏后为空 | 使用 `script` 命令写入文件 |
| `terminal(background=True, pty=True)` | 输出缓冲截断 | 使用 `script` + 文件读取 |
| 管道 `| cat` | PTY 特性丢失 | 不要使用管道 |

## 性能预期

| 指标 | 预期 | 方法 |
|------|------|------|
| 启动 | < 5s | time |
| 响应 | 2-5s | 状态栏 |
| 工具 | 3-10s | poll 时间差 |
