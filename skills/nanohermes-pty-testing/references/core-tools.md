# 工具运行时 + 工具搜索 + Dispatcher — 79 用例

## tool-runtime (54 用例)

### terminal 工具 (5)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-02 | 基础命令 | `运行 echo hello` | 输出 "hello" | [PTY] |
| T-03 | 复杂计算 | `计算 2 的 10 次方` | 输出 1024 | [PTY] |
| T-13 | 超时控制 | 执行 `sleep 100` | 超时截断 | [UNIT] |
| T-14 | exit code 非 0 | `运行 false` | exit code 1 返回 | [PTY] |
| T-15 | 工作目录 | `workdir 参数指定目录` | 在指定目录执行 | [UNIT] |

### read_file (4)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-04 | 读取文件 | `读取 /tmp/nanotest.txt` | 显示内容 | [PTY] |
| T-16 | offset/limit 分页 | `读取第 1 行` | offset=1, limit=1 | [PTY] |
| T-46 | 分页 has_more | 大文件 offset=1,limit=10 | has_more=True, next_offset | [PTY] |
| T-47 | 行号格式 | read_file 返回 | 6 位行号 + 内容 | [PTY] |
| T-44 | 二进制文件拒绝 | read_file .png | 返回二进制文件错误 | [PTY] |
| T-45 | 权限不足读取 | read_file 无权限文件 | 权限不足错误 | [UNIT] |

### write_file (2)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-05 | 创建文件 | `写入 /tmp/nanotest.txt` | 16 bytes written | [PTY] |
| T-17 | 自动创建目录 | `写入 /tmp/a/b/c/test.txt` | 父目录自动创建 | [PTY] |
| T-48 | 敏感路径写入 | write_file .env | 拒绝写入敏感路径 | [PTY] |
| T-49 | 权限不足写入 | write_file 无权限目录 | 权限不足错误 | [UNIT] |

### patch 编辑 (3)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-06 | 替换内容 | `把 Hello 替换为 Hi` | 替换成功 | [PTY] |
| T-18 | 模糊匹配 | 轻微缩进差异的替换 | 仍匹配成功 | [PTY] |
| T-19 | replace_all | 全局替换所有匹配项 | 多处替换成功 | [UNIT] |

### search_files 文件名 (3)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-07 | 文件名搜索 | `搜索 *.py 文件` | 返回匹配文件列表 | [PTY] |
| T-20 | files_only 模式 | `搜索只返回文件路径` | output_mode=files_only | [PTY] |
| T-54 | output_mode 切换 | files_only vs content | 不同输出模式 | [PTY] |

### search_files 内容 (7)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-08 | 内容搜索 | `搜索含 class 的 Python 文件` | 返回匹配结果 | [PTY] |
| T-21 | count 模式 | `统计含 class 的文件数` | output_mode=count | [PTY] |
| T-22 | context 行数 | `搜索 async def 前后 3 行` | 含上下文行 | [PTY] |
| T-23 | offset 分页 | 跳过前 N 个结果 | 分页正确 | [UNIT] |
| T-11 | 大型输出截断 | 读取 /tmp/big_file_t11.txt（2000行） | 输出被截断，提示默认读取500行 | [PTY] |
| T-50 | 递归搜索 | recursive=True | 递归搜索子目录 | [PTY] |
| T-51 | 非递归搜索 | recursive=False | 只搜索当前目录 | [PTY] |
| T-52 | 目录不存在 | path 指向文件 | 目录不存在错误 | [PTY] |
| T-53 | max_results | 限制结果数量 | 最多返回 max_results | [PTY] |

### execute_code (4)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-10 | 代码执行 | `计算 100 以内质数和` | 1060 | [PTY] |
| T-24 | hermes_tools 导入 | `from hermes_tools import terminal` | 导入成功 | [UNIT] |
| T-25 | 超时限制 | 无限循环 | 5min 超时截断 | [UNIT] |
| T-26 | stdout 限制 | 输出超过 50KB | 被截断 | [UNIT] |

### memory_tool (4)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-10 | 记忆保存 | `记住名字是测试员小王` | success, add to user | [PTY] |
| T-27 | memory replace | 替换已有记忆条目 | 旧条目被新条目替换 | [PTY] |
| T-28 | memory remove | 删除指定记忆条目 | 条目被删除 | [PTY] |
| T-29 | 无效操作提示 | action 不合法 | 友好提示 | [UNIT] |

### process_tool (3)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-30 | process list | 列出所有后台进程 | 进程列表 | [UNIT] |
| T-31 | process kill | 终止后台进程 | 进程被终止 | [UNIT] |
| T-32 | wait timeout | 等待超时 | 返回部分输出 | [UNIT] |

