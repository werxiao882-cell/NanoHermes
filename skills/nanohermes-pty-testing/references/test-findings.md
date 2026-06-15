# PTY 测试执行发现 — 2026-06-10

## 配置细节

### nanohermes.json 创建（测试前必须）

项目默认**没有** `nanohermes.json`，只有 `nanohermes.example.json`。测试前必须创建。

**当 .env 使用 `OPENAI_API_KEY` + `OPENAI_BASE_URL` 时**：

```json
{
  "model": {
    "provider": "openai",
    "name": "qwen3.6-plus"
  },
  "providers": {
    "openai": {
      "base_url_env": "OPENAI_BASE_URL",
      "api_key_env": "OPENAI_API_KEY"
    }
  },
  "tui": {
    "typing_speed": 10,
    "show_tool_panel": true,
    "tool_panel_position": "right"
  }
}
```

**关键**：provider 类型用 `openai`，字段用 `base_url_env` / `api_key_env`（不是 `base_url` / `api_key_env`）。

### .env 实际格式

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen3.6-plus
```

通义千问通过 DashScope OpenAI 兼容端点访问。

---

## JSONL 存储格式

### 实际格式：多行 pretty-print

```json
{
  "role": "user",
  "timestamp": 1781052950.5410993,
  "content": "运行 echo hello"
}
{
  "role": "assistant",
  "timestamp": 1781052955.123,
  "content": "...",
  "tool_calls": [...]
}
```

**不是**紧凑单行 JSONL。每条消息以 `{` 开头，以 `}` 结尾，中间有缩进。

### 验证方法

```bash
# ❌ 错误：假设单行格式
head -1 file.jsonl | jq

# ✅ 正确：grep 统计角色
grep '"role":' file.jsonl | sort | uniq -c

# ✅ 正确：Python 逐条解析
python3 -c "
import json
with open('file.jsonl') as f:
    content = f.read()
    messages = []
    current = ''
    for line in content.split('\n'):
        if line.strip() == '{':
            current = line
        elif line.strip() == '}':
            current += '\n' + line
            messages.append(json.loads(current))
            current = ''
        else:
            current += '\n' + line if current else ''
    print(f'Total messages: {len(messages)}')
    from collections import Counter
    roles = Counter(m['role'] for m in messages)
    print(f'Roles: {dict(roles)}')
"
```

---

## SQLite 计数器已知问题

测试中发现 `message_count`、`tool_call_count`、`api_call_count` 均为 0，但实际消息已正确存储到 JSONL。

```sql
-- 查询显示：
SELECT id, model, title, message_count, tool_call_count FROM sessions;
-- 结果: 41d8d3ed-...|qwen3.6-plus|新会话|0|0
```

**原因**：增量更新逻辑可能未在会话结束时触发。

**替代验证方法**：直接统计 JSONL 中的消息数。

---

## AI 行为模式

### clarify 工具触发条件

- **用户说"问我一个问题"** → AI 倾向于用文本生成选择题，**不调用 clarify 工具**
- clarify 主要用于：任务存在歧义、需要用户明确选择方向时
- 这不是 bug，是 AI 的行为偏好

### memory 工具触发条件

- **用户说"请记住X"** → AI 倾向于用文本对话回复"好的我记住了"，**不调用 memory 工具**
- 实际验证：37 轮对话中 memory 工具调用次数 = **0**（从 JSONL 验证）
- **解决方案**：需要更明确的指令才能触发，如"调用 memory 工具，action=add, target=user, content=..."
- 测试 memory 功能时，使用明确工具调用指令而非自然语言

### 过度搜索

- 搜索工具时，AI 可能调用 `search_tools` 2-3 次（不同搜索策略）
- 这是已知限制，skill 中已记录

### 上下文保持

- AI 能正确引用之前对话中创建的文件和内容
- "刚才创建的文件" → 正确识别 `/tmp/nanotest.txt`

---

## 性能数据

| 操作 | 耗时 |
|------|------|
| 启动 | ~5s |
| echo hello | 3s |
| false 命令 | 2.3s |
| 创建文件 | 1.9s |
| 读取文件 | 1.9s |
| patch 替换 | 19.5s（包含思考） |
| 搜索 class | 8.9s |
| 质数和计算 | 6.7s |
| 记忆保存 | 2.6s |
| 选择题 | 6.1s |
| TODO 创建 | 2.4s |

**总计**：~14 分钟完成完整 37 用例测试（阶段 1-5）

---

## 实际测试中遇到的错误及修复

### 1. 配置缺失
- **症状**：启动报错或行为异常
- **修复**：创建 `nanohermes.json`
- **耗时**：< 1min

### 2. 依赖验证超时
- **症状**：`python -c "import ..."` 超时
- **原因**：conda 环境激活 + 模块加载需要时间
- **修复**：timeout 从 15s 增加到 60s
- **耗时**：< 1min

### 3. PTY CPR 警告
- **症状**：`WARNING: your terminal doesn't support cursor position requests (CPR).`
- **处理**：非阻塞警告，预期行为，忽略即可

### 4. TUI 输出 ANSI 转义码污染
- **症状**：pexpect 捕获的 `/tools` 等 TUI 命令输出包含大量 `\x1b[35m`、`\x1b[?7l`、`\x1b[7A` 等 ANSI 转义序列，导致正则匹配关键词失败
- **根因**：NanoHermes TUI 使用 rich/prompt_toolkit 渲染彩色 UI，PTY 模式下会输出完整 ANSI 控制码
- **修复**：在 pexpect `self.child.before` 后先用正则清理 ANSI 码再匹配：
  ```python
  ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\([AB0-2]|\x1b\)[0-9]|\r')
  output = ansi_escape.sub('', output)
  ```
- **影响用例**：TS-01（/tools 匹配 defer/延迟 关键词）

### 5. pexpect 驱动 PTY 测试
- **工具选择**：pexpect 是 Python PTY 测试的最佳选择，比 subprocess.Popen + pipe 更可靠
- **安装**：`pip install pexpect`（清华源可用）
- **关键配置**：`pexpect.spawn(cmd, encoding='utf-8', timeout=60, maxread=80000)`
- **日志记录**：`logfile=open('main.log', 'w')` 捕获完整输出
- **prompt 匹配**：需要匹配多种就绪信号 `r'➤|❯|Input\s*:|user\s*>|Type\s+/quit|CPR\b|history\r'`
- **ANSI 清理**：必须在匹配前清理，否则正则无法工作

---

## 测试 Runner 架构

### pty_runner.py 关键设计

1. **pexpect 驱动真实 PTY**（非 subprocess pipe）
2. **ANSI 转义码自动清理**（正则 strip）
3. **结构化测试用例**：test_id + input_text + expected_patterns
4. **自动报告生成**：Markdown 格式，保存到 testing-artifacts/reports/
5. **失败用例单独日志**：每个失败的测试保存完整输出到 logs/<test_id>.log

### 测试执行注意事项

- **长时间运行**：完整 37 用例约需 14 分钟，必须用 background=True + notify_on_complete=True
- **实时进度**：通过 `tail testing-artifacts/logs/main.log` 查看进度
- **清理环境**：每次测试前 `rm -rf ~/.nanohermes/sessions/* ~/.nanohermes/sessions.db* ~/.nanohermes/memory/*`
- **清缓存**：`rm -rf src/__pycache__ src/*/__pycache__`
