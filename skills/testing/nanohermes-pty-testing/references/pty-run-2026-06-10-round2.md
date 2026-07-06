# PTY 自动化 Runner 执行记录（第二轮 — 2026-06-10）

## 执行概况
- **Runner**: `scripts/pty_runner.py`（pexpect 驱动）
- **总用例**: 37
- **通过**: 35 | **失败**: 2 | **通过率**: 94.6%
- **耗时**: ~792 秒（13 分钟）

## 失败用例分析

### TS-01 — `/tools` deferred 工具列表匹配失败
**原因**：`/tools` 输出包含大量 ANSI 转义码（`\x1b[35m` 等），即使 strip 后仍有 `\r`、`\b` 等残留字符打断关键词匹配。正则 `defer|延迟` 无法在清理后的文本中匹配。
**修复方向**：
1. 使用更宽松的匹配模式（如 `deferred|defer` 不区分大小写 + 更完整的 ANSI strip）
2. 或直接检查 NanoHermes 进程输出中是否包含工具列表的结构性特征
**状态**：未修复，仍需处理

### T-44 — 二进制文件读取拒绝测试匹配失败
**原因**：NanoHermes 拒绝读取 `.png` 文件时，AI 回复措辞不包含测试预期的 "binary|二进制|不支持|无法读取|拒绝|deny|cannot|error" 关键词。AI 可能用了"这个文件是图片格式"等不同表述。
**修复方向**：
1. 扩展匹配模式，加入更多可能的拒绝措辞
2. 或改为检查工具调用结果（`read_file` 返回错误状态）而非 AI 的文本回复
**状态**：未修复，仍需处理

## 成功改进

### M-01 — 记忆持久化测试通过
**关键改进**：测试输入从自然语言（"请记住：我的名字是测试员小王"）改为明确参数格式（"调用 memory 工具，参数：action=add, target=user, content='名字是测试员小王'"），成功触发 memory 工具调用。阶段 5 验证 USER.md 包含内容。

### 进度汇报规范
**用户反馈**："也不告诉我"、"时刻提醒我进度呀"
**改进**：SKILL.md 新增"进度汇报规范（强制执行）"章节，要求每 30 秒汇报一次。

## 新发现的问题

### 提示符匹配过宽导致重复发送
清理 ANSI 后，正则 `➤|❯|Type\s+/quit|CPR|history` 匹配过于宽泛，导致同一命令被重复发送 2-3 次。例如 `/tools` 连续出现 3 次。需要在 runner 中增加去重逻辑或使用更精确的 prompt 匹配。

### search_tools 发现机制
当测试涉及延迟加载工具（memory、todo）时，AI 会先调用 `search_tools select:<toolname>` 发现工具，然后再调用实际工具。这是预期行为，但增加了测试用例的响应时间。

## 日志文件
- 主日志：`testing-artifacts/logs/main.log`（2046 行）
- 失败用例：`testing-artifacts/logs/T-44.log`
- 报告：`testing-artifacts/reports/report-2026-06-10-1213.md`
