# NanoHermes 测试用例参考

扩展测试用例的方法论和完整用例列表，基于项目 15 个核心模块。

## 从项目文档扩展测试用例的方法

当需要为 AI Agent 项目添加更多测试用例时：

### 1. 从 README.md 提取模块列表

```bash
# 查找项目结构表
grep -A 20 "## 核心模块" README.md
# 或查找架构表
grep -A 20 "| 模块 | 职责 |" README.md
```

每个模块对应一组测试用例：核心功能 + 边界情况 + 与其他模块的集成。

### 2. 从 AGENTS.md 提取编码规范和约束

AGENTS.md 包含模块职责划分表、禁止行为、推荐模式。每个约束都可以转化为测试：

| AGENTS.md 约束 | 对应测试 |
|----------------|---------|
| "每个模块必须包含 ARCHITECTURE.md" | 验证所有 src/*/ARCHITECTURE.md 存在 |
| "单个文件不超过 300 行" | 扫描所有 .py 文件大小 |
| "函数不超过 50 行" | AST 分析函数行数 |
| "代码注释使用中文" | 检查注释语言 |
| "入口文件直接操作 SDK → 错误" | 检查 main.py 是否直接 import SDK |

### 3. 从 OpenSpec 变更提取测试场景

```bash
# 列出所有变更及其任务
for d in openspec/changes/*/; do
  name=$(basename "$d"); tasks="$d/tasks.md"
  if [ -f "$tasks" ]; then
    total=$(grep -c '^\s*[-*]' "$tasks" 2>/dev/null || echo 0)
    done=$(grep -c '^\s*[-*] \[x\]' "$tasks" 2>/dev/null || echo 0)
    echo "$name: $done/$total"
  fi
done
```

每个未完成的 task 都是潜在的测试场景。

### 4. 测试用例分类框架

按以下维度组织测试用例：

| 维度 | 说明 | 示例 |
|------|------|------|
| 功能测试 | 模块核心功能 | session CRUD、工具执行 |
| 集成测试 | 模块间交互 | 工具→会话存储、记忆→提示组装 |
| 边界测试 | 极端输入/状态 | 空输入、超长文本、特殊字符 |
| 错误处理 | 异常场景恢复 | API 超时、文件不存在、权限错误 |
| 性能测试 | 响应时间/资源使用 | 启动时间、内存、搜索速度 |
| 安全测试 | 注入/越权/泄露 | 命令注入、路径遍历、Key 脱敏 |

### 5. NanoHermes 15 模块完整用例表

| 模块 | 用例数 | 核心测试 |
|------|--------|---------|
| session-storage | 7 | 会话 CRUD、FTS5、WAL 并发 |
| tool-runtime | 12 | 6 种工具、错误处理、输出截断 |
| memory-system | 5 | 注入/更新/持久化/去重 |
| provider-runtime | 6 | API 调用、流式、回退链 |
| unified-config-system | 7 | 优先级链、Pydantic、多提供商 |
| system-prompt-assembly | 8 | 三层架构、威胁/Unicode 检测 |
| tool-search | 6 | BM25/Regex/Auto、延迟加载 |
| conversation-loop | 10 | 上下文保持、事件总线、压缩 |
| multi-agent-delegation | 5 | leaf/orchestrator、并发 |
| skill-system | 6 | 技能 CRUD、类别组织 |
| context-compression | 5 | 摘要、头尾保护、预算 |
| insights-metrics | 4 | Token 统计、成本、趋势 |
| add-mcp-server-support | 6 | Stdio/HTTP/SSE 传输 |
| cli (TUI) | 8 | 渲染、流式、命令/键盘 |
| auxiliary | 4 | 后台任务、刷写、隔离 |

### 6. 高级场景用例

| 场景 | 步骤 | 验证点 |
|------|------|--------|
| 工具组合 | 创建→读取→编辑→验证 | 链式操作数据一致性 |
| 多会话切换 | A→B→A | 上下文正确恢复 |
| 跨会话记忆 | A 保存→B 读取 | 记忆共享 |
| API 超时 | 模拟慢响应 | 友好错误提示 |
| 100+ 轮对话 | 长时间交互 | 性能正常无卡顿 |

## 使用时机

当用户要求：
- "增加更多测试用例"
- "基于项目文档扩展测试"
- "覆盖更多测试场景"
- 或类似需求

先分析项目架构文档（README.md、AGENTS.md、OpenSpec），提取模块列表和约束，然后按上述分类框架生成用例。
