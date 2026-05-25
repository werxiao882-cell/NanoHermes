## 为什么

业界成熟的自进化 AI Agent 系统拥有完整的插件化记忆系统，支持多种记忆提供者，通过 MemoryManager 统一编排。NanoHermes 需要实现相同的记忆系统架构，使 Agent 能够在跨会话中保持持久记忆。

## 变更内容

- 实现 MemoryProvider 抽象基类，定义标准生命周期钩子
- 实现 MemoryManager 编排器，管理记忆提供者
- 实现内置文件基础记忆提供者（MEMORY.md/USER.md）
- 实现上下文隔离标签（`<memory-context>`）和流式上下文清洗
- 实现单外部提供者限制，防止工具 schema 膨胀

## 能力

### 新增能力

- `memory-provider-interface`: MemoryProvider 抽象基类，定义 initialize、prefetch、sync_turn、shutdown 等标准生命周期钩子。支持可选钩子：on_turn_start、on_session_end、on_session_switch、on_pre_compress、on_delegation、on_memory_write。
- `memory-manager`: MemoryManager 编排器，管理记忆提供者生命周期。强制执行单外部提供者限制。在 Agent 初始化、每轮对话前后调用提供者钩子。
- `file-memory-provider`: 内置文件基础记忆提供者，使用 MEMORY.md（Agent 记忆）和 USER.md（用户画像）文件。支持 add/replace/remove 操作。
- `context-fencing`: 上下文隔离机制，使用 `<memory-context>` 标签包裹注入的记忆上下文。提供 sanitize_context 函数和 StreamingContextScrubber 类清洗流式输出。

### 修改能力

<!-- 无现有能力需要修改 -->

## 影响

- 新增 `src/memory/` 目录，包含 MemoryProvider、MemoryManager、FileMemoryProvider
- 新增 `src/memory/context-fencing.ts` 包含上下文隔离逻辑
- 系统提示组装依赖记忆系统注入上下文
- 无破坏性变更，从零开始构建
