# NanoHermes 问题排查指南

> **加载时机**: 当测试遇到问题或需要排查故障时加载此文件

---

## 已知问题

| 问题 | 现象 | 影响 | 状态 |
|------|------|------|------|
| MEMORY.md 重复条目 | 相同信息多次写入 | 低（功能正常，文件冗余） | 待修复 |
| search_files 过度搜索 | AI 连续调用多次搜索 | 低（效率可优化） | 待优化 |

## 测试注意事项

1. **API 成本**: 真实 API 测试会产生费用，控制测试轮次
2. **速率限制**: 注意 API 调用频率，避免触发限流
3. **数据清理**: 测试前备份重要数据，测试后清理测试会话
4. **环境隔离**: 使用独立的测试目录，避免污染生产环境
5. **超时处理**: 长时间无响应时检查网络连接和 API Key

## 测试失败排查

| 现象 | 可能原因 | 解决方法 |
|------|---------|---------|
| 启动失败 | 依赖缺失 | `pip install -r requirements.txt` |
| API 调用失败 | Key 无效/网络问题 | 检查 .env 配置 |
| 工具调用超时 | 命令执行慢 | 增加 timeout 参数 |
| 记忆未保存 | 权限问题 | 检查 ~/.nanohermes/ 权限 |
| 会话未存储 | 数据库锁 | 关闭其他进程，删除 .db-wal |

## 调试方法

### 1. 启用调试模式
```bash
python -m src.main --debug 2>&1 | tee test.log
```
输出完整的请求/响应 JSON 和模型思考内容。

### 2. 搜索关键日志
```bash
# 搜索错误
grep -i "error" test.log

# 搜索工具调用
grep -i "tool_call" test.log

# 搜索记忆操作
grep -i "memory" test.log

# 搜索配置加载
grep -i "config\|credential" test.log
```

### 3. 检查文件系统
```bash
# 检查会话存储
ls -la ~/.nanohermes/sessions/
wc -l ~/.nanohermes/sessions/*.jsonl

# 检查记忆文件
cat ~/.nanohermes/memory/MEMORY.md
cat ~/.nanohermes/memory/USER.md

# 检查数据库
sqlite3 ~/.nanohermes/sessions.db "SELECT COUNT(*) FROM sessions;"
sqlite3 ~/.nanohermes/sessions.db ".tables"
```

### 4. 验证配置
```bash
# 检查 .env 文件
cat .env

# 检查 JSON 配置
cat nanohermes.json 2>/dev/null || echo "No project config"
cat ~/.nanohermes/config.json 2>/dev/null || echo "No global config"

# 测试配置加载
python -c "from src.config.loader import load_config; print(load_config())"
```

### 5. 网络诊断
```bash
# 测试 API 连通性
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  "$DASHSCOPE_BASE_URL/chat/completions"

# 检查 DNS 解析
nslookup dashscope.aliyuncs.com

# 测试网络延迟
ping -c 3 dashscope.aliyuncs.com
```

## 性能指标基准

| 指标 | 预期值 | 测量方法 | 告警阈值 |
|------|--------|---------|---------|
| 启动时间 | < 5 秒 | `time python -m src.main` | > 10 秒 |
| 简单响应 | 2-5 秒 | 观察状态栏 | > 15 秒 |
| 工具调用 | 3-8 秒/次 | 记录时间戳 | > 30 秒 |
| 内存使用 | < 500MB | `ps aux \| grep nanohermes` | > 1GB |
| 会话存储 | < 10MB/百轮 | `du -sh ~/.nanohermes/sessions/` | > 50MB |
| 搜索性能 | < 2 秒/千文件 | 记录搜索时间 | > 10 秒 |

## 常见问题 FAQ

### Q: 测试时 AI 不响应怎么办？
A: 检查以下几点：
1. API Key 是否有效（`echo $DASHSCOPE_API_KEY`）
2. 网络是否通畅（`curl` 测试 API 端点）
3. 模型名称是否正确（`MODEL_NAME` 环境变量）
4. 查看 `--debug` 模式的完整日志

### Q: 工具调用返回错误怎么办？
A: 查看错误类型：
- **工具未找到**: 检查工具注册表，确认 `discover_tools()` 扫描到该模块
- **参数错误**: 检查 LLM 返回的 JSON 参数格式
- **执行超时**: 增加 `timeout` 参数（默认 300 秒）
- **权限错误**: 检查文件/目录权限

### Q: 会话无法恢复怎么办？
A: 检查：
1. `~/.nanohermes/sessions/` 目录是否存在 JSONL 文件
2. `~/.nanohermes/sessions.db` 数据库是否损坏
3. 尝试 `--list-sessions` 查看可用会话
4. 如有 `.db-wal` 文件，先关闭所有进程再删除

### Q: 记忆文件不更新怎么办？
A: 检查：
1. AI 是否调用了 `memory` 工具
2. `~/.nanohermes/memory/` 目录权限是否正确
3. 记忆文件格式是否正确（YAML frontmatter + markdown body）

### Q: 如何清理测试数据？
A: 运行以下命令：
```bash
rm -rf ~/.nanohermes/sessions/*
rm -f ~/.nanohermes/sessions.db
rm -rf ~/.nanohermes/memory/*
```
⚠️ **注意**: 这将删除所有历史会话和记忆，请先备份重要数据！
