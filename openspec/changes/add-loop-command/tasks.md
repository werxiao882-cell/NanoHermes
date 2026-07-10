## 1. 项目结构与基础

- [ ] 1.1 创建 `src/loop/` 目录及 `__init__.py`
- [ ] 1.2 创建 `src/loop/ARCHITECTURE.md` 模块架构文档
- [ ] 1.3 定义循环相关数据类型（`LoopConfig`, `LoopState`, `LoopStatus` 枚举）

## 2. 间隔解析器

- [ ] 2.1 实现 `src/loop/interval_parser.py` 中的 `parse_interval()` 函数
- [ ] 2.2 支持持续时间格式：`30s`, `5m`, `2h`, `1d`
- [ ] 2.3 支持自然语言格式：`every 5 minutes`, `every 2 hours`
- [ ] 2.4 支持 Cron 表达式格式：`*/5 * * * *`
- [ ] 2.5 实现间隔验证（最小 60s，最大 86400s）
- [ ] 2.6 编写间隔解析器单元测试

## 3. 内置维护提示

- [ ] 3.1 实现 `src/loop/prompt.py` 中的 `get_maintenance_prompt()` 函数
- [ ] 3.2 实现 `loop.md` 文件加载逻辑（项目级 `.claude/loop.md` → 用户级 `~/.nanohermes/loop.md`）
- [ ] 3.3 实现内置维护提示文本（继续工作 → 检查 PR → 清理优化）
- [ ] 3.4 实现 25,000 字节截断限制
- [ ] 3.5 编写提示加载单元测试

## 4. 循环管理器

- [ ] 4.1 实现 `src/loop/manager.py` 中的 `LoopManager` 类
- [ ] 4.2 实现 `create_loop()` 方法：创建循环，生成 ID，存储元数据
- [ ] 4.3 实现 `stop_loop()` 方法：停止当前循环
- [ ] 4.4 实现 `get_active_loop()` 方法：获取当前活跃循环
- [ ] 4.5 实现 `is_loop_expired()` 方法：检查 7 天过期
- [ ] 4.6 实现 `restore_loop()` 方法：从会话元数据恢复循环
- [ ] 4.7 实现动态间隔解析（从 AI 响应中提取 `__next_interval: Xm__`）
- [ ] 4.8 实现循环执行调度器（基于 `asyncio.sleep` 或后台线程）
- [ ] 4.9 编写循环管理器单元测试

## 5. TUI 命令集成

- [ ] 5.1 在 `src/cli/tui.py` 的 `_handle_command()` 中添加 `/loop` 处理
- [ ] 5.2 在 `src/cli/tui.py` 的 `_handle_command()` 中添加 `/stop-loop` 处理
- [ ] 5.3 实现 `_cmd_loop()` 方法：解析参数，创建循环，显示确认信息
- [ ] 5.4 实现 `_cmd_stop_loop()` 方法：停止循环，显示确认信息
- [ ] 5.5 在 `SLASH_COMMANDS` 列表中添加 `/loop` 和 `/stop-loop`
- [ ] 5.6 在 `src/cli/completers.py` 的 `COMMANDS` 中添加命令描述
- [ ] 5.7 实现循环状态指示器（在状态栏显示当前循环信息）
- [ ] 5.8 实现循环执行时的进度显示

## 6. 循环执行集成

- [ ] 6.1 实现循环触发逻辑：间隔到期后调用 `_run_conversation_loop(prompt)`
- [ ] 6.2 实现循环执行结果展示（与正常对话相同的输出格式）
- [ ] 6.3 实现循环错误处理：单次失败不停止循环
- [ ] 6.4 实现循环上下文注入：循环提示作为用户消息追加
- [ ] 6.5 实现循环元数据持久化：存储到会话 JSONL
- [ ] 6.6 实现 `Esc` 键停止等待中的循环

## 7. 会话恢复集成

- [ ] 7.1 在 `--resume` 时检查并恢复未过期循环
- [ ] 7.2 在 `--resume <id>` 时检查并恢复未过期循环
- [ ] 7.3 在 `--resume-title` 时检查并恢复未过期循环
- [ ] 7.4 恢复时显示循环状态信息

## 8. 测试

- [ ] 8.1 编写间隔解析器测试（各种格式、边界情况、无效输入）
- [ ] 8.2 编写 `loop.md` 加载测试（项目级优先、用户级回退、不存在回退内置）
- [ ] 8.3 编写循环管理器测试（创建、停止、过期、恢复）
- [ ] 8.4 编写 `/loop` 命令测试（4 种模式）
- [ ] 8.5 编写 `/stop-loop` 命令测试
- [ ] 8.6 编写循环执行集成测试
- [ ] 8.7 编写会话恢复循环测试
- [ ] 8.8 运行 `pytest tests/loop/ -v` 确保全部通过

## 9. 文档

- [ ] 9.1 更新 `AGENTS.md` 添加 `/loop` 命令说明
- [ ] 9.2 在 `/help` 输出中添加 `/loop` 和 `/stop-loop` 说明
- [ ] 9.3 编写 `loop.md` 示例文件（`.claude/loop.md.example`）
