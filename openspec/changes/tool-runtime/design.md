## Context

NanoHermes 从零构建，参考 Hermes Agent 的 tools runtime 架构（Python 实现，自注册工具模型）。NanoHermes 使用 TypeScript + Node.js。

当前项目无现有工具层。工具注册、分发、终端执行都需要从零实现。

## Goals / Non-Goals

**Goals:**
- 自注册工具模型：import 工具模块时自动注册到全局注册表
- 工具集分组：按功能命名工具集，支持启用/禁用过滤
- 统一分发：对话循环通过工具名调用，不关心实现细节
- 终端工具：支持本地命令执行、危险命令审批
- 异步桥接：在同步上下文中执行异步工具

**Non-Goals:**
- 不实现 MCP 工具集成（后续独立 change）
- 不实现插件式工具注册（第一阶段内置工具）
- 不实现 Docker/SSH 远程环境（第一阶段仅本地终端）
- 不实现工具并发执行（第一阶段顺序执行）

## Decisions

### 1. 使用 Map 作为注册表存储

**Decision**: ToolRegistry 使用 `Map<string, ToolEntry>` 存储工具，键为工具名。

**Why**: TypeScript 原生数据结构，O(1) 查找，类型安全。比对象字典更易于迭代和检查。

### 2. 工具使用 ESM 模块自注册

**Decision**: 每个工具文件在模块顶层调用 `registry.register()`，通过 glob 扫描 `src/tools/*.ts` 并动态 import 实现发现。

**Why**: 参考实现使用 Python 的 import 时模块执行。TypeScript 编译后的 JS 可用 `import()` 动态加载。添加新工具无需修改注册列表。

**Alternatives considered**:
- 手动 import 列表：添加工具时需要修改入口文件，容易遗漏
- 配置文件声明：增加维护负担，不如代码即文档

### 3. 工具 handler 返回字符串（JSON 格式）

**Decision**: 所有工具 handler 返回 `string`（通常是 JSON.stringify 的结果），分发器保证返回值始终是合法 JSON 字符串。

**Why**: LLM 工具调用期望字符串结果。统一返回类型简化对话循环的处理逻辑。

### 4. 错误包装在分发器层完成

**Decision**: dispatch() 捕获所有异常，返回 `{"error": "message"}` JSON 字符串。handler 内部不需要 try/catch。

**Why**: 确保 LLM 始终收到结构化结果，不会收到未处理的异常堆栈。参考实现也是双层错误包装。

### 5. 终端工具使用 child_process.spawn

**Decision**: 终端工具使用 `child_process.spawn` 执行命令，支持 stdout/stderr 流式收集和超时。

**Why**: spawn 支持流式输出和进程控制，比 exec/execSync 更灵活。

**Alternatives considered**:
- execSync：阻塞调用，不支持超时和流式输出
- exec：缓冲区限制，不适合长输出

### 6. 危险命令审批使用正则模式匹配

**Decision**: 预定义 DANGEROUS_PATTERNS 正则列表，命令执行前匹配。匹配时返回审批请求而非执行结果。

**Why**: 简单有效，不需要理解命令语义。参考实现使用相同策略。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 动态 import 加载失败阻塞启动 | 单个工具 import 失败时 catch 并记录警告，不阻塞其他工具 |
| 工具名冲突 | 注册时检查重复，后注册的覆盖并记录警告 |
| 终端命令注入 | 危险命令审批 + 工作目录限制 + 超时保护 |
| 异步桥接事件循环冲突 | 检测是否已有运行中的事件循环，有则创建新线程执行 |
| 工具 schema 膨胀影响 token 使用 | 工具集过滤确保只发送启用的工具 schema |

## Open Questions

- 工具并发执行策略？（参考实现使用 ThreadPoolExecutor，TypeScript 可用 Promise.all）
- 是否需要工具执行沙箱？（第一阶段不需要，后续可加）
