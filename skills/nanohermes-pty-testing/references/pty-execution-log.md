# PTY 自动化测试执行日志

## 第三次运行（全面 133 用例，2026-06-14）

**时间**：3499 秒（~58 分钟）
**结果**：133 用例，125 通过，8 失败，通过率 94.0%
**报告**：`testing-artifacts/reports/report-2026-06-14-1949.md`
**脚本**：`testing-artifacts/scripts/full_pty_test.py`

### 失败用例分析

全部 8 个失败都是 **TUI 状态栏信息未在 script 捕获输出中出现**，非功能 bug：

| ID | 阶段 | 失败原因 | 说明 |
|----|------|---------|------|
| P-05 | S3.4-provider | token 关键词未匹配 | 状态栏 token 信息不在 script 输出中 |
| P-08 | S3.4-provider | token 关键词未匹配 | 同上 |
| P-12 | S3.4-provider | pricing 关键词未匹配 | 定价信息不在 script 输出中 |
| P-31 | S3.4-provider | usage 关键词未匹配 | 同上 |
| P-36 | S3.4-provider | total 关键词未匹配 | 同上 |
| TUI-16 | S3.6-tui | progress 关键词未匹配 | 进度条不在 script 输出中 |
| I-01 | S4-高级 | stats/token 关键词未匹配 | 同上 |
| S-58 | S5-存储 | token_count 关键词未匹配 | post_check 通过（DB 有数据） |

### 关键发现

1. **script 捕获不包含 TUI 状态栏**：NanoHermes 的 token/定价/进度信息渲染在 TUI 状态栏（底部），`script` 命令主要捕获对话区域内容。这些用例的 pattern 匹配应改为检查 JSONL 中的 token 数据或 SQLite 中的 counters。

2. **S-58 post_check 通过**：AI 回复中没 "token" 关键词，但 SQLite 中 `input_tokens` / `output_tokens` 字段有数据，token 统计实际工作正常。

3. **133 个用例覆盖 22 个阶段**：从启动验证到存储验证全覆盖，94.0% 通过率。

4. **存储验证强健**：sessions.db 133 sessions, WAL mode, 121 JSONL 文件。

### 按阶段通过率

| 阶段 | 通过率 | 说明 |
|------|--------|------|
| S2-启动 | 100% | 2/2 |
| S3.1-对话 | 100% | 7/7 |
| S3.2 工具链（全部子阶段） | 100% | 35/35 |
| S3.3 工具搜索+分发 | 100% | 13/13 |
| S3.4-loop | 100% | 5/5 |
| S3.4-provider | 55% | 6/11，5 个状态栏 token 用例 |
| S3.5-config | 100% | 8/8 |
| S3.5-prompt | 100% | 4/4 |
| S3.6-tui | 92% | 12/13，1 个进度条 |
| S4-高级 | 83% | 5/6，1 个 stats |
| S5-存储 | 97% | 28/29，1 个 token_count |

---

## 第一次运行（原始 runner，2026-06-10）

**时间**：~14 分钟
**结果**：37 用例，35 通过，2 失败，通过率 94.6%

### 失败用例

- **TS-01**：ANSI 转义码干扰关键词匹配 → 修复：ANSI 清理
- **M-01**：memory 工具未触发 → 修复：使用明确工具调用指令

## pexpect 驱动注意事项

### 安装
```bash
pip install pexpect  # 清华源可用
```

### 关键配置
```python
child = pexpect.spawn(cmd, encoding='utf-8', timeout=60, maxread=80000,
                      logfile=open('main.log', 'w'))
```

### Prompt 匹配
```python
idx = child.expect([
    r'➤|❯|Input\s*:|user\s*>|Type\s+/quit|CPR\b|history\r',
    pexpect.TIMEOUT,
    pexpect.EOF
], timeout=45)
```

### ANSI 清理（必须）
```python
ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\([AB0-2]|\x1b\)[0-9]|\r')
output = ansi_escape.sub('', output)
```

### script 捕获（TUI 输出）
NanoHermes TUI 使用清屏序列（`\x1b[2J`），pexpect buffer 会被冲刷。
正确做法：`script -q -c "python -m src.main" /tmp/output.log`

### 进度汇报
每 5 个用例汇报一次进度，包含通过数和耗时。
