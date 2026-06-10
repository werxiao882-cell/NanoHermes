## 1. 项目设置

- [x] 1.1 创建 `src/delegation/` 目录结构
- [x] 1.2 定义委托相关类型和接口 (AgentRole, DelegationResult, DelegationManager)
- [x] 1.3 配置 pytest 测试框架 (Python 项目)

## 2. 委托 API 实现

- [x] 2.1 实现 delegate_task 函数
- [x] 2.2 实现 _spawn_single 函数（单任务模式）
- [x] 2.3 实现 _spawn_batch 函数（批量并行模式）
- [x] 2.4 实现 Semaphore 并发控制 (通过 max_concurrent 切片实现)
- [x] 2.5 编写委托 API 的单元测试 (17 tests, all passing)
  - [x] 2.5.1 测试单任务委托
  - [x] 2.5.2 测试批量并行委托
  - [x] 2.5.3 测试缺少 goal 和 tasks

## 3. 角色系统实现

- [x] 3.1 实现 DELEGATE_BLOCKED_TOOLS 常量
- [x] 3.2 实现 build_child_agent_config 函数
- [x] 3.3 实现 filter_blocked_tools 函数
- [x] 3.4 实现 build_leaf_system_prompt 函数
- [x] 3.5 实现 build_orchestrator_system_prompt 函数
- [ ] 3.6 编写角色系统的单元测试
  - [ ] 3.6.1 测试 leaf 角色阻止 delegate_task
  - [ ] 3.6.2 测试 leaf 角色阻止 clarify
  - [ ] 3.6.3 测试 orchestrator 角色允许 delegate_task

## 4. 并发和深度控制实现

- [x] 4.1 实现 max_concurrent_children 配置
- [x] 4.2 实现 max_spawn_depth 配置
- [x] 4.3 实现 child_timeout_seconds 处理
- [x] 4.4 实现 subagent_auto_approve 配置
- [ ] 4.5 实现 _subagentAutoDeny 和 _subagentAutoApprove 回调
- [ ] 4.6 编写并发控制的单元测试
  - [ ] 4.6.1 测试并发限制为 3
  - [ ] 4.6.2 测试深度限制阻止 leaf 委托
  - [ ] 4.6.3 测试 orchestrator 深度限制
  - [ ] 4.6.4 测试子 Agent 超时
  - [ ] 4.6.5 测试自动拒绝
  - [ ] 4.6.6 测试自动批准

## 5. 子 Agent 隔离测试

- [ ] 5.1 编写子 Agent 上下文隔离的单元测试
  - [ ] 5.1.1 测试子 Agent 无父历史
  - [ ] 5.1.2 测试父上下文只看到摘要
