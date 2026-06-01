## 为什么

业界成熟的自进化 AI Agent 系统拥有完整的插件化记忆系统，支持多种记忆提供者，通过 MemoryManager 统一编排。NanoHermes 需要实现相同的记忆系统架构，使 Agent 能够在跨会话中保持持久记忆。

**历史 vs 记忆**：
- **历史**（SessionDB）：原始数据，用户在第 N 次对话中说了什么
- **记忆**（Memory）：提炼后的知识，用户偏好 Python 而非 JavaScript、项目使用 PostgreSQL

**设计赌注回扣：** Memory Provider 是 **Personal Long-Term** 赌注的核心基础设施。通过可插拔的记忆后端，Agent 能够"越用越懂你"，从理念变为可测量的工程实现。

## 变更内容

- 实现 MemoryProvider 抽象基类，定义标准生命周期钩子（17 个方法，4 个 abstract）
- 实现 MemoryManager 编排器，管理记忆提供者，采用 Fan-out 容错设计
- 实现内置文件基础记忆提供者（MEMORY.md/USER.md）
- 实现上下文隔离标签（`<memory-context>`）和流式上下文清洗
- 实现单外部提供者限制，防止工具 schema 膨胀
- 实现 `on_memory_write` Mirror hook，保持内置记忆与外部 provider 同步
- 实现字符数限制（memory_char_limit=2200, user_char_limit=1375）

## 能力

### 新增能力

- `memory-provider-interface`: MemoryProvider 抽象基类，定义 17 个方法接口。其中 4 个核心抽象方法（`name`, `is_available`, `initialize`, `system_prompt_block`），其余 13 个有默认空实现。支持可选钩子：`on_turn_start`、`on_session_end`、`on_pre_compress`、`on_delegation`、`on_memory_write`。
- `memory-manager`: MemoryManager 编排器，管理记忆提供者生命周期。强制执行单外部提供者限制。采用 Fan-out 容错设计（一个 provider 失败不影响其他 provider 和主流程）。在 Agent 初始化、每轮对话前后调用提供者钩子。
- `file-memory-provider`: 内置文件基础记忆提供者，使用 MEMORY.md（Agent 记忆）和 USER.md（用户画像）文件。支持 add/replace/remove 操作。使用原子写入（临时文件 + rename）防止并发丢失。
- `context-fencing`: 上下文隔离机制，使用 `<memory-context>` 标签包裹注入的记忆上下文。提供 `sanitize_context` 函数和 `StreamingContextScrubber` 类清洗流式输出。

### 修改能力

<!-- 无现有能力需要修改 -->

## 影响

- 新增 `src/memory/` 目录，包含 `memory_provider.py`、`memory_manager.py`、`file_memory_provider.py`
- 新增 `src/memory/context_fencing.py` 包含上下文隔离逻辑
- 系统提示组装依赖记忆系统注入上下文
- 无破坏性变更，从零开始构建
- 预留外部 provider 接口（Honcho、Mem0、Hindsight、Holographic、OpenViking、RetainDB、SuperMemory、ByteRover 等 8 种）
- 当前处于"双轨接线"中间形态：内置记忆仍由 MemoryStore 直接加载，外部 provider 由 MemoryManager 管理
