## 1. 项目设置

- [ ] 1.1 创建 `src/delegation/` 目录结构
- [ ] 1.2 定义委托相关类型和接口
- [ ] 1.3 配置 vitest 测试框架

## 2. 委托 API 实现

- [ ] 2.1 实现 delegateTask 函数
- [ ] 2.2 实现 delegateSingle 函数（单任务模式）
- [ ] 2.3 实现 delegateBatch 函数（批量并行模式）
- [ ] 2.4 实现 Semaphore 类用于并发控制
- [ ] 2.5 编写委托 API 的单元测试
  - [ ] 2.5.1 测试单任务委托
  - [ ] 2.5.2 测试批量并行委托
  - [ ] 2.5.3 测试缺少 goal 和 tasks

## 3. 角色系统实现

- [ ] 3.1 实现 DELEGATE_BLOCKED_TOOLS 常量
- [ ] 3.2 实现 buildChildAgentConfig 函数
- [ ] 3.3 实现 filterBlockedTools 函数
- [ ] 3.4 实现 buildLeafSystemPrompt 函数
- [ ] 3.5 实现 buildOrchestratorSystemPrompt 函数
- [ ] 3.6 编写角色系统的单元测试
  - [ ] 3.6.1 测试 leaf 角色阻止 delegate_task
  - [ ] 3.6.2 测试 leaf 角色阻止 clarify
  - [ ] 3.6.3 测试 orchestrator 角色允许 delegate_task

## 4. 并发和深度控制实现

- [ ] 4.1 实现 max_concurrent_children 配置
- [ ] 4.2 实现 max_spawn_depth 配置
- [ ] 4.3 实现 child_timeout_seconds 处理
- [ ] 4.4 实现 subagent_auto_approve 配置
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