### todo_tool (3)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-33 | todo merge | 更新+添加任务 | merge 模式正确 | [PTY] |
| T-34 | 状态转换 | pending→in_progress→completed | 状态流转正确 | [PTY] |
| T-35 | 取消任务 | 状态转为 cancelled | 取消成功 | [UNIT] |

### clarify_tool (3)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-12 | 选择题 | `问我一个问题` | ⚠️ **注意**：AI 倾向于用文本对话生成选择题，不必然调用 clarify 工具。clarify 主要用于任务歧义时。见 `references/test-findings.md` | [PTY] |
| T-36 | 开放式问题 | 无 choices 参数 | 自由输入 | [PTY] |
| T-37 | Other 选项 | 选择 Other 后自定义 | 自定义输入 | [UNIT] |

### 工具基础设施 (6)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| T-01 | 工具列表 | `/tools` 命令 | 显示所有工具 | [PTY] |
| T-38 | 并发限制 | 同工具类型最多 N 并发 | 并发控制正确 | [UNIT] |
| T-39 | 输出截断 | 大输出超过预算 | 自动截断 | [PTY] |
| T-09 | 错误处理 | 读不存在文件 | 友好错误提示 | [PTY] |
| T-18 | 工具链验证 | write→read→patch→read | 链式调用正确 | [PTY] |
| T-43 | 动态加载 | search 后工具加入上下文 | 延迟工具可用 | [PTY] |

## tool-search (6 用例)

| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| TS-01 | 延迟加载标记 | `/tools` 看 deferred | 显示 deferred 标记 | [PTY] |
| TS-02 | BM25 搜索 | `自然语言查询工具` | 返回相关工具 | [PTY] |
| TS-03 | Regex 搜索 | `精确工具名匹配` | 精确匹配 | [PTY] |
| TS-04 | Auto 模式 | 自动选择策略 | BM25 或 Regex | [PTY] |
| TS-05 | 按需发现 | 需要时调用 search_tools | 动态发现工具 | [PTY] |
| TS-06 | 无结果处理 | 搜索不存在的工具 | 友好提示无结果 | [PTY] |

## Dispatcher (19 用例)

### 工具分发 (7)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| D-09 | 工具未找到 | dispatch 不存在工具 | JSON 错误 + 延迟工具提示 | [PTY] |
| D-10 | 延迟工具提示 | dispatch 延迟工具 | select: 语法提示 | [PTY] |
| D-11 | 可用性检查 | check_fn 返回 False | 工具不可用错误 | [UNIT] |
| D-12 | 参数 JSON 解析 | args 为 JSON 字符串 | 解析为 dict | [PTY] |
| D-13 | 参数 dict | args 为 dict | 直接使用 | [PTY] |
| D-14 | 参数 None | args=None | 空 dict | [PTY] |
| D-15 | 参数非法 JSON | args 为非法 JSON | 解析错误 | [UNIT] |

### 执行追踪 (4)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| D-16 | 执行追踪开始 | mark_start | 记录工具开始 | [DEBUG] |
| D-17 | 执行防重入 | 重复 mark_start | 已在执行中错误 | [UNIT] |
| D-18 | 执行追踪完成 | mark_complete | 记录执行时长 | [DEBUG] |
| D-19 | 执行追踪失败 | mark_failed | 记录错误信息 | [DEBUG] |

### 结果预算 (1)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| D-20 | 结果预算 | apply_budget_to_dispatch_result | 大结果截断 | [PTY] |

### 异步桥接 (7)
| ID | 测试内容 | 操作步骤 | 预期 | 标记 |
|----|---------|---------|------|------|
| D-21 | 异步桥接策略 A | 已有事件循环时 | 新线程+新循环执行 | [UNIT] |
| D-22 | 异步桥接策略 B | 无事件循环时 | 持久循环执行 | [UNIT] |
| D-23 | 持久循环懒加载 | 首次调用时创建 | 避免启动开销 | [UNIT] |
| D-24 | 持久循环锁保护 | 并发创建 | 防止多循环 | [UNIT] |
| D-25 | 守护线程清理 | 程序退出时 | 自动清理 | [UNIT] |
| D-26 | 超时保护 300s | future.result(timeout=300) | 超时返回错误 | [UNIT] |
| D-27 | 新线程桥接超时 | thread.join(timeout=300) | 超时返回错误 | [UNIT] |

## 测试优先级

**P0（阶段 3 必测）**：T-02, T-04~05, T-06~08, T-10, T-12, T-14, T-16, T-17, T-20~22, T-27, T-33, T-34, T-36, T-39, T-01, T-09, TS-01~06, D-09~10, D-12~14, D-20

**P1（阶段 4 选测）**：T-03, T-11, T-28, T-44~46, T-50~54, T-47, D-11

**P2（需特殊条件）**：T-13, T-15, T-19, T-23~26, T-29~32, T-35, T-37, T-38, D-15, D-21~27
