## 循环管理器

`LoopManager` 负责循环的生命周期：创建、执行、停止、恢复。

### 需求

- **MUST** `create_loop(interval, prompt)` 创建新循环，返回循环 ID
- **MUST** `stop_loop()` 停止当前活跃循环
- **MUST** `get_active_loop()` 返回当前活跃循环的配置，无则返回 None
- **MUST** 循环创建时生成唯一 8 字符 ID
- **MUST** 循环元数据包含：loop_id、interval、prompt、created_at、expires_at、status
- **MUST** 循环在创建 7 天后自动过期（expires_at = created_at + 7 days）
- **MUST** `is_loop_expired()` 检查当前时间是否超过 expires_at
- **MUST** 循环执行时复用 TUI 的 `_run_conversation_loop(prompt)` 方法
- **MUST** 动态间隔模式下，从 AI 响应中提取 `__next_interval: Xm__` 标记
- **MUST** 单次循环执行失败不停止整个循环，记录错误继续
- **MUST** 循环元数据存储到会话 JSONL 文件中
- **MUST** `restore_loop(loop_meta)` 从元数据恢复循环状态
- **SHOULD** 循环执行时显示进度指示器
- **SHOULD** 循环执行结果以与正常对话相同的格式展示

### 循环状态机

```
created → active → (executing) → waiting → (executing) → ... → stopped
         ↓
       expired (7 天后自动)
```

### 动态间隔提取

AI 响应中的间隔标记格式：
```
__next_interval: 5m__
```

支持的单位：`s`, `m`, `h`, `d`
如果 AI 未输出标记，默认使用 10 分钟间隔。

### 循环执行流程

```
1. 检查循环状态（是否已停止/过期）
2. 构建用户消息（循环提示）
3. 调用 _run_conversation_loop(prompt)
4. 显示执行结果
5. 如果是动态间隔模式，解析 AI 响应获取下一次间隔
6. 等待间隔时间
7. 回到步骤 1
```
