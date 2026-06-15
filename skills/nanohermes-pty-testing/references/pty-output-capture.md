# TUI 输出捕获 — pexpect vs script 对比

## 问题

NanoHermes TUI 使用 Textual 框架渲染，启动时会发送一系列 ANSI 控制序列：
- `\x1b[2J` — 清屏
- `\x1b[H` — 光标归位
- `\x1b[J` — 清除光标以下
- `\x1b[?7l` / `\x1b[?7h` — 自动换行关闭/开启
- `\x1b[?25l` / `\x1b[?25h` — 光标隐藏/显示

这些序列导致 `pexpect.spawn().before` 缓冲区被清空，捕获到的输出为空字符串。

## 两种方案对比

### ❌ 方案一：pexpect 直接捕获

```python
child = pexpect.spawn('python -m src.main', encoding='utf-8')
child.expect(r'prompt', timeout=30)
output = child.before  # ❌ 空字符串（被清屏序列冲刷）
```

**失败原因**：Textual 启动时发送清屏序列，pexpect 的匹配消费了缓冲区中直到匹配点的所有内容，但清屏序列之后的内容被 TUI 持续输出覆盖。

### ✅ 方案二：script 命令捕获

```python
child = pexpect.spawn(
    'bash',
    args=['-c', 'script -q -c "python -m src.main" /tmp/output.log'],
    encoding='utf-8',
)
time.sleep(12)  # 等待 TUI 渲染
child.sendline('/tools')
time.sleep(15)  # 等待 AI 响应
child.close(force=True)

with open('/tmp/output.log', 'r') as f:
    output = f.read()  # ✅ 完整 TUI 内容
```

**成功原因**：`script` 命令在伪终端外层录制所有 I/O，相当于终端会话的"录像机"，不受应用层清屏序列影响。

## ANSI 清理

捕获到的原始输出包含 ANSI 转义码，验证前必须清理：

```python
import re

def clean_ansi(text):
    """移除 ANSI 转义序列"""
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)  # CSI 序列
    text = re.sub(r'\x1b\[\?[0-9]+[a-z]', '', text)    # DEC 私有模式
    text = re.sub(r'\x1b\][0-9];.*?\x07', '', text)    # OSC 序列
    text = re.sub(r'\x08', '', text)                     # 退格
    text = re.sub(r'\r\n', '\n', text)                   # 换行统一
    return text
```

## Runner 脚本

改进版 PTY runner 见 `scripts/pty_runner_v2.py`，已集成 `script` 捕获模式。
