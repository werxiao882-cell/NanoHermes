## 1. 项目设置

- [x] 1.1 创建 `src/tools/` 目录结构
- [x] 1.2 创建 `src/tools/environments/` 目录结构
- [x] 1.3 编写 `src/tools/ARCHITECTURE.md` 架构文档

## 2. 工具注册表

- [x] 2.1 定义 ToolEntry 接口（name, toolset, schema, handler, check_fn）
- [x] 2.2 实现 ToolRegistry 类（Map 存储，register 方法）
- [x] 2.3 实现工具名冲突检测和警告
- [x] 2.4 实现 getTool 和 getAllTools 方法
- [x] 2.5 实现 getToolSchemas 方法（按 toolset 过滤）
- [x] 2.6 编写注册表单元测试

## 3. 工具自动发现

- [x] 3.1 实现 discoverTools 函数，扫描目录查找 .py 文件
- [x] 3.2 实现 AST 解析检测顶层 register_tool() 调用
- [x] 3.3 实现动态 import 工具模块（单个失败不阻塞其他）
- [x] 3.4 跳过 __init__.py, registry.py 等非工具文件
- [ ] 3.5 编写自动发现单元测试

## 4. 工具集定义和解析

- [x] 4.1 定义 TOOLSETS 常量（toolset name → tool names 映射）
- [x] 4.2 实现 resolveToolset 函数（展开 toolset 为工具名列表）
- [x] 4.3 实现 enabled_toolsets 过滤（只包含列出的）
- [x] 4.4 实现 disabled_toolsets 过滤（排除列出的）
- [x] 4.5 实现 legacy toolset name 映射（*_tools → 现代名）
- [x] 4.6 实现 toolset check_fn 支持
- [x] 4.7 编写工具集解析单元测试

## 5. 可用性检查

- [x] 5.1 实现 checkToolAvailability 函数，运行 check_fn 并缓存结果
- [x] 5.2 实现相同 check_fn 去重（多次调用只执行一次）
- [x] 5.3 实现 check_fn 异常处理（异常视为不可用）
- [x] 5.4 编写可用性检查单元测试

## 6. 工具分发器

- [x] 6.1 实现 dispatch(name, args, task_id) 函数
- [x] 6.2 实现按名称查找 ToolEntry 并调用 handler
- [x] 6.3 实现 args 到 handler 参数的映射
- [x] 6.4 实现 task_id 传播到 handler
- [x] 6.5 实现错误包装（捕获所有异常，返回 JSON 错误字符串）
- [x] 6.6 编写分发器单元测试

## 7. 终端工具

- [x] 7.1 实现 TerminalEnvironment 接口（execute, cwd, timeout）
- [x] 7.2 实现 LocalEnvironment 类，使用 subprocess.Popen
- [x] 7.3 实现 stdout/stderr 流式收集和输出
- [x] 7.4 实现 cwd 参数支持
- [x] 7.5 实现超时保护（默认 300 秒，超时则 kill 进程）
- [x] 7.6 实现 DANGEROUS_PATTERNS 正则列表
- [x] 7.7 实现危险命令检测和审批请求返回
- [x] 7.8 实现终端工具注册（register_tool 调用）
- [x] 7.9 编写终端工具单元测试

## 8. 异步桥接

- [x] 8.1 实现 detectRunningLoop 函数
- [x] 8.2 实现 PersistentLoop 类（持久事件循环管理）
- [x] 8.3 实现 asyncBridge 函数（无 loop 时用持久 loop，有 loop 时用线程）
- [x] 8.4 实现异步 handler 执行和结果返回
- [x] 8.5 实现异步异常捕获和错误返回
- [ ] 8.6 编写异步桥接单元测试

## 9. 集成测试

- [ ] 9.1 编写完整工具调用链集成测试（register → discover → resolve → dispatch）
- [ ] 9.2 编写终端工具集成测试（执行命令 → 获取输出）
- [ ] 9.3 编写危险命令审批集成测试
- [ ] 9.4 编写工具集过滤集成测试（enabled/disabled）

## 10. 工具文件重构

- [x] 10.1 统一工具文件命名格式：`<category>_tools.py`
- [x] 10.2 拆分 default_tools.py 为独立文件：
  - clarify_tools.py
  - code_execution_tools.py
  - cronjob_tools.py
  - delegation_tools.py
  - memory_tools.py
  - session_search_tools.py
  - skills_tools.py
  - process_tools.py
- [x] 10.3 删除废弃的 default_tools.py 和 clarify_tool.py
- [x] 10.4 更新 main.py 导入路径
- [x] 10.5 更新测试文件导入路径
- [x] 10.6 验证所有测试通过

## 11. Todo 工具实现

- [x] 11.1 实现 TodoStore 类（内存任务列表）
- [x] 11.2 实现 todo_tool 函数（读写任务）
- [x] 11.3 实现任务状态管理（pending/in_progress/completed/cancelled）
- [x] 11.4 实现任务合并和替换逻辑
- [x] 11.5 注册 todo 工具到工具注册表
- [x] 11.6 编写 todo 工具单元测试
