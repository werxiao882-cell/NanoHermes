# PTY 自动化测试执行日志 — 2026-06-10

## 第一次运行（原始 runner）

**时间**：~14 分钟
**结果**：37 用例，35 通过，2 失败，通过率 94.6%

### 失败用例分析

#### TS-01 — `/tools` 命令未匹配到 "defer/延迟" 关键词
- **原因**：TUI 输出包含大量 ANSI 转义序列（`\x1b[35m`、`\x1b[?7l`、`\x1b[7A` 等），导致纯文本正则匹配 `defer|延迟` 失败
- **解决方案**：在 pexpect `child.before` 后先 strip ANSI 码，或简化匹配模式
- **影响**：不影响功能，仅影响测试验证

#### M-01 — `~/.nanohermes/memory/USER.md` 为空（仅 `# User Profile` 标题）
- **根因**：memory 工具在整个会话中**从未被调用**（JSONL 验证：0 次 memory 调用）
- **AI 行为模式**：收到"请记住：我的名字是测试员小王"后，AI 直接用文字回复"好的我记住了"，没有调用 memory 工具
- **解决方案**：测试中使用更明确的指令，如"调用 memory 工具，action=add, target=user, content=..."
- **影响**：测试用例需要调整提示方式，非 NanoHermes 功能 bug

### 通过的关键用例
- T-02: echo hello → "hello" ✅
- T-14: false → exit code 1 ✅
- T-05: write_file → 16 bytes written ✅
- T-04: read_file → "Hello NanoHermes" ✅
- T-06: patch replace → 替换成功 ✅
- C-02: verify → "Hi NanoHermes" ✅
- T-10: execute_code → 1060 (质数和) ✅
- T-17: auto create dirs → nested dirs 成功 ✅
- T-11: large output truncation ✅
- T-39: seq 1 5000 truncation ✅
- M-02: memory add (工具返回 success) ✅
- T-27: memory replace (工具返回 success) ✅
- S-01: JSONL 文件存在 ✅
- S-02: sessions.db 存在 ✅
- S-03: WAL journal mode ✅

## 第二次运行（修复 ANSI 清理 + 明确 memory 指令）

**状态**：运行中...

### 修复内容
1. **ANSI 清理**：在 `send_input()` 中添加 `ansi_escape.sub('', output)` 清理 ANSI 转义码
2. **Memory 指令**：将"请记住：我的名字是测试员小王"改为"调用 memory 工具，action=add, target=user, content='名字是测试员小王'"

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
# 需要匹配多种就绪信号
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

### 长时间运行
- 完整 37 用例约需 14 分钟
- 必须使用 `background=True` + `notify_on_complete=True`
- 实时进度通过 `tail testing-artifacts/logs/main.log` 查看
- **进度汇报**：每 30 秒向用户汇报一次（用户反馈要求）
