## 上下文

业界成熟的自进化 AI Agent 系统的委托工具模块 (~2800 LOC) 实现了完整的多 Agent 委托系统。核心设计决策包括：
- 子 Agent 拥有新鲜对话上下文，无父历史
- 父上下文只看到委托调用和摘要结果
- leaf 角色阻止递归委托和用户交互
- 并发限制（默认 3）和深度限制（默认 2）
- 危险命令审批可配置

## 目标 / 非目标

**目标：**
- 实现委托 API（单任务和批量并行）
- 实现角色系统和工具集限制
- 实现并发和深度控制
- 实现危险命令审批

**非目标：**
- 不实现独立进程 spawn（使用 OpenCode subagent）
- 不实现终端会话隔离（由 OpenCode 处理）

## 技术方案

### 1. 委托 API

```typescript
interface DelegateOptions {
  goal?: string;           // 单任务目标
  tasks?: Task[];          // 批量任务数组
  context?: string;        // 额外上下文
  toolsets?: string[];     // 请求的工具集
  role?: 'leaf' | 'orchestrator';
  model?: string;
  provider?: string;
}

interface Task {
  goal: string;
  context?: string;
  toolsets?: string[];
}

async function delegateTask(options: DelegateOptions): Promise<DelegateResult> {
  if (options.tasks) {
    // 批量并行模式
    return delegateBatch(options.tasks, options);
  } else if (options.goal) {
    // 单任务模式
    return delegateSingle(options);
  } else {
    throw new Error('必须提供 goal 或 tasks');
  }
}
```

### 2. 角色系统

```typescript
const DELEGATE_BLOCKED_TOOLS = new Set([
  'delegate_task',   // 阻止递归委托
  'clarify',         // 阻止用户交互
  'memory',          // 阻止写入共享 MEMORY.md
  'send_message',    // 阻止跨平台副作用
  'execute_code'     // 子 Agent 应逐步推理，而非写脚本
]);

function buildChildAgentConfig(options: DelegateOptions): ChildAgentConfig {
  const allowedToolsets = options.toolsets || DEFAULT_SUBAGENT_TOOLSETS;
  
  if (options.role === 'leaf') {
    // leaf 角色：移除被阻止的工具
    return {
      ...options,
      toolsets: filterBlockedTools(allowedToolsets, DELEGATE_BLOCKED_TOOLS),
      systemPrompt: buildLeafSystemPrompt(options)
    };
  } else {
    // orchestrator 角色：保留 delegate_task
    return {
      ...options,
      toolsets: allowedToolsets,
      systemPrompt: buildOrchestratorSystemPrompt(options)
    };
  }
}
```

### 3. 并发控制

```typescript
async function delegateBatch(tasks: Task[], options: DelegateOptions): Promise<DelegateResult> {
  const maxConcurrent = options.maxConcurrentChildren || 3;
  const results: DelegateResult[] = [];
  
  // 使用信号量控制并发
  const semaphore = new Semaphore(maxConcurrent);
  
  const promises = tasks.map(async (task) => {
    await semaphore.acquire();
    try {
      const result = await delegateSingle({ ...options, goal: task.goal });
      results.push(result);
      return result;
    } finally {
      semaphore.release();
    }
  });
  
  await Promise.all(promises);
  return { results, summary: buildBatchSummary(results) };
}
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| 子 Agent 可能执行危险命令 | 默认自动拒绝，可配置为自动批准 |
| 并发子 Agent 过多消耗资源 | 限制 max_concurrent_children |
| 递归委托导致深度爆炸 | 限制 max_spawn_depth |
