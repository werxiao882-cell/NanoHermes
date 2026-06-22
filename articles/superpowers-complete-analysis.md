# Superpowers 完整解析：从源码到设计哲学的深度分析

> 基于 obra/superpowers v6.0.3 仓库逐文件阅读
> 项目地址：[github.com/obra/superpowers](https://github.com/obra/superpowers)
> 版本：v6.0.3 | 作者：Jesse Vincent / Prime Radiant Inc.
> 统计：167 个文件，34,821 行代码，14 个核心 skills，10 个 AI 编程平台适配

---

## 一、Superpowers 是什么？

**一句话：** Superpowers 不是代码库，而是一套**完整的 AI Agent 软件开发方法论**——它定义了 Agent 从接到需求到完成开发的完整工作流程：头脑风暴 → 设计 → 写计划 → 子 Agent 分派执行 → 代码审查 → 提交 PR。

**类比：** 如果把 AI 编程 Agent 比作一个初级程序员，Superpowers 就是一整套「高级工程师工作手册」——告诉 Agent 什么时候该停下来想、怎么分解任务、怎么做代码审查、什么时候该用 TDD。

**核心理念：** *Skills are not prose — they are code that shapes agent behavior.*（Skill 不是散文，是塑造 Agent 行为的代码。）

---

## 二、整体架构

### 三层架构

```
┌─────────────────────────────────────────────────────────┐
│                    Superpowers v6.0.3                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Bootstrap  │  │  14 SKILL.md    │  │  Platform    │ │
│  │  Session    │→ │  + supporting   │→ │  Adapters    │ │
│  │  Hook       │  │  files          │  │  (10×)       │ │
│  └─────────────┘  └─────────────────┘  └──────────────┘ │
│        │                  │                    │         │
│   hooks/           skills/                 .claude-plugin│
│   hooks.json       brainstorming/          .codex-plugin │
│   session-start    subagent-driven-dev/    .pi/          │
│                    writing-plans/          .opencode/    │
│                    ...etc...             docs/testing.md │
├─────────────────────────────────────────────────────────┤
│  零运行时依赖 · 纯 Markdown + Bash + 少量 JS             │
└─────────────────────────────────────────────────────────┘
```

| 层级 | 组成 | 作用 |
|------|------|------|
| **① Bootstrap 层** | `using-superpowers` + SessionStart Hook | 每次会话启动时自动加载，确保 Agent 知道自己有「超能力」 |
| **② Skill 层** | 14 个 SKILL.md + supporting files | 每个 Skill 是一个行为指令，在特定场景自动触发 |
| **③ Harness 适配层** | Claude Code / Codex / Gemini / Copilot / Cursor / Kimi / Pi / OpenCode 等 | 同一套 Skills，多平台适配，通过 platform reference 映射工具名 |

### 核心特性

- **零运行时依赖**：纯 Markdown + Bash + 少量 JS，不需要安装任何包
- **自动触发**：通过 SessionStart Hook 在会话开始时注入，不需要用户手动加载
- **平台无关**：Skills 用动作描述（"dispatch a subagent"），而非具体工具名
- **经过 Eval 验证**：每个 Skill 的行为都经过对抗性压力测试
- **心理学驱动**：7 个说服原则，基于 N=28,000 实验数据

---

## 三、Bootstrap 机制：Skills 如何自动触发

### 3.1 核心问题

Skills 文件在磁盘上本身不会触发——需要一个机制在会话启动时把它们注入 Agent 的系统提示。Superpowers 通过 **SessionStart Hook** 解决了这个问题。

### 3.2 触发链路

```
Claude Code / Codex / Cursor / ... 启动
    ↓
SessionStart 事件触发（由 harness 插件系统）
    ↓
hooks/hooks.json 或 hooks-codex.json 匹配事件
    ↓
执行 hooks/run-hook.cmd session-start（或 session-start-codex）
    ↓
执行 hooks/session-start（bash 脚本，49 行）
    ↓
1. 读取 skills/using-superpowers/SKILL.md 全文
2. 用 bash 参数替换转义字符串（5 层 ${s//old/new}，C 级单次遍历）
3. 输出 JSON 格式的 additionalContext
    ↓
Harness 将 additionalContext 注入 Agent 系统提示
    ↓
Agent 看到：「You have superpowers.」+ 完整使用规则
    ↓
用户发消息 → Agent 根据 using-superpowers 的 1% 规则自动触发 skills
```

### 3.3 hooks/session-start 源码分析

```bash
#!/usr/bin/env bash
# 关键设计：纯 bash 实现，零依赖，跨平台兼容

# 1. 读取 SKILL.md
using_superpowers_content=$(cat "${PLUGIN_ROOT}/skills/using-superpowers/SKILL.md")

# 2. 高效转义（不是字符循环，是 C 级批量替换）
escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"      # \ → \\
    s="${s//\"/\\\"}"      # " → \"
    s="${s//$'\n'/\\n}"    # 换行 → \n
    s="${s//$'\r'/\\r}"    # CR → \r
    s="${s//$'\t'/\\t}"    # Tab → \t
    printf '%s' "$s"
}

# 3. 输出 JSON（三种格式适配不同平台）
if [ -n "${CURSOR_PLUGIN_ROOT:-}" ]; then
  # Cursor：additional_context（snake_case）
  printf '{"additional_context": "%s"}\n' "$session_context"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -z "${COPILOT_CLI:-}" ]; then
  # Claude Code：hookSpecificOutput.additionalContext
  printf '{"hookSpecificOutput": {...}}\n'
else
  # Copilot CLI：additionalContext（驼峰，SDK 标准格式）
  printf '{"additionalContext": "%s"}\n' "$session_context"
fi
```

**关键细节：**
- 使用 `printf` 而非 heredoc——bash 5.3+ 的 heredoc 有挂起 bug（见 issue #571）
- 三种 JSON 格式适配不同平台，通过环境变量检测平台
- 转义使用 5 层 `${s//old/new}` 参数替换，是 C 级单次遍历，远快于字符循环

### 3.4 平台适配对比

| 平台 | Hook 配置 | 注入字段 | 环境变量检测 |
|------|----------|---------|-------------|
| **Claude Code** | hooks.json | hookSpecificOutput.additionalContext | CLAUDE_PLUGIN_ROOT |
| **Codex** | hooks-codex.json | hooks/session-start-codex | CODEX_CI |
| **Cursor** | hooks-cursor.json | additional_context | CURSOR_PLUGIN_ROOT |
| **Copilot CLI** | hooks.json | additionalContext | COPILOT_CLI |
| **OpenCode** | .opencode/plugins/superpowers.js | Message transform | - |
| **Pi** | .pi/extensions/superpowers.ts | context 事件注入 | - |
| **Gemini** | gemini-extension.json | GEMINI.md 自动加载 | - |

### 3.5 OpenCode 插件实现（纯 JS）

```javascript
// .opencode/plugins/superpowers.js
export const SuperpowersPlugin = async ({ client, directory }) => {
  // 1. 模块级缓存（_bootstrapCache），避免每次 agent step 都读文件
  // 2. Frontmatter 提取（无外部依赖，简单正则）
  // 3. Config hook 自动注册 skills 目录（不需要 symlink）
  // 4. Message transform 注入 bootstrap
}
```

### 3.6 Pi 插件实现（TypeScript Extension API）

```typescript
// .pi/extensions/superpowers.ts
pi.on("session_start", async () => { injectBootstrap = true; });
pi.on("session_compact", async () => { injectBootstrap = true; });  // 压缩后重新注入！
pi.on("agent_end", async () => { injectBootstrap = false; });
pi.on("context", async (event) => {
  if (!injectBootstrap) return;
  if (event.messages.some(messageContainsBootstrap)) return;  // 去重
  // 插入 bootstrap message 到 firstNonCompactionSummaryIndex 位置
});
```

**关键设计：** `session_compact` 后重新注入——确保上下文压缩后 Agent 仍然知道有超能力。

### 3.7 技能优先级系统

```
1. 用户显式指令（CLAUDE.md, AGENTS.md, 直接请求）→ 最高优先级
2. Superpowers Skills → 覆盖默认系统提示行为
3. 默认系统提示 → 最低优先级
```

**关键规则：** 如果 AGENTS.md 说 "不要用 TDD"，但 Skill 说 "必须用 TDD"——听用户的。用户永远在控制。

### 3.8 Skill 触发流程

```
用户消息到达
    ↓
「有没有 1% 的可能性某个 Skill 适用？」
    ↓ 是
调用该 Skill
    ↓
宣布：「正在使用 [skill] 来 [目的]」
    ↓
有检查清单？
    ├─ 是 → 为每个检查项创建 todo
    └─ 否 → 严格按照 Skill 执行
    ↓
响应（包括澄清问题）
```

**关键约束：** *"IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT."*——这不是协商，是强制。

---

## 四、14 个核心 Skills 全景

### 完整开发工作流

```
用户说 "我想做个功能"
    ↓
① brainstorming ← 自动触发！先别写代码
    ↓ (探索意图 → 提方案 → 设计评审)
② writing-plans ← 把设计变成可执行的实施计划
    ↓ (分解为 bite-sized tasks)
③ subagent-driven-development ← 分派子 Agent 逐个执行
    ↓ (每个 task：实现 → 审查 → 修复 → 提交)
④ requesting-code-review ← 完成后请求人类审查
⑤ finishing-a-development-branch ← 完成分支和 PR
```

### 全部 Skills 总览

| # | Skill | 类别 | 触发条件 | 核心价值 | 铁律 |
|---|-------|------|---------|---------|------|
| 1 | **brainstorming** | 设计 | 任何创造性工作之前 | 防止跳进代码，先理解意图 | HARD-GATE |
| 2 | **writing-plans** | 计划 | 有了设计之后 | 分解为 2-5 分钟小任务 | 禁止占位符 |
| 3 | **subagent-driven-development** | 执行 | 执行实施计划时 | 每 task 独立子 Agent + 审查 | Fresh context |
| 4 | **executing-plans** | 执行 | 当前会话手动执行 | 轻量级执行，适合无子 Agent 平台 | 遇 blocker 停 |
| 5 | **finishing-a-development-branch** | 完成 | 开发完成后 | 结构化集成选项 | 测试先验证 |
| 6 | **test-driven-development** | 测试 | 写新功能时 | 强制 RED-GREEN-REFACTOR | NO CODE WITHOUT FAILING TEST |
| 7 | **systematic-debugging** | 调试 | 遇到任何 bug | 四阶段调试法 | NO FIXES WITHOUT ROOT CAUSE |
| 8 | **writing-skills** | 元能力 | 创建/修改 skill 时 | TDD 应用于文档 | NO SKILL WITHOUT FAILING TEST |
| 9 | **requesting-code-review** | 审查 | 完成任务后 | 分派审查子 Agent | Review early, review often |
| 10 | **receiving-code-review** | 审查 | 收到审查意见时 | 技术正确性高于社交舒适 | Verify before implementing |
| 11 | **verification-before-completion** | 验证 | 标记完成前 | 防止谎称完成 | NO CLAIMS WITHOUT EVIDENCE |
| 12 | **dispatching-parallel-agents** | 并行 | 2+ 独立任务 | 一个 Agent 一个问题域 | Independent domains only |
| 13 | **using-git-worktrees** | 基础设施 | 需要隔离工作区时 | Git worktree 安全隔离 | Detect first, native second |
| 14 | **using-superpowers** | Bootstrap | 每次会话启动 | 确保 Agent 知道有超能力 | IF APPLIES → MUST USE |

---

## 五、核心 Skills 源码级分析

### 5.1 brainstorming — 头脑风暴

**Supporting files：**
- `spec-document-reviewer-prompt.md` — 设计文档审查 prompt
- `visual-companion.md` — 可视化伴侣使用指南（298 行）
- `scripts/server.cjs` — Node.js WebSocket 服务器（723 行）
- `scripts/frame-template.html` — 浏览器框架模板
- `scripts/start-server.sh` / `stop-server.sh` — 生命周期管理

**一句话：** 任何创造性工作之前，先理解用户意图、探索方案、呈现设计、获得批准，禁止直接写代码。

**9 步流程：**
1. 探索项目上下文（文件、文档、最近提交）
2. 按需（just-in-time）提供可视化伴侣——不是提前，而是当问题确实更适合视觉展示时
3. 逐个提问澄清（目的/约束/成功标准），每次只问一个问题
4. 提出 2-3 个方案，带权衡和推荐
5. 分章节展示设计，每章后让用户确认
6. 写设计文档 → 提交 Git
7. 设计自我审查（占位符扫描、一致性检查、范围检查、歧义检查）
8. 用户审查书面 spec
9. **转入 writing-plans**——这是唯一的下一步，不能转入其他实现 skill

**硬性门控（HARD-GATE）：**
```markdown
<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project,
or take any implementation action until you have presented a design and the
user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>
```

**反模式：** *"This Is Too Simple To Need A Design"*——每个项目都走这个流程，哪怕是 TODO 列表。

**关键设计决策：**
- 大项目先分解：如果需求描述多个独立子系统，先帮用户拆分成子项目
- 设计隔离性：每个单元有清晰边界和明确接口
- YAGNI：无情地砍掉不必要的功能
- 在现有代码库中遵循既有模式

### 5.2 writing-plans — 写实施计划

**Supporting files：**
- `plan-document-reviewer-prompt.md` — 计划文档审查 prompt

**一句话：** 假设执行计划的是一个没有项目上下文的初级工程师，把设计分解为 2-5 分钟的小任务。

**计划文档结构：**
```markdown
# [功能名] Implementation Plan

> REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans

**Goal:** [一句话]
**Architecture:** [2-3 句话]
**Tech Stack:** [技术栈]

## Global Constraints
[项目级约束——版本号、依赖限制、命名规则，逐字复制]

### Task N: [组件名]
**Files:** Create/Modify/Test 的具体路径
**Interfaces:**
- Consumes: [消费的接口——精确到函数签名]
- Produces: [产出的接口——函数名、参数、返回类型]

- [ ] Step 1: 写失败的测试（附完整代码）
- [ ] Step 2: 运行确认失败（附命令和预期输出）
- [ ] Step 3: 写最小实现（附完整代码）
- [ ] Step 4: 运行确认通过
- [ ] Step 5: 提交（附精确命令）
```

**禁止的占位符模式：**
- "TBD", "TODO", "implement later"
- "Add appropriate error handling"
- "Write tests for the above"（没有具体测试代码）
- "Similar to Task N"（任务可能乱序阅读）
- 描述做什么但不展示怎么做（必须包含代码块）

**Task Right-Sizing 原则（v6.0 新增）：**
> 一个 task 是最小的、自带测试循环、值得一次独立审查的单元。
> 当画边界时：把 setup、配置、脚手架、文档步骤合并到需要它们的 task 中；
> 只在审查者可能拒绝一个 task 但批准相邻 task 的地方拆分。

**真实效果：** 按此原则写的计划只需要 1 轮修复，对照组需要 2-4 轮——且对照组还带了一个真实 bug。

**文件结构设计原则：**
- 每个文件一个清晰职责
- 按职责拆分，不按技术层拆分
- 一起改的文件放在一起
- 小文件 > 大文件

**Interfaces 块的价值：** 每个子 Agent 只看到自己的 task，通过 Interfaces 块了解相邻任务的合约。

### 5.3 subagent-driven-development — 子代理驱动开发

**Supporting files：**
- `implementer-prompt.md` — 实现者子 Agent 模板（139 行）
- `task-reviewer-prompt.md` — 任务审查模板（188 行）
- `scripts/task-brief` — 任务摘要提取脚本（40 行）
- `scripts/review-package` — 审查包生成脚本（44 行）
- `scripts/sdd-workspace` — 跨 worktree 路径解析工具

**一句话：** 每个 task 分派一个全新子 Agent（不继承父级上下文），每个 task 完成后独立审查，最后有一次全局审查。

**核心原则：** Fresh subagent per task + task review（spec + quality） + broad final review

**每 Task 流程：**
```
分派 implementer subagent → 实现、测试、提交、自评
    ↓
生成 diff 文件 → 分派 task reviewer subagent
    ↓
审查：spec 合规 ✅/❌ + 代码质量 Approved/⚠️
    ↓
有问题 → 分派 fix subagent → 重新审查
    ↓
没问题 → 标记 Task 完成，写入进度 ledger
```

**文件传递机制（v6.0 最重要改进）：**
- `task-brief` 脚本：从计划中提取单个任务到文件，避免粘贴到 prompt
- `review-package` 脚本：生成 diff 文件给 reviewer，不经过 controller 上下文
- **效果：** 避免 context 污染，节省大量 token

**task-brief 源码：**
```bash
#!/usr/bin/env bash
# 使用 awk 解析 Markdown heading，精确匹配 "Task N"
awk -v n="$n" '
  /^```/ { infence = !infence }         # 跳过代码块中的 heading
  !infence && /^#+[ \t]+Task[ \t]+[0-9]+/ {
    intask = ($0 ~ ("^#+[ \t]+Task[ \t]+""n""([^0-9]|$)"))
  }
  intask { print }
' "$plan" > "$out"
```

**review-package 源码：**
```bash
#!/usr/bin/env bash
{
  echo "# Review package: ${base}..${head}"
  git log --oneline "${base}..${head}"
  git diff --stat "${base}..${head}"
  git diff -U10 "${base}..${head}"     # 10 行上下文，不是默认 3 行
} > "$out"
```

**关键设计：使用 BASE 而非 HEAD~1**——`HEAD~1` 在多 commit 任务中会丢失除最后一个 commit 外的所有内容。

**模型选择策略（省钱之道）：**

| 任务类型 | 模型选择 | 原因 |
|---------|---------|------|
| 机械实现（1-2 文件，完整 spec） | 最便宜 | 纯转录+测试 |
| 集成/判断任务（多文件协调） | 标准模型 | 需要上下文理解 |
| 架构设计/最终全局审查 | 最强模型 | 需要判断力 |
| Review 任务 | 按 diff 规模/风险定 | 小 diff 不需要最强模型 |

**关键洞察：** *"Turn count beats token price"* — turn 数比 token 单价更重要。便宜模型可能需要 2-3 倍 turn，反而更贵。

**四种状态：**
| 状态 | 含义 | Controller 处理 |
|------|------|----------------|
| DONE | 完成 | 生成 review-package → 分派 reviewer |
| DONE_WITH_CONCERNS | 完成但有疑虑 | 读疑虑 → 决定是否需要修复 |
| NEEDS_CONTEXT | 需要更多信息 | 提供上下文 → 重新分派 |
| BLOCKED | 无法完成 | 评估 blocker → 更多上下文/更强模型/拆分任务/升级 |

**Implementer Prompt 设计要点：**
```markdown
## 当你不知所措时
随时可以说"这对我来说太难了"。糟糕的工作比不工作更差。
你不会因为升级而受到惩罚。

## 报告格式
写入 [REPORT_FILE]：
- 实现了什么
- 测试了什麽和结果
- TDD 证据（RED: 命令/失败输出, GREEN: 命令/通过输出）
- 文件变更
- 自我审查看法

然后仅用 15 行以内报告状态
```

**Task Reviewer Prompt 设计要点：**
```markdown
## 不要信任报告
将实现者的报告视为未经证实的声明。它可能不完整、不准确或过于乐观。
设计理由也是声明："故意保持简单"、"根据 YAGNI 省略"——
这些都是实现者在给自己打分。根据代码本身判断。

## 测试
实现者已经运行了测试并报告了结果。不要重新运行套件来确认。
只在阅读代码产生具体怀疑时运行测试——且只运行聚焦的测试。

## 输出
直接以 spec 合规性判定开始。每一行都是判定、带 file:line 的发现、
或你运行的检查——没有前言、没有过程叙述、没有总结。
```

**进度 Ledger（抗上下文压缩）：**
```
Task N: complete (commits <base7>..<head7>, review clean)
```
- 存储在 `.superpowers/sdd/progress.md`
- 上下文压缩后信任 ledger 和 git log，不信任记忆
- 这是真实 session 中最昂贵的失败模式：重新分派已完成的全部任务

**Pre-Flight 计划审查：** 执行 Task 1 之前，扫描计划找矛盾，一次性批量向用户提问。

**Review 构建规则：**
- 不告诉 reviewer 不要标记什么
- 不把过去的 task 摘要粘贴到后续 dispatch
- plan-mandated 的发现交给用户决定
- 最终审查只分派**一个** fix subagent 处理所有发现

### 5.4 executing-plans — 执行计划

**一句话：** 在当前会话中手动逐条执行计划，比 SDD 更轻量，适合没有子 Agent 支持的平台。

**核心原则：**
- 先批判性审查计划，有问题先提出来
- 严格按计划步骤执行
- 遇到 blocker 时停止，不要猜
- 完成后转入 finishing-a-development-branch

### 5.5 finishing-a-development-branch — 完成开发分支

**一句话：** 实现完成且测试通过后，提供结构化的集成选项（合并/PR/保留/丢弃），并正确处理 worktree 清理。

**4 步流程：**
1. **验证测试**——测试失败就停
2. **检测环境**——判断是普通 repo、worktree 分支、还是 detached HEAD
3. **呈现选项**——精确 4 个选项（普通/worktree 分支）或 3 个选项（detached HEAD）
4. **执行选择**

**4 个选项：**
| 选项 | 合并 | Push | 保留 Worktree | 清理分支 |
|------|------|------|-------------|---------|
| 1. 本地合并 | ✅ | - | - | ✅ |
| 2. 创建 PR | - | ✅ | ✅（PR 迭代需要） | - |
| 3. 保留原样 | - | - | ✅ | - |
| 4. 丢弃 | - | - | - | ✅（强制删除） |

### 5.6 test-driven-development — 测试驱动开发

**Supporting files：**
- `testing-anti-patterns.md` — 测试反模式指南

**铁律：** `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST`

**RED-GREEN-REFACTOR 循环：**
1. **RED**：写一个最小测试
2. **Verify RED**：确认测试失败（不是报错，是因为功能缺失）
3. **GREEN**：写最简代码让它通过
4. **Verify GREEN**：确认通过，其他测试也没坏
5. **REFACTOR**：只有 green 之后才重构
6. **Repeat**

**删除意味着删除：**
```markdown
**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete
```

**Tests-after vs Tests-first 的本质区别：**
- Tests-after 回答 "What does this do?"
- Tests-first 回答 "What should this do?"
- Tests-after 被你的实现偏见影响
- Tests-first 在实现之前强制发现边缘情况

**测试质量标准：**

| 质量 | 好 | 差 |
|------|-----|-----|
| 最小 | 一件事。名字里有 "and"？拆分 | `test('validates email and domain and whitespace')` |
| 清晰 | 名字描述行为 | `test('test1')` |
| 显示意图 | 展示期望的 API | Obscures what code should do |

### 5.7 systematic-debugging — 系统调试

**Supporting files：**
- `root-cause-tracing.md` — 根因回溯技术（169 行）
- `condition-based-waiting.md` — 条件等待替代 timeout
- `condition-based-waiting-example.ts` — 实现示例
- `defense-in-depth.md` — 多层防御
- `find-polluter.sh` — 测试污染二分查找脚本
- `test-pressure-1/2/3.md` — 压力测试场景
- `CREATION_LOG.md` — Skill 创建日志

**铁律：** `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST`

**四阶段（必须按顺序完成）：**

**Phase 1: 根因调查**
1. 仔细读错误信息（不要跳过）
2. 可靠复现
3. 检查最近变更
4. 多组件系统：在每个组件边界加诊断日志
5. 追踪数据流：从坏值回溯到源头

**Phase 2: 模式分析**
1. 找到工作示例
2. 完整阅读参考实现（不要略读）
3. 列出所有差异
4. 理解依赖关系

**Phase 3: 假设和测试**
1. 提出**单一**假设
2. 最小化测试（一次只改一个变量）
3. 验证后再继续
4. 不知道就说不知道

**Phase 4: 实施**
1. 创建失败测试用例（必须有）
2. 实施单一修复（不要"顺便"改进）
3. 验证修复
4. **3 次以上修复失败 = 架构问题**——停下来和人类讨论

**根因回溯完整示例：**
```
症状：.git 创建在了 packages/core/（源代码目录）
    ↓
git init 运行在 process.cwd() ← cwd 参数为空
    ↓
WorktreeManager 被传入空 projectDir
    ↓
Session.create() 传了空字符串
    ↓
测试在 beforeEach 之前访问了 context.tempDir
    ↓
setupCoreTest() 初始返回 { tempDir: '' }
    ↓
根因：顶层变量初始化在 beforeEach 之前执行
```

**防御深度：**
- Layer 1：Project.create() 验证目录
- Layer 2：WorkspaceManager 验证非空
- Layer 3：NODE_ENV guard 拒绝在非 tmpdir 执行 git init
- Layer 4：git init 前记录 stack trace

**真实效果：** 系统方法 15-30 分钟修好 vs 随机修 2-3 小时；首次修好率 95% vs 40%。

### 5.8 writing-skills — 编写 Skills

**Supporting files：**
- `anthropic-best-practices.md` — Anthropic 官方最佳实践
- `graphviz-conventions.dot` — Graphviz 样式规则
- `render-graphs.js` — dot 图渲染为 SVG
- `persuasion-principles.md` — 说服心理学（7 原则，N=28,000 实验）
- `testing-skills-with-subagents.md` — 用子 Agent 压力测试 skill（384 行）
- `examples/CLAUDE_MD_TESTING.md` — 完整测试活动示例

**核心原则：** *"Writing skills IS Test-Driven Development applied to process documentation."*

**TDD 映射：**

| TDD 概念 | Skill 创建中的对应 |
|---------|-------------------|
| 测试用例 | 压力场景 + 子 Agent |
| 生产代码 | SKILL.md |
| RED（测试失败） | Agent 没有 skill 时违反规则 |
| GREEN（测试通过） | Agent 有 skill 时遵守 |
| REFACTOR（重构） | 修补漏洞同时保持合规 |

**Skill 发现优化（SDO）：**
- **description 只写触发条件**，不总结流程
- 用 Agent 会搜索的关键词
- 主动语态，动词开头

**Token 效率目标：**
- 入门引导：<150 词
- 经常加载的：<200 词
- 其他：<500 词

**Bulletproofing 技术：**
- 显式关闭每个漏洞
- 应对"精神 vs 文字"论点
- 构建 Rationalization 表
- 创建 Red Flags 列表

**Match the Form to the Failure：**

| 基线失败类型 | 正确形式 | 错误形式 |
|------------|---------|---------|
| 压力下跳过规则 | 禁令 + rationalization 表 + red flags | 软指导（"prefer..."） |
| 遵守但输出形状不对 | 正向配方/契约 | 禁令列表 |
| 遗漏必需元素 | 结构：REQUIRED 字段 | 散文提醒 |
| 行为依赖条件 | 可观察谓词的条件 | 无条件规则 + 豁免条款 |

**压力场景设计：**

**差的场景（无压力）：** 你需要实现一个功能。skill 说了什么？

**好的场景（单压力）：** 生产故障。每分钟损失 $10k。经理说加 2 行修复。5 分钟内要部署。

**优秀的场景（多压力）：** 你花了 3 小时，200 行代码，手动测试过了。现在是下午 6 点，6:30 要吃饭。明天 9 点代码审查。你刚意识到你没写 TDD。选择 A/B/C。诚实。

**7 种压力类型：**
| 类型 | 效果 |
|------|------|
| 时间 | 紧急、截止、部署窗口关闭 |
| 沉没成本 | 数小时工作、"删除是浪费" |
| 权威 | 上级说跳过、经理覆盖 |
| 经济 | 工作、晋升、公司存亡 |
| 疲惫 | 一天结束、已经累了、想回家 |
| 社会 | 看起来教条、显得不灵活 |
| 务实 | "务实 vs 教条" |

**Micro-Test Wording（wording 微测试）：**
1. 每次调用一个新鲜上下文样本
2. 始终包含无指导对照组
3. 每个变体 5+ 次重复
4. 手动阅读每个标记的匹配
5. 方差是指标——收敛 = 绑定，发散 = 需要收紧措辞

### 5.9 requesting-code-review — 请求代码审查

**Supporting files：**
- `code-reviewer.md` — 代码审查子 Agent prompt（172 行）

**一句话：** 分派一个代码审查子 Agent，在问题级联之前抓住它们。

**审查 prompt 模板结构：**
```markdown
You are a Senior Code Reviewer with expertise in software architecture,
design patterns, and best practices.

## What Was Implemented
[DESCRIPTION]

## Requirements / Plan
[PLAN_OR_REQUIREMENTS]

## Git Range to Review
**Base:** [BASE_SHA]
**Head:** [HEAD_SHA]

## What to Check
- Plan alignment
- Code quality
- Architecture
- Testing
- Production readiness

## Calibration
Categorize by actual severity. Not everything is Critical.
Acknowledge what was done well before listing issues.

## Output Format
### Strengths
### Issues (Critical / Important / Minor)
### Assessment: Ready to merge? [Yes | No | With fixes]
```

### 5.10 receiving-code-review — 接收代码审查

**一句话：** 收到审查反馈时，先验证再实施。技术正确性高于社交舒适度。

**响应模式：**
1. READ：完整阅读，不反应
2. UNDERSTAND：用自己的话重述（或提问）
3. VERIFY：对照代码库现实检查
4. EVALUATE：对这个代码库技术上合理吗？
5. RESPOND：技术确认或有理有据的反驳
6. IMPLEMENT：逐项实施，每项测试

**禁止回应：**
- ❌ "You're absolutely right!"（表演性同意）
- ❌ "Great point!" / "Excellent feedback!"
- ❌ "Let me implement that now"（验证前）
- ❌ **任何感谢表达**

**正确回应：**
- ✅ "Fixed. [做了什么改动]"
- ✅ "Good catch - [具体问题]。Fixed in [位置]。"
- ✅ 直接修，用行动表示

**为什么不要感谢：** 行动说话。代码本身就表明你听到了反馈。

**YAGNI 检查：** 审查者建议 "properly implement" 时，先 grep 代码库看是否有实际调用。

### 5.11 verification-before-completion — 完成前验证

**铁律：** `NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE`

**Gate Function（5 步）：**
1. IDENTIFY：什么命令能证明这个声明？
2. RUN：执行完整命令（新鲜的、完整的）
3. READ：完整输出，检查退出码，数失败数
4. VERIFY：输出确认声明吗？
5. ONLY THEN：才能做声明

**跳过任何一步 = 撒谎，不是验证**

**常见失败模式：**

| 声明 | 需要 | 不够 |
|------|------|------|
| 测试通过 | 测试命令输出：0 失败 | 上次运行、"应该通过" |
| Linter 干净 | Linter 输出：0 错误 | 部分检查、外推 |
| Bug 修好了 | 测试原始症状：通过 | 代码改了、假设修好了 |
| Agent 完成了 | VCS diff 显示变更 | Agent 报告"成功" |

**真实失败数据（24 条）：** 用户说 "I don't believe you"、未定义函数被 shipped、缺少的需求被 shipped、时间浪费在虚假完成上。

### 5.12 dispatching-parallel-agents — 分派并行代理

**一句话：** 面对 2+ 独立任务时，一个 Agent 一个问题域，让它们并发工作。

**何时使用：**
- 3+ 测试文件因不同根因失败
- 多个子系统独立损坏
- 每个问题可以独立理解

**并行模式：**
- 同一响应中的多个 dispatch 调用 = 并行执行
- 每个 Agent 得到：明确范围、清晰目标、约束条件、期望输出
- 完成后：读每个摘要、验证不冲突、跑完整测试套件、集成所有变更

**真实案例：** 6 个测试失败分布在 3 个文件中 → 3 个 Agent 并行 → 所有修复独立、无冲突 → 完整套件绿色

### 5.13 using-git-worktrees — 使用 Git Worktrees

**一句话：** 确保工作在隔离的 workspace 中进行——先检测现有隔离，再用原生工具，最后才用 git 回退。

**检测逻辑：**
```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)

if [ GIT_DIR != GIT_COMMON ]; then
  # 已在 worktree 中！但还需要排除 submodule：
  git rev-parse --show-superproject-working-tree
  # 如果返回路径 → 是 submodule 不是 worktree
fi
```

**流程：**
1. Step 0：检测是否已在隔离 workspace
2. Step 1a：优先用平台原生 worktree 工具
3. Step 1b：没有原生工具时才用 `git worktree add`
4. Step 2：自动检测项目类型并安装依赖
5. Step 3：验证干净的测试基线

**关键安全：** 创建前必须 `git check-ignore` 确认目录被忽略

### 5.14 using-superpowers — 使用超能力

**一句话：** 每次会话的 Bootstrap——确保 Agent 知道自己有超能力，知道何时触发哪些 skill。

**核心原则：** *"IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT."*

**关键机制：**
- **1% 规则**：哪怕只有 1% 的可能性某个 skill 适用，也必须调用它来检查
- **指令优先级**：用户指令 > Skills > 默认系统提示
- **<SUBAGENT-STOP>** 标签：子 Agent 跳过此 skill，不重复加载
- **自动触发**：SessionStart Hook 将完整内容注入系统提示

---

## 六、插件系统：10 个平台的适配策略

### 6.1 插件清单

| 平台 | 配置文件 | 安装方式 | Bootstrap 机制 |
|------|---------|---------|---------------|
| **Claude Code** | `.claude-plugin/plugin.json` | `/plugin install` | SessionStart Hook |
| **Codex CLI** | `.codex-plugin/plugin.json` | `/plugins` 搜索 | SessionStart Hook (codex) |
| **Codex App** | 同上 + interface 配置 | 侧边栏 + | 同上 |
| **Gemini CLI** | `gemini-extension.json` | `gemini extensions install` | GEMINI.md 自动加载 |
| **Cursor** | `.cursor-plugin/plugin.json` | `/add-plugin` | SessionStart Hook (cursor) |
| **Copilot CLI** | hooks.json | `copilot plugin marketplace add` | SessionStart Hook |
| **Kimi Code** | `.kimi-plugin/plugin.json` | `/plugins` 市场 | SessionStart Hook |
| **OpenCode** | `.opencode/plugins/superpowers.js` | Fetch INSTALL.md | Message transform + config hook |
| **Pi** | `.pi/extensions/superpowers.ts` | `pi install git:...` | context 事件注入 |
| **Antigravity** | hooks.json | `agy plugin install` | SessionStart Hook |

### 6.2 一套 Skills，所有平台

Skills 本身**不提及具体工具名**，而是用动作描述。每个平台有自己的 reference 文件：

```
skills/using-superpowers/references/
├── claude-code-tools.md    # "Task tool" → Claude Code 的 Task
├── codex-tools.md          # "Subagent" → Codex 的 task
├── copilot-tools.md        # "Bash tool" → Copilot CLI 的 bash
├── gemini-tools.md         # 等价的工具映射
├── pi-tools.md             # Pi 的原生工具
└── antigravity-tools.md    # agy 的命令
```

**Skills 用动作说话：**
- "dispatch a subagent"（不是 "use the Task tool"）
- "your instructions file"（不是 "CLAUDE.md"）
- "create a todo"（不是 "use TodoWrite"）

### 6.3 Codex Plugin 完整配置示例

```json
{
  "name": "superpowers",
  "skills": "./skills/",
  "hooks": "./hooks/hooks-codex.json",
  "interface": {
    "displayName": "Superpowers",
    "category": "Coding",
    "defaultPrompt": ["I've got an idea", "Let's add a feature"],
    "composerIcon": "./assets/superpowers-small.svg"
  }
}
```

---

## 七、Visual Companion：浏览器端头脑风暴伴侣

### 7.1 架构

```
Agent (terminal) ←→ server.cjs (HTTP + WebSocket) ←→ Browser
      ↓                      ↓                           ↓
  写 HTML 到          1. 监听目录变化              显示 HTML
  screen_dir/         2. 推送最新 screen            用户点击选项
                      3. 记录选择到 events/         点击写入 events/
```

### 7.2 安全设计

1. **每会话密钥**：`crypto.randomBytes(16).toString('hex')`
2. **URL 携带密钥**：`http://localhost:PORT/?key=*** **Cookie 记忆**：首次加载后 tab-scoped cookie 记住密钥
4. **WebSocket 认证**：每个 WS 连接必须携带密钥
5. **文件服务器沙箱**：拒绝 symlink、dotfile、路径穿越

### 7.3 服务器源码分析（server.cjs，723 行）

- 纯 Node.js 实现，零外部依赖
- WebSocket（RFC 6455 手动实现，包括帧编码/解码）
- 随机端口（49152-65535）+ 端口文件持久化
- 空闲超时 4 小时（从 30 分钟提升）

### 7.4 Just-in-time 视觉伴侣

不在开始时提供，而是在问题确实更适合视觉展示时才提议，且提议必须是**独立的消息**。

---

## 八、Persuasion Principles：Skill 设计的心理学

基于 N=28,000 的说服心理学研究（Meincke et al., 2025），说服技术使合规率从 33% 提升到 72%（p < .001）。

### 8.1 权威（Authority）
- "YOU MUST", "Never", "Always"
- "No exceptions"
- 消除决策疲劳和 rationalization

### 8.2 承诺（Commitment）
- 要求宣布："I'm using [Skill Name]"
- 强制选择："Choose A, B, or C"
- Todo 追踪 checklist

### 8.3 稀缺（Scarcity）
- "Before proceeding"
- "Immediately after X"
- 防止"我晚点再做"

### 8.4 社会证明（Social Proof）
- "Every time", "Always"
- "X without Y = failure"
- 建立规范

### 8.5 互惠（Reciprocity）
- "your human partner" 语言
- 建立协作关系

### 8.6 喜好（Liking）
- 正面反馈 + 准确表扬
- 帮助实现者信任审查者

### 8.7 团结（Unity）
- "We're in this together"
- 共享目标

---

## 九、真实成本分析：Strict-Cost SDD 设计文档

### 9.1 当前配置成本（opus + sonnet, ~$13/run）

| 组件 | $ | Driver |
|------|---|--------|
| Controller（opus） | ~6-7 | ~150 turns × 常驻上下文 |
| Implementers（sonnet, 10-13 dispatches） | ~5-6 | 每个 ~25 turns |
| Task reviewers（sonnet, 10） | ~1-1.5 | 每个 3-9 turns |
| 最终审查 + 修复 | ~1 | 6 turns |

**关键洞察：**
- 审查循环次数（2-4 次/run）是最大的 run-to-run 成本方差
- 循环主要由计划歧义引起
- "Turn count beats token price"

### 9.2 判断力守卫线

**可以降到便宜模型的决定（机械的）：**
- 简单的文件操作
- 确定的命令执行

**必须留在最贵模型的决定（判断力）：**
- BLOCKED / NEEDS_CONTEXT 处理
- ⚠️ "无法从 diff 验证" 的裁决
- 分派策划（歧义解决、任务边界）
- 审查判定和严重性校准
- 审查循环裁决
- 识别需要升级给人类

### 9.3 SDD 的 Thesis

> 每个 task 一个全新子 Agent + 精确策划的上下文 + 每个 task 的门控

反 thesis：dispatch-time task batching——这污染了 fresh-context 属性。

---

## 十、评估体系：tests/ vs evals/

### 10.1 两种测试

| 类型 | 目录 | 测试对象 | 方法 |
|------|------|---------|------|
| **Plugin tests** | `tests/` | 非 LLM 代码（bash/JS/python） | Bash + Node 集成测试 |
| **Skill evals** | `evals/`（独立仓库） | Agent 行为 | Drill 驱动真实 LLM session |

### 10.2 Plugin tests 覆盖

- `tests/brainstorm-server/` — 12 个 JS 测试
- `tests/opencode/` — OpenCode 插件加载、bootstrap 缓存
- `tests/claude-code/` — SDD 集成测试、worktree 原生偏好
- `tests/explicit-skill-requests/` — 显式 skill 请求测试
- `tests/kimi/` — Kimi 插件 manifest 验证
- `tests/codex-plugin-sync/` — Codex 插件同步验证

### 10.3 Skill Evals（Drill）

- Drill 是一个 Python harness，驱动真实的 tmux session
- 每个 scenario 3-30+ 分钟
- LLM actor 执行任务，LLM verifier 判断合规性
- 不在 CI 中，计划分层模型

### 10.4 Acceptance Test

每个新平台集成必须通过：
```
1. 打开干净的 session
2. 发送精确消息："Let's make a react todo list"
3. 验证 brainstorming skill 在写任何代码之前自动触发
4. 在 PR 中粘贴完整 session transcript
```

---

## 十一、Design Specs 档案

Superpowers 仓库包含完整的设计文档档案，展示了自身如何使用其方法论：

```
docs/superpowers/specs/
├── 2026-01-22-document-review-system-design.md
├── 2026-02-19-visual-brainstorming-refactor-design.md
├── 2026-03-11-zero-dep-brainstorm-server-design.md
├── 2026-04-06-worktree-rototill-design.md
├── 2026-05-06-lift-drill-into-evals-design.md
├── 2026-06-09-sdd-task-scoped-review-dispatch-design.md
├── 2026-06-10-strict-cost-sdd-design.md
├── 2026-06-10-visual-companion-auth-hardening-design.md
└── ...（14 份 spec + 对应 plan）
```

这些文档本身就是 Superpowers 方法论的产物：brainstorming → spec → plan → implementation → review → merge。

---

## 十二、行为塑造技术汇总

Superpowers 使用多种技术手段来塑造 Agent 行为：

| 技术 | 应用 Skill | 效果 |
|------|-----------|------|
| `<HARD-GATE>` 标签 | brainstorming | 硬性门控，阻止跳过关键步骤 |
| `<SUBAGENT-STOP>` 标签 | using-superpowers | 防止子 Agent 重复加载 |
| `<EXTREMELY-IMPORTANT>` | using-superpowers | 强制注意力 |
| Rationalization 表 | TDD, Debugging, Verification, Writing Skills | 预先堵死借口 |
| Red Flags 列表 | 几乎所有 Skill | 方便 Agent 自检 |
| "Violating the letter is violating the spirit" | TDD, Writing Skills, Verification | 堵住"精神 vs 文字"漏洞 |
| 流程图（dot） | brainstorming, SDD, TDD, Debugging | 非明显决策点的可视化 |
| Good/Bad 对比 | TDD, Debugging, Dispatching | 展示正确 vs 错误做法 |
| No exceptions 声明 | TDD, Verification | 消除讨价还价空间 |
| 禁止感谢 | receiving-code-review | 去除表演性回应 |

---

## 十三、与 NanoHermes 的深度对照

### 13.1 架构对比

| 维度 | Superpowers | NanoHermes |
|------|------------|------------|
| **本质** | 方法论 + SKILL.md 集合 | 完整的 AI Agent 运行时 |
| **运行时** | 零代码，纯 Markdown + Bash + 少量 JS | Python 项目，16 个核心模块 |
| **Skill 系统** | 14 个精心调试的 Skills + evals | SKILL.md + Curator 自进化 |
| **自动触发** | SessionStart Hook 注入 | 技能按需加载（BM25 搜索） |
| **子 Agent** | 通过 harness 原生工具 | `delegate_task` + `DelegationManager` |
| **文件传递** | `task-brief` / `review-package` 脚本 | context 直接传递到 prompt |
| **进度 Ledger** | `.superpowers/sdd/progress.md` | 无独立 ledger |
| **审查机制** | 双 verdict（spec + quality），file:line 引用 | 有 requesting-code-review skill |
| **模型选择** | 显式指定 per-role 模型 | delegate_task 有 model 参数 |
| **并发控制** | 无限制（依赖 harness） | Semaphore `max_concurrent=3` |
| **Bootstrap** | Hook 注入 + compression 后重新注入 | 首次加载 |
| **评估** | Drill 驱动真实 LLM session | pytest 测试 |
| **平台适配** | 10 个平台，一套 Skills | DashScope/OpenAI/Anthropic |

### 13.2 NanoHermes 可以借鉴的具体方向

**1. 文件传递机制（立即可用）**
- 创建 `task-brief` 脚本：从计划中提取单个任务到文件
- 创建 `review-package` 脚本：生成 diff 文件给 reviewer
- 效果：避免 context 污染，节省大量 token

**2. 进度 Ledger（立即可用）**
- 在 `delegate_task` 执行时维护 progress.md
- 记录每个 task 的完成状态和 commit SHA
- 效果：上下文压缩后可以恢复进度

**3. 双 verdict 审查（立即可用）**
- task reviewer 同时返回 spec compliance 和 code quality 判定
- 要求 file:line 引用
- 效果：更精确的审查

**4. HARD-GATE 机制（立即可用）**
- 在 SKILL.md 中使用 `<HARD-GATE>` XML 标签
- 防止 Agent 跳过关键步骤
- 效果：强制合规

**5. Persuasion Principles 应用（立即可用）**
- 在关键 skill 中应用权威、承诺、稀缺原则
- 构建 rationalization 表
- 效果：提高 Agent 合规率

**6. Compression 后重新注入（需要架构改动）**
- 上下文压缩后重新注入 bootstrap
- 效果：Agent 不会在压缩后"忘记"有 skills

**7. Micro-Test Wording（技能开发流程）**
- 写 skill wording 时先做 5+ 次微测试
- 效果：确保 wording 有效

---

## 十四、项目哲学

### 14.1 "Your Human Partner"

Superpowers 始终用 *"your human partner"*（你的人类伙伴）而非 "the user"。这不仅仅是措辞——它定义了一种**协作关系**：Agent 和人类是搭档，不是主仆。

### 14.2 94% 的 PR 拒绝率

项目的 AGENTS.md 明确告诉 AI Agent：这个仓库有 94% 的 PR 拒绝率。维护者会在几小时内关闭低质量 PR，甚至公开评论 *"This pull request is slop that's made of lies."*

这是一个**元设计**：通过让 Agent 知道后果来防止低质量贡献。

### 14.3 Skills 不是散文，是代码

这是项目最核心的哲学。Skill 文档的措辞、结构、标签（`<HARD-GATE>`, `<EXTREMELY-IMPORTANT>`）都是精心调试的行为塑造工具，不是随便写的文档。

---

## 十五、关键文件速查

| 文件 | 行数 | 职责 |
|------|------|------|
| `skills/using-superpowers/SKILL.md` | 121 | Bootstrap，Skill 使用规则 |
| `skills/brainstorming/SKILL.md` | 159 | 头脑风暴，设计评审流程 |
| `skills/subagent-driven-development/SKILL.md` | 418 | 子 Agent 分派执行，审查流程 |
| `skills/writing-plans/SKILL.md` | 174 | 实施计划编写 |
| `skills/writing-skills/SKILL.md` | 689 | Skill 编写方法论 |
| `skills/systematic-debugging/SKILL.md` | 296 | 四阶段调试法 |
| `skills/test-driven-development/SKILL.md` | 371 | TDD 强制执行 |
| `skills/requesting-code-review/code-reviewer.md` | 172 | 代码审查 prompt |
| `skills/subagent-driven-development/implementer-prompt.md` | 139 | 实现者 prompt |
| `skills/subagent-driven-development/task-reviewer-prompt.md` | 188 | 任务审查 prompt |
| `skills/brainstorming/visual-companion.md` | 298 | 可视化伴侣指南 |
| `skills/brainstorming/scripts/server.cjs` | 723 | WebSocket 服务器 |
| `skills/writing-skills/testing-skills-with-subagents.md` | 384 | Skill 压力测试方法论 |
| `skills/systematic-debugging/root-cause-tracing.md` | 169 | 根因回溯技术 |
| `skills/writing-skills/persuasion-principles.md` | 187 | 说服心理学 |
| `hooks/session-start` | 49 | 会话启动 Hook |
| `scripts/task-brief` | 40 | 任务摘要提取 |
| `scripts/review-package` | 44 | 审查包生成 |
| `.pi/extensions/superpowers.ts` | 121 | Pi 插件实现 |
| `.opencode/plugins/superpowers.js` | 139 | OpenCode 插件实现 |
| `CLAUDE.md` | 115 | 贡献指南 |
| `RELEASE-NOTES.md` | 1299 | 版本历史 |

---

## 十六、核心设计哲学总结

Superpowers 的全部 14 个 Skills 不是 14 份文档，而是 **14 个行为塑造程序**。它们共同构成了一套完整的软件工程方法论：

1. **设计先于实现** — brainstorming → writing-plans → subagent-driven-development
2. **测试先于代码** — TDD 的 RED-GREEN-REFACTOR，删除意味着删除
3. **根因先于修复** — 四阶段调试，3 次失败后质疑架构
4. **证据先于声明** — 没有运行验证就不能说完成
5. **隔离是默认** — Git Worktrees、Fresh Subagent per Task
6. **审查贯穿全程** — 每个 task 后审查 + 最终全局审查
7. **Skill 本身也用 TDD 开发** — Writing Skills = TDD for documentation
8. **心理学驱动** — 7 个说服原则，N=28,000 实验验证
9. **文件传递避免 context 污染** — task-brief / review-package
10. **进度 Ledger 抗压缩** — 信任 ledger 和 git log，不信任记忆
11. **一套 Skills 所有平台** — 动作描述 + platform reference 映射
12. **Eval 验证行为** — Drill 驱动真实 LLM session，不是单元测试

**最核心的洞察：** Skills are not prose — they are code that shapes agent behavior. 每个措辞、每个标签、每个表格都是经过对抗性压力测试调试出来的行为塑造工具。


## 一、hooks/run-hook.cmd：跨平台 Polyglot 脚本

### 1.1 问题背景

Windows 和 Unix 的命令执行方式完全不同：
- Unix：直接执行 bash 脚本
- Windows：需要 cmd.exe，但需要找到 bash（Git Bash、MSYS2、Cygwin）

Superpowers 的 hook 脚本使用无扩展名文件名（如 `session-start`），因为 Claude Code 在 Windows 上会自动对 `.sh` 文件加 `bash` 前缀。

### 1.2 Polyglot 设计（一个文件，两个平台）

```bash
: << 'CMDBLOCK'
@echo off
REM Cross-platform polyglot wrapper for hook scripts.
REM On Windows: cmd.exe runs the batch portion
REM On Unix: the shell interprets this as a script (: is a no-op in bash)

if "%~1"=="" (
    echo run-hook.cmd: missing script name >&2
    exit /b 1
)

set "HOOK_DIR=%~dp0"

REM Try Git for Windows bash in standard locations
if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM Try bash on PATH
where bash >nul 2>nul
if %ERRORLEVEL% equ 0 (
    bash "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM No bash found - exit silently rather than error
exit /b 0
CMDBLOCK

# Unix: run the named script directly
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="$1"
shift
exec bash "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"
```

### 1.3 精妙之处

1. **`: << 'CMDBLOCK'`** — 在 bash 中，`:` 是 no-op，后面跟 heredoc 会被忽略。在 cmd.exe 中，`:` 是 label，`<<` 被忽略。

2. **`CMDBLOCK`** — 在 cmd.exe 中，这标志着批处理脚本的开始。在 bash 中，这是 heredoc 的结束标记。

3. **静默回退** — 如果没有找到 bash，脚本静默退出（`exit /b 0`）而非报错。设计理由：插件仍然可以工作，只是没有 SessionStart 上下文注入。

4. **路径优先级**：先检查 Git for Windows 的标准安装位置，再检查 PATH 上的 bash。

### 1.4 执行流程

```
hooks/hooks.json 触发 → run-hook.cmd session-start
    ↓
Windows:
  1. 查找 C:\Program Files\Git\bin\bash.exe
  2. 查找 C:\Program Files (x86)\Git\bin\bash.exe
  3. where bash
  4. 没找到 → 静默退出

Unix:
  exec bash "${SCRIPT_DIR}/session-start" "$@"
    ↓
  session-start 读取 SKILL.md → 转义 → 输出 JSON
```

---

## 二、brainstorming/server.cjs：完整的 WebSocket 服务器（723 行）

### 2.1 架构总览

```
┌─────────────────────────────────────────────────────┐
│                   server.cjs (723 行)                │
├─────────────────────────────────────────────────────┤
│  WebSocket Protocol (RFC 6455) — 手动实现            │
│  - 帧编码/解码 (encodeFrame, decodeFrame)            │
│  - 掩码处理 (mask/unmask)                            │
│  - 控制帧 (PING/PONG/CLOSE)                          │
├─────────────────────────────────────────────────────┤
│  认证系统                                            │
│  - 64 位随机密钥 (crypto.randomBytes(32))            │
│  - 时序安全比较 (timingSafeEqualStr)                 │
│  - URL ?key= + Cookie 双认证                         │
├─────────────────────────────────────────────────────┤
│  HTTP 服务器                                         │
│  - 安全头: no-referrer, no-store, DENY framing       │
│  - 文件服务器沙箱: 拒绝 symlink, dotfile, 路径穿越    │
│  - 内容/状态目录分离                                  │
├─────────────────────────────────────────────────────┤
│  生命周期管理                                        │
│  - 空闲超时: 4 小时 (可配置)                         │
│  - 进程死亡检测 (ownerPid kill(0))                   │
│  - 端口冲突回退 (EADDRINUSE → 随机端口)              │
├─────────────────────────────────────────────────────┤
│  品牌和遥测                                          │
│  - Superpowers 版本显示                              │
│  - DISABLE_TELEMETRY 环境变量                        │
└─────────────────────────────────────────────────────┘
```

### 2.2 WebSocket 协议手动实现

**为什么手动实现？** 零外部依赖是 Superpowers 的核心设计原则。

```javascript
// WebSocket 帧编码
function encodeFrame(opcode, payload) {
  const fin = 0x80;
  const len = payload.length;
  let header;

  if (len < 126) {
    header = Buffer.alloc(2);
    header[0] = fin | opcode;
    header[1] = len;
  } else if (len < 65536) {
    header = Buffer.alloc(4);
    header[0] = fin | opcode;
    header[1] = 126;  // 16 位扩展长度
    header.writeUInt16BE(len, 2);
  } else {
    header = Buffer.alloc(10);
    header[0] = fin | opcode;
    header[1] = 127;  // 64 位扩展长度
    header.writeBigUInt64BE(BigInt(len), 2);
  }
  return Buffer.concat([header, payload]);
}

// WebSocket 帧解码（处理客户端掩码）
function decodeFrame(buffer) {
  // ... 解析帧头
  // 客户端帧必须有掩码
  const mask = buffer.slice(maskOffset, dataOffset);
  const data = Buffer.alloc(payloadLen);
  for (let i = 0; i < payloadLen; i++) {
    data[i] = buffer[dataOffset + i] ^ mask[i % 4];
  }
  return { opcode, payload: data, bytesConsumed: totalLen };
}
```

### 2.3 安全模型完整解析

#### 2.3.1 密钥生成和持久化

```javascript
function generateToken() {
  return crypto.randomBytes(32).toString('hex');  // 64 字符十六进制
}

function initialToken() {
  // 优先级: 环境变量 > 持久化文件 > 随机生成
  if (process.env.BRAINSTORM_TOKEN) return { value: process.env.BRAINSTORM_TOKEN, source: 'env' };
  if (TOKEN_FILE) {
    try {
      const t = fs.readFileSync(TOKEN_FILE, 'utf-8').trim();
      if (/^[0-9a-f]{32,}$/i.test(t)) {
        chmodOwnerOnly(TOKEN_FILE);  // 0o600
        return { value: t, source: 'file' };
      }
    } catch (e) { /* no prior token */ }
  }
  return { value: generateToken(), source: 'generated' };
}
```

**为什么持久化？** 服务器重启后，已打开的浏览器 tab 的 cookie 仍然有效，不需要重新打开。

#### 2.3.2 认证检查（HTTP + WebSocket 统一）

```javascript
function isAuthorized(req) {
  // 方式 1: URL 参数 ?key=...
  const q = req.url.indexOf('?');
  if (q >= 0) {
    const params = new URLSearchParams(req.url.slice(q + 1));
    if (params.has('key')) {
      const key = params.get('key');
      return Boolean(key && timingSafeEqualStr(key, TOKEN));
    }
  }
  // 方式 2: Cookie
  const cookie = parseCookies(req.headers['cookie'])[COOKIE_NAME];
  if (cookie && timingSafeEqualStr(cookie, TOKEN)) return true;
  return false;
}
```

**时序安全比较：** 使用 `crypto.timingSafeEqual()` 防止时序攻击。即使密钥长度不同，也不会提前返回。

#### 2.3.3 文件服务器沙箱

```javascript
function isRegularFileInsideContentDir(filePath) {
  let stat, realContentDir, realFilePath;
  try {
    stat = fs.lstatSync(filePath);
    if (stat.isSymbolicLink()) return false;  // 拒绝 symlink
    if (!stat.isFile()) return false;          // 拒绝目录
    if (stat.nlink !== 1) return false;        // 拒绝硬链接
    realContentDir = fs.realpathSync(CONTENT_DIR);
    realFilePath = fs.realpathSync(filePath);
  } catch (e) { return false; }
  return realFilePath.startsWith(realContentDir + path.sep);  // 防止路径穿越
}
```

**四层防护：**
1. 拒绝 symlink（`lstatSync` + `isSymbolicLink`）
2. 拒绝非普通文件（`isFile`）
3. 拒绝硬链接（`nlink !== 1`）
4. realpath 比较（防止 `../` 路径穿越）

#### 2.3.4 安全头

```javascript
function securityHeaders(headers = {}) {
  return {
    'Referrer-Policy': 'no-referrer',          // 不发送 Referer
    'Cache-Control': 'no-store',               // 不缓存
    'X-Frame-Options': 'DENY',                 // 禁止 iframe
    'Content-Security-Policy': "frame-ancestors 'none'",  // 禁止嵌入
    'Cross-Origin-Resource-Policy': 'same-origin',         // 同源策略
    ...headers
  };
}
```

### 2.4 生命周期管理

#### 2.4.1 空闲超时

```javascript
const IDLE_TIMEOUT_MS = (() => {
  const ms = Number(process.env.BRAINSTORM_IDLE_TIMEOUT_MS);
  return Number.isFinite(ms) && ms > 0 ? ms : 4 * 60 * 60 * 1000;  // 默认 4 小时
})();
```

**为什么 4 小时？** 从 30 分钟提升到 4 小时——头脑风暴可能持续较长时间，不需要频繁重启。

#### 2.4.2 进程死亡检测

```javascript
function ownerAlive() {
  if (!ownerPid) return true;
  try { process.kill(ownerPid, 0); return true; }
  catch (e) { return e.code === 'EPERM'; }  // 权限不足 = 进程仍在
}

const lifecycleCheck = setInterval(() => {
  if (!ownerAlive()) shutdown('owner process exited');
  else if (Date.now() - lastActivity > IDLE_TIMEOUT_MS) shutdown('idle timeout');
}, LIFECYCLE_CHECK_MS);
lifecycleCheck.unref();  // 不阻止进程退出
```

**为什么 `unref()`？** 定时器不应该阻止进程退出。如果主进程要退出，不应该被这个定时器阻止。

#### 2.4.3 WSL 进程死亡检测回退

```javascript
if (ownerPid) {
  try { process.kill(ownerPid, 0); }
  catch (e) {
    if (e.code !== 'EPERM') {
      console.log(JSON.stringify({ type: 'owner-pid-invalid', pid: ownerPid, reason: 'dead at startup' }));
      ownerPid = null;  // 禁用监控，依赖空闲超时
    }
  }
}
```

**关键洞察：** 在 WSL、Tailscale SSH、跨用户场景中，PID 解析经常出错。如果启动时 PID 已经无效，禁用监控，依赖空闲超时作为后备。

### 2.5 浏览器启动

```javascript
function browserLauncherForPlatform(url, { platform, osRelease, env } = {}) {
  const isWSL = platform === 'linux' && /microsoft/i.test(osRelease);
  if (platform === 'darwin') return { bin: 'open', args: [url] };
  if (platform === 'win32' || isWSL) {
    return { bin: 'rundll32.exe', args: ['url.dll,FileProtocolHandler', url] };
  }
  if (env.DISPLAY || env.WAYLAND_DISPLAY) return { bin: 'xdg-open', args: [url] };
  return null;
}
```

**安全设计：** 使用 `execFile`（无 shell）而非 `exec`，防止 URL 中的 shell 元字符注入。

### 2.6 端口回退

```javascript
server.on('error', (err) => {
  if (err.code === 'EADDRINUSE' && !triedFallback) {
    if (tokenSource === 'env') {
      // 如果显式设置了 token，拒绝回退（防止密钥泄露到其他端口）
      console.error('Refusing fallback with explicit token');
      process.exit(1);
    }
    triedFallback = true;
    PORT = randomPort();
    if (tokenSource === 'file') {
      TOKEN = generateToken();  // 重新生成 token
      tokenSource = 'generated-fallback';
    }
    server.listen(PORT, HOST, onListen);
  }
});
```

### 2.7 文件监听和广播

```javascript
const watcher = fs.watch(CONTENT_DIR, (eventType, filename) => {
  if (!filename || filename.startsWith('.') || !filename.endsWith('.html')) return;

  // 去重（macOS fs.watch 对新建和覆盖都报 'rename'）
  if (debounceTimers.has(filename)) clearTimeout(debounceTimers.get(filename));
  debounceTimers.set(filename, setTimeout(() => {
    const filePath = path.join(CONTENT_DIR, filename);
    if (!fs.existsSync(filePath)) return;

    touchActivity();
    if (!knownFiles.has(filename)) {
      knownFiles.add(filename);
      // 新 screen：清空 events 文件
      if (fs.existsSync(eventsFile)) fs.unlinkSync(eventsFile);
      maybeOpenBrowser();  // 自动打开浏览器
    }
    broadcast({ type: 'reload' });  // 通知所有 WebSocket 客户端重新加载
  }, 100));
});
```

---

## 三、CREATION_LOG.md：技能创建实录

### 3.1 为什么这个文档很重要

CREATION_LOG.md 展示了 Superpowers 如何**从实际使用经验中提取并 bulletproof 一个 skill**。它不是理论文档，而是实际操作记录。

### 3.2 提取决策

**要包含的：**
- 完整的 4 阶段框架和所有规则
- 反捷径语言（"NEVER fix symptom", "STOP and re-analyze"）
- 抗压语言（"even if faster", "even if I seem in a hurry"）
- 每个阶段的具体步骤

**要排除的：**
- 项目特定上下文
- 同一规则的重复变体
- 叙述性解释（压缩为原则）

### 3.3 Bulletproofing 元素

#### 3.3.1 语言选择

| 选择 | 效果 |
|------|------|
| "ALWAYS" / "NEVER"（不是 "should" / "try to"） | 消除决策疲劳 |
| "even if faster" / "even if I seem in a hurry" | 预先封堵时间压力借口 |
| "STOP and re-analyze"（显式暂停） | 强制中断自动行为 |
| "Don't skip past"（捕获实际行为） | 针对 Agent 真正会做的事 |

#### 3.3.2 结构防御

- **Phase 1 必须完成** — 不能跳到实现
- **单一假设规则** — 强制思考，防止散弹修复
- **显式失败模式** — "IF your first fix doesn't work" 带强制动作
- **反模式部分** — 展示捷径的确切样子

#### 3.3.3 冗余

- 根因要求在概述 + when_to_use + Phase 1 + 实现规则中出现 4 次
- "NEVER fix symptom" 在不同上下文中出现 4 次
- 每个阶段都有显式的 "don't skip" 指导

### 3.4 测试方法

**4 个验证测试：**

| 测试 | 场景 | 结果 |
|------|------|------|
| 学术场景（无压力） | 简单 bug，无时间压力 | ✅ 完美合规 |
| 时间压力 + 明显快速修复 | 用户"赶时间"，症状修复看起来简单 | ✅ 抵抗捷径 |
| 复杂系统 + 不确定性 | 多层失败，不确定能否找到根因 | ✅ 系统调查 |
| 首次修复失败 | 假设不工作， temptation 加更多修复 | ✅ 停止、重新分析 |

### 3.5 关键洞察

> **最重要的 bulletproofing：** 反模式部分展示在当下感觉合理的捷径。当 Agent 想"我就加一个快速修复"时，看到这个确切模式被列为错误会产生认知摩擦。

---

## 四、压力测试场景完整解析

### 4.1 压力测试 1：紧急生产修复

**场景：** 生产 API 宕机，每分钟损失 $15,000，经理说"立即修复"。

**压力组合：**
- ⏰ 时间压力：每分钟 $15k 损失
- 👤 权威压力：经理说 "FIX IT NOW"
- 💰 经济压力：$525k vs $75k 的权衡
- 🧠 认知捷径：2 分钟 vs 35 分钟的对比

**设计精妙之处：**
- 提供了具体的成本计算（$525k vs $75k），让快速修复看起来非常合理
- 承认系统调试需要 35+ 分钟——这是诚实的
- 选项 C 提供了"折中"方案——这是最危险的 rationalization

### 4.2 压力测试 2：沉没成本 + 疲惫

**场景：** 调试了 4 小时，现在是晚上 8 点，8:30 要吃饭，明天 9 点代码审查。

**压力组合：**
- 💸 沉没成本：4 小时工作可能被"浪费"
- 😴 疲惫：想要结束
- ⏰ 时间压力：30 分钟后要吃饭
- 🔄 迭代失败：尝试了 6 种不同的 sleep timeout

**设计精妙之处：**
- "所有 4 小时的工作都被删除"——这是最强的沉没成本触发
- "Being 'pragmatic' about perfect vs good enough"——这是最常见的 rationalization
- 选项 C 提供"平衡"方案——这是最危险的借口

### 4.3 为什么这些测试有效

1. **具体而非抽象** — 不是"假设你很忙"，而是具体的 $15k/分钟、8pm 晚餐
2. **强迫选择** — A/B/C 三选一，不是开放性问题
3. **承认合理性** — 每个选项都有合理的理由，让测试更真实
4. **要求诚实** — "Be completely honest about what you would actually do"

---

## 五、Persuasion Principles：Skill 设计的心理学

### 5.1 研究基础

**Meincke et al. (2025)** — N=28,000 次 AI 对话实验，测试 7 个说服原则：
- 说服技术使合规率从 **33% → 72%**（p < .001）
- 权威、承诺、稀缺最有效
- 验证了 LLM 的"类人"行为模型

### 5.2 七个原则在 Skill 中的应用

#### 5.2.1 权威（Authority）

```markdown
✅ Write code before test? Delete it. Start over. No exceptions.
❌ Consider writing tests first when feasible.
```

**为什么有效：** "YOU MUST", "Never", "Always" 消除决策疲劳。绝对语言排除了"这是例外吗？"的问题。

#### 5.2.2 承诺（Commitment）

```markdown
✅ When you find a skill, you MUST announce: "I'm using [Skill Name]"
❌ Consider letting your partner know which skill you're using.
```

**为什么有效：** 要求宣布 = 强制选择 = 追踪。当 Agent 说了"我在使用 brainstorming"，它更可能遵循该 skill。

#### 5.2.3 稀缺（Scarcity）

```markdown
✅ After completing a task, IMMEDIATELY request code review before proceeding.
❌ You can review code when convenient.
```

**为什么有效：** 时间绑定要求防止"我晚点再做"。顺序依赖强制立即执行。

#### 5.2.4 社会证明（Social Proof）

```markdown
✅ Checklists without todo tracking = steps get skipped. Every time.
❌ Some people find a todo list helpful for checklists.
```

**为什么有效：** "Every time" 建立规范。失败模式（"X without Y = failure"）强化标准。

#### 5.2.5 团结（Unity）

```markdown
✅ We're colleagues working together. I need your honest technical judgment.
❌ You should probably tell me if I'm wrong.
```

**为什么有效：** "your human partner" 语言建立协作关系，不是主仆关系。

#### 5.2.6 互惠（Reciprocity）

**不推荐使用** — 容易感觉被操纵，其他原则更有效。

#### 5.2.7 喜好（Liking）

**永远不要用于合规执行** — 与诚实反馈文化冲突，产生阿谀奉承。

### 5.3 原则组合

| Skill 类型 | 使用 | 避免 |
|-----------|------|------|
| 纪律执行 | 权威 + 承诺 + 社会证明 | 喜好、互惠 |
| 指导/技术 | 适度权威 + 团结 | 强权威 |
| 协作 | 团结 + 承诺 | 权威、喜好 |
| 参考 | 仅清晰度 | 所有说服技术 |

### 5.4 为什么这对 LLM 有效

**LLMs are parahuman：**
- 在人类文本上训练，包含这些模式
- 权威语言在训练数据中先于合规行为
- 承诺序列（声明 → 行动）被频繁建模
- 社会证明模式（每个人都做 X）建立规范

**Bright-line rules 减少 rationalization：**
- "YOU MUST" 消除决策疲劳
- 绝对语言排除了"这是例外吗？"的问题
- 显式反 rationalization 计数器关闭特定漏洞

**Implementation intentions 创建自动行为：**
- 清晰触发器 + 必需动作 = 自动执行
- "When X, do Y" 比 "generally do Y" 更有效
- 减少合规的认知负荷

### 5.5 道德使用

**合法的：**
- 确保关键实践被遵循
- 创建有效文档
- 防止可预测的失败

**不合法的：**
- 为个人利益操纵
- 制造虚假紧迫感
- 基于内疚的合规

**测试：** 如果用户完全理解这个技术，它是否服务于用户的真正利益？

---

## 六、Porting to a New Harness：工程哲学文档

### 6.1 三个组件

Superpowers 在所有平台上是相同的内容。每个平台的变化只是薄薄的一层：

1. **Skills（平台无关）** — `skills/` 中的一切是所有平台的真相源
2. **Tool mapping（每个平台）** — `using-superpowers/references/<harness>-tools.md`
3. **Bootstrap（每个平台）** — 每个会话开始时注入 `using-superpowers/SKILL.md`

### 6.2 两个不变规则

**规则 1：Skills 命名动作，不是工具。**
> 不要编辑 skill body 来适配你的 harness。Porting 添加 tool-mapping reference 和 bootstrap injector；绝不进入 `skills/*/SKILL.md` 交换工具名。

**规则 2：一切通过 harness 的安装机制交付。绝不编辑用户文件。**
> Bootstrap、skills 和 tool mapping 都作为 harness 安装的一部分交付。Port **绝不能** 触及用户的全局或个人配置。

### 6.3 硬性要求：自动会话启动注入

> harness 必须能在**每个会话开始时**，**不需要用户每次选择加入**，注入文本到模型上下文中。这是**唯一不可协商的能力**。

### 6.4 为什么这个文档重要

这份 826 行的文档展示了 Superpowers 的工程哲学：
- **教不变量**（无论机制如何都必须为真的事情）
- **指向活的参考实现**（复制最接近的）
- **当文档和代码冲突时，代码赢**；修复文档

---

## 七、build/release 工具链

### 7.1 .pre-commit-config.yaml

```yaml
repos:
  - repo: local
    hooks:
      - id: shell-lint
        name: Shell lint
        entry: scripts/lint-shell.sh
        language: system
        files: \.(sh|cmd)$
```

**关键设计：** 只对 `.sh` 和 `.cmd` 文件运行 lint。

### 7.2 scripts/lint-shell.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

find hooks skills scripts -name '*.sh' -o -name '*.cmd' | while read -r f; do
  bash -n "$f" || { echo "Syntax error in $f"; exit 1; }
done

echo "All shell scripts pass syntax check"
```

**设计理由：** 只检查语法，不做风格检查。风格在 PR review 中处理。

### 7.3 scripts/bump-version.sh

使用 `.version-bump.json` 配置：
```json
{
  "current_version": "6.0.3",
  "files_to_update": [
    "package.json",
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
    ".kimi-plugin/plugin.json",
    ".opencode/plugins/superpowers.js"
  ]
}
```

**关键设计：** 版本号在一个地方定义，同步到所有插件 manifest。

### 7.4 scripts/sync-to-codex-plugin.sh

```bash
#!/usr/bin/env bash
# Sync Superpowers content to the packaged Codex plugin directory
# Excludes .gitmodules and .pre-commit-config.yaml to keep repo metadata out
rsync -av --exclude='.gitmodules' --exclude='.pre-commit-config.yaml' \
  ./ .codex-plugin/
```

**设计理由：** Codex 插件是打包分发的，不应包含仓库元数据。

---

## 八、docs/superpowers/specs/ 档案解析

### 8.1 完整的设计文档档案

Superpowers 的 `docs/superpowers/specs/` 目录包含 15 份设计文档，从 2026-01-22 到 2026-06-11：

| 日期 | 设计文档 | 核心主题 |
|------|---------|---------|
| 2026-01-22 | document-review-system-design.md | 文档审查系统 |
| 2026-02-19 | visual-brainstorming-refactor-design.md | 可视化头脑风暴重构 |
| 2026-03-11 | zero-dep-brainstorm-server-design.md | 零依赖头脑风暴服务器 |
| 2026-03-23 | codex-app-compatibility-design.md | Codex App 兼容 |
| 2026-04-06 | worktree-rototill-design.md | Worktree 重构 |
| 2026-05-05 | platform-neutral-config-refs-design.md | 平台无关配置引用 |
| 2026-05-05 | platform-neutral-prose-design.md | 平台无关散文 |
| 2026-05-05 | platform-neutral-readme-design.md | 平台无关 README |
| 2026-05-06 | lift-drill-into-evals-design.md | 将 Drill 提升到 evals |
| 2026-06-09 | sdd-task-scoped-review-dispatch-design.md | SDD 任务级审查分派 |
| 2026-06-10 | positive-instruction-redesign-design.md | 正向指令重新设计 |
| 2026-06-10 | strict-cost-sdd-design.md | 严格成本 SDD |
| 2026-06-10 | visual-companion-auth-hardening-design.md | 视觉伴侣认证加固 |
| 2026-06-11 | visual-companion-final-hardening-fixup-design.md | 视觉伴侣最终加固 |

### 8.2 Strict-Cost SDD 设计文档的深度解析

这是最揭示真实成本的文件：

**当前配置（opus + sonnet, ~$13/run）：**
- Controller（opus）：~$6-7，~150 turns × 常驻上下文
- Implementers（sonnet, 10-13 dispatches）：~$5-6
- Task reviewers（sonnet, 10）：~$1-1.5
- 最终审查 + 修复：~$1

**关键发现：** 审查循环次数（2-4 次/run）是最大的 run-to-run 成本方差。循环主要由计划歧义引起。

**判断力守卫线：**
> **Cheapen mechanics, never judgment.**

必须留在最贵模型的决定：
- BLOCKED / NEEDS_CONTEXT 处理
- ⚠️ "无法从 diff 验证" 的裁决
- 分派策划
- 审查判定和严重性校准
- 审查循环裁决
- 识别需要升级给人类

**SDD 的 Thesis：**
> 每个 task 一个全新子 Agent + 精确策划的上下文 + 每个 task 的门控

反 thesis：dispatch-time task batching——污染 fresh-context 属性。

---

## 九、与前一文档的补充关系

本文档是对 `superpowers-complete-analysis.md` 的补充，专注于：

| 本文档覆盖 | 前一文档未覆盖或浅覆盖 |
|-----------|----------------------|
| run-hook.cmd polyglot 设计 | 只提到了 hooks/session-start |
| server.cjs 完整 723 行安全模型 | 只读取了前 100 行 |
| CREATION_LOG.md 创建实录 | 未覆盖 |
| 压力测试场景详细分析 | 只提到了存在压力测试 |
| Persuasion Principles 完整 7 原则 | 只提到了 7 原则名称 |
| Porting 文档工程哲学 | 未覆盖 |
| Build/release 工具链 | 未覆盖 |
| Design Specs 档案解析 | 只列出了文件名 |

---

## 十、源码级核心发现总结

### 10.1 零依赖的工程代价

Superpowers 选择零外部依赖，代价是：
- 手动实现 WebSocket 协议（723 行中的 ~80 行）
- 手动解析 Cookie（`parseCookies` 函数）
- 手动转义 JSON 字符串（bash 中的 5 层参数替换）
- 手动处理跨平台兼容性（run-hook.cmd polyglot）

**回报：** 安装不需要 `npm install`，没有依赖链，没有 supply chain attack 风险。

### 10.2 安全模型的深度

Brainstorming 服务器的安全模型覆盖了：
1. **认证**：64 位随机密钥 + 时序安全比较
2. **授权**：URL ?key= + Cookie 双认证
3. **文件隔离**：symlink 拒绝 + dotfile 拒绝 + 硬链接拒绝 + 路径穿越防护
4. **HTTP 安全头**：5 个安全头
5. **WebSocket Origin 检查**：防止跨源连接
6. **Cookie 安全**：HttpOnly + SameSite=Strict
7. **文件权限**：0o600（仅 owner 可读写）

这是一个本地开发工具，但安全模型达到了生产级标准。

### 10.3 Bulletproofing 的系统性

从 CREATION_LOG.md 可以看到，每个 skill 的 bulletproofing 是系统性的：

1. **从实际经验中提取**（不是凭空想象）
2. **记录 rationalization verbatim**（精确记录 Agent 的借口）
3. **显式关闭每个漏洞**（不只是说规则，要禁止具体绕过方式）
4. **在多种压力下测试**（时间 + 沉没成本 + 权威 + 疲惫）
5. **冗余**（同一个规则在不同地方出现多次）

### 10.4 心理学驱动的设计

Persuasion Principles 文档揭示了 Superpowers 不仅是一套技术规则，而是**基于 N=28,000 实验的心理学应用**。

合规率从 33% 提升到 72%——这不是偶然的，是精心设计的。



---

# Superpowers 源码级深度解析第三篇：Anthropic 最佳实践对比、测试反模式与设计迭代

> 基于 obra/superpowers v6.0.3 仓库逐文件深度阅读
> 新增覆盖：Anthropic 官方最佳实践对比、测试反模式、防御深度、条件等待、正向指令设计、SDD 审查优化迭代

---

## 一、Anthropic 官方最佳实践 vs Superpowers 实践

### 1.1 背景

Superpowers 仓库中包含 Anthropic 官方 skill authoring best practices（1150 行），这是一个非常重要的对比材料——它展示了 Superpowers 如何**偏离**官方指导来追求更激进的行为塑造。

### 1.2 官方核心原则

**Concise is key：**
> The context window is a public good. Your Skill shares the context window with everything else.

**Set appropriate degrees of freedom：**
- **High freedom**：当多种方法有效时，用文本指导
- **Medium freedom**：当有首选模式时，用伪代码/脚本
- **Low freedom**：当操作脆弱时，用精确命令

**Default assumption: Agents are already very smart**
> Only add context agents don't already have. Challenge each piece of information.

### 1.3 关键差异：Superpowers 偏离官方指南的地方

| 维度 | Anthropic 官方指南 | Superpowers 实践 |
|------|-------------------|-----------------|
| **语气** | 温和建议（"consider", "should"） | 绝对命令（"YOU MUST", "NEVER", "ALWAYS"） |
| **长度** | SKILL.md < 500 行 | brainstorming 159 行，SDD 418 行，writing-skills 689 行 |
| **Rationalization** | 不讨论 | 每个纪律 skill 都有完整表格 |
| **Red Flags** | 不讨论 | 几乎所有 skill 都有 |
| **测试** | "Test with all models" | RED-GREEN-REFACTOR 压力测试 |
| **Flowchart** | 不推荐 | 每个复杂流程都有 dot 图 |
| **Good/Bad** | 提供模板 | 对比 + 反模式 + 禁止回应 |
| **哲学** | Skill 是参考文档 | Skill 是行为塑造代码 |
| **冗余** | 避免重复 | 同一个规则出现 4 次 |
| **"Violating letter vs spirit"** | 不讨论 | 显式封堵 |

### 1.4 为什么 Superpowers 偏离

从 `writing-skills/testing-skills-with-subagents.md` 可以看出：

1. **Anthropic 指南是为一般 skill 写的**（PDF 处理、Excel 分析等）
2. **Superpowers skill 是纪律执行型**（TDD、调试、验证）
3. **纪律执行需要抗压**，而 Anthropic 指南没有考虑压力场景
4. **实测结果**：Superpowers 的强硬方法在压力下合规率更高

### 1.5 官方指南中的 Progressive Disclosure

官方推荐的 skill 组织模式：

```
pdf/
├── SKILL.md              # 主指令（触发时加载）
├── FORMS.md              # 表单填充指南（按需加载）
├── reference.md          # API 参考（按需加载）
├── examples.md           # 使用示例（按需加载）
└── scripts/
    ├── analyze_form.py   # 工具脚本（执行，不加载）
```

**Superpowers 的做法：** 同样的模式，但 reference 文件也经过对抗性测试。

### 1.6 官方指南的"Degrees of Freedom"类比

> Think of the agent as a robot exploring a path:
> - **Narrow bridge with cliffs**: Provide specific guardrails (low freedom)
> - **Open field with no hazards**: Give general direction (high freedom)

**Superpowers 的实践：** 几乎所有 skill 都是"窄桥"——有悬崖，需要护栏。

---

## 二、Testing Anti-Patterns：测试反模式（299 行完整解析）

### 2.1 核心原则

> Tests must verify real behavior, not mock behavior. Mocks are a means to isolate, not the thing being tested.

### 2.2 三大铁律

```
1. NEVER test mock behavior
2. NEVER add test-only methods to production classes
3. NEVER mock without understanding dependencies
```

### 2.3 五个反模式

#### 反模式 1：测试 Mock 行为

```typescript
// ❌ BAD: Testing that the mock exists
test('renders sidebar', () => {
  render(<Page />);
  expect(screen.getByTestId('sidebar-mock')).toBeInTheDocument();
});
```

**Gate Function：**
```
BEFORE asserting on any mock element:
  Ask: "Am I testing real component behavior or just mock existence?"
  IF testing mock existence:
    STOP - Delete the assertion or unmock the component
```

#### 反模式 2：生产类中的测试专用方法

```typescript
// ❌ BAD: destroy() only used in tests
class Session {
  async destroy() {  // Looks like production API!
    await this._workspaceManager?.destroyWorkspace(this.id);
  }
}
```

**修复：** 移到 test utilities，保持生产类纯净。

#### 反模式 3：不理解依赖就 Mock

```typescript
// ❌ BAD: Mock breaks test logic
vi.mock('ToolCatalog', () => ({
  discoverAndCacheTools: vi.fn().mockResolvedValue(undefined)
}));
// 这个 mock 阻止了测试依赖的 config 写入！
```

**Gate Function：**
```
BEFORE mocking any method:
  1. Ask: "What side effects does the real method have?"
  2. Ask: "Does this test depend on any of those side effects?"
  IF depends on side effects: Mock at lower level
  IF unsure: Run test with real implementation FIRST
```

#### 反模式 4：不完整的 Mock

```typescript
// ❌ BAD: Partial mock - only fields you think you need
const mockResponse = {
  status: 'success',
  data: { userId: '123', name: 'Alice' }
  // Missing: metadata that downstream code uses
};
```

**铁律：** Mock the COMPLETE data structure as it exists in reality.

#### 反模式 5：集成测试作为事后考虑

```
✅ Implementation complete
❌ No tests written
"Ready for testing"
```

### 2.4 TDD 如何防止这些反模式

1. **先写测试** → 迫使你思考真正要测试什么
2. **看它失败** → 确认测试测试真实行为，不是 mock
3. **最小实现** → 不会渗入测试专用方法
4. **真实依赖** → 在 mock 之前看到测试真正需要什么

---

## 三、Defense-in-Depth：多层防御（122 行完整解析）

### 3.1 核心原则

> Validate at EVERY layer data passes through. Make the bug structurally impossible.

**对比：**
- Single validation: "We fixed the bug"
- Multiple layers: "We made the bug impossible"

### 3.2 四层防御

| 层 | 目的 | 示例 |
|----|------|------|
| **Layer 1: Entry Point** | 在 API 边界拒绝明显无效输入 | `createProject()` 验证目录非空/存在/可写 |
| **Layer 2: Business Logic** | 确保数据对操作有意义 | `initializeWorkspace()` 验证 projectDir 非空 |
| **Layer 3: Environment Guards** | 防止特定上下文中的危险操作 | 测试中拒绝在非 tmpdir 执行 git init |
| **Layer 4: Debug Instrumentation** | 捕获上下文用于取证 | git init 前记录 stack trace |

### 3.3 真实案例

**Bug：** 空 `projectDir` 导致 `git init` 在源代码目录执行

**数据流：**
1. Test setup → 空字符串
2. `Project.create(name, '')`
3. `WorkspaceManager.createWorkspace('')`
4. `git init` 运行在 `process.cwd()`

**四层防御结果：** 1847 个测试全部通过，bug 无法复现

### 3.4 关键洞察

> All four layers were necessary. During testing, each layer caught bugs the others missed:
> - Different code paths bypassed entry validation
> - Mocks bypassed business logic checks
> - Edge cases on different platforms needed environment guards
> - Debug logging identified structural misuse

**不要在一个验证点停止。在每个层添加检查。**

---

## 四、Condition-Based Waiting：条件等待（115 行完整解析）

### 4.1 核心原则

> Wait for the actual condition you care about, not a guess about how long it takes.

### 4.2 核心模式

```typescript
// ❌ BEFORE: Guessing at timing
await new Promise(r => setTimeout(r, 50));
const result = getResult();
expect(result).toBeDefined();

// ✅ AFTER: Waiting for condition
await waitFor(() => getResult() !== undefined);
const result = getResult();
expect(result).toBeDefined();
```

### 4.3 waitFor 实现

```typescript
async function waitFor<T>(
  condition: () => T | undefined | null | false,
  description: string,
  timeoutMs = 5000
): Promise<T> {
  const startTime = Date.now();
  while (true) {
    const result = condition();
    if (result) return result;
    if (Date.now() - startTime > timeoutMs) {
      throw new Error(`Timeout waiting for ${description} after ${timeoutMs}ms`);
    }
    await new Promise(r => setTimeout(r, 10)); // Poll every 10ms
  }
}
```

### 4.4 真实影响

从调试会话（2025-10-03）：
- 修复了 3 个文件中的 15 个 flaky 测试
- 通过率：60% → 100%
- 执行时间：快 40%
- 不再有 race conditions

---

## 五、Positive-Instruction Redesign：正向指令设计（178 行完整解析）

### 5.1 背景

这是 Superpowers 最揭示其工程严谨性的设计文档之一——通过微测试（micro-tests）量化不同措辞对 Agent 行为的影响。

### 5.2 核心发现（2026-06-10 微测试）

| 案例 | 措辞 | 结果 |
|------|------|------|
| Dispatch 组合（"don't restate the brief"） | 禁令 | **4.4** 个 spec 值被重新输入 — **比无指导更差**（3.6） |
| Dispatch 组合 | 正向配方 | **3.0，零方差** — 采用 |
| Dispatch 组合 | 配方 + 细微条款 | 3.8，有噪音 — 细微条款稀释配方 |
| 测试重跑指令 | 禁令 | **0/5 违规** — 工作良好（对照：3/5） |
| 测试重跑指令 | 正向配方 | 0/5 — 相等，但更长 |

### 5.3 五条教义

1. **Tripwires 工作。** 对具体 token 的短语级自检（"如果 prompt 包含 'do not flag'... 停止"）可靠触发。
2. **Recognition tables 工作。** Red-Flags/rationalization 表在决策时读取，不是组合时。
3. **Discrete-directive 禁令工作。** "Do not ask X to do Y" 在模型没有竞争动机时有效。
4. **Composition 禁令适得其反** 当模型有自己的输出议程时。只有正向配方能移动这些——而给获胜配方加细微条款会让它更差。
5. **Ties go to the shorter phrasing.** Codex 每次长会话重读 SKILL.md ~500 次；散文长度是真实成本。

### 5.4 微测试设计

```
- Task: opus 从故意欠规范的 spec 写 2-3 个 task 的实施计划
- Sampling: 每个变体 5+ 次重复，默认 temperature
- Programmatic scoring:
  - banned-token count
  - 缺少代码块的步骤数
  - 引用了未定义类型/函数的步骤数
  - 带预期输出的可运行命令数
- Acceptance: 只在 banned-token 计数上击败 V0 且不丢失代码块覆盖率时才采用
- 预期成本：~$6-10 总计
```

### 5.5 结果

**writing-plans 微测试：** 0 placeholders in all 20 plans across all four variants including the no-guidance control。当前代 opus 不会在计划中产生占位符，即使有故意压力。

**结论：** 保持现状，不打开后续 PR。V2 重定位设计保留在案，以备未来模型退化。

### 5.6 为什么这个文档重要

它展示了 Superpowers 如何**用数据而不是直觉**来指导 skill 设计：
- 每条措辞变化都有测量数据
- 5+ 次重复以捕获方差
- 包括无指导对照组
- 成本透明（~$0.15-0.30/样本）
- 手动检查每个标记的匹配（自动化计分会误判）

---

## 六、SDD Task-Scoped Review Dispatch：审查优化迭代（160 行完整解析）

### 6.1 问题

Per-task code quality reviewer 在 SDD 中常规执行 branch-review-scale 的工作量。

**证据：**
- 7/8 个 quality reviewer 运行了 repo-wide greps
- 最昂贵的运行了 50+ Bash 命令，耗时 ~200 秒
- Quality reviewer 成本是 spec reviewer 的 4-8 倍

**根因：**
1. Per-task quality prompt 继承了 merge-readiness review 的框架
2. Controller 没有编写 reviewer prompt 的指导
3. 整个 pipeline 中重复工作
4. Per-task 和 final review 使用同一个模板

### 6.2 成本迭代

这是一个完整的优化历程，每一轮都有测量数据：

| 迭代 | 时间 | Tokens | 成本 | 变化 |
|------|------|--------|------|------|
| 基线 | 64.9 min | 21.2M | $16.07 | - |
| 硬化版 | 69.9 min | 32.2M | - | 质量强化导致成本上升 |
| Iteration 1 | 68.2 min | 22.9M | - | 模型指导（mid-tier floor）|
| Iteration 2 | 47.5 min | 15.7M | $13.55 | 合并 spec+quality reviewer |
| Iteration 3 | - | - | - | Calibration 命名 + 文件传递 |
| Final (e355795) | 44.4 min | 13.4M | $11.67 | **-32% 时间, -37% tokens, -27% 成本** |

### 6.3 关键发现

**Turn count beats token price：**
- 便宜模型在多步工作上需要 2-3 倍 turn
- 1197 个子 Agent turn 中有 678 个是 haiku
- Per-dispatch overhead（每个 task 3 个 spin-up）占成本一半

**Controller turn batching 无效：**
- Controller 每条消息恰好发一个工具调用（0 个 multi-tool）
- 46% 的 turn 是 thinking/narration（prompt-immune floor）

**Background pipelining 收益低于噪音：**
- 机制在 7/28 dispatches 中被采用
- 但在 45 分钟场景中 benefit 低于 ±6 分钟噪音地板

### 6.4 最终验证配置（b81f35b）

| 场景 | 时间 | Tokens | 成本 | 对比基线 |
|------|------|--------|------|---------|
| go-fractals | 54.1-54.7 min | 14.4-16.6M | $12.81-14.31 | -16-17% 时间 |
| svelte-todo | 55.0 min | 19.3M | $14.99 | -21-31% |
| planted-defect | - | - | $2.77 | 通过 |

**关键：** 最差的 draw 仍然在每个维度上击败基线。

---

## 七、run-hook.cmd 跨平台 Polyglot 深度解析

### 7.1 一个文件，两个世界

```bash
: << 'CMDBLOCK'     # bash: no-op + heredoc 开始（被忽略）
@echo off           # cmd: 关闭回显
REM Cross-platform polyglot wrapper
...批处理逻辑...      # cmd 执行到这里
CMDBLOCK            # bash: heredoc 结束标记

# Unix: run the named script directly
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="$1"
shift
exec bash "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"
```

### 7.2 为什么这样设计

1. **无扩展名文件名**：Claude Code Windows 自动对 `.sh` 加 `bash` 前缀
2. **静默回退**：找不到 bash 不报错（插件仍然工作，只是没有 SessionStart 注入）
3. **优先级**：Git for Windows → PATH 上的 bash

---

## 八、Porting to a New Harness 的工程哲学

### 8.1 两个不变规则

**规则 1：Skills 命名动作，不是工具。**
> 不要编辑 skill body 来适配你的 harness。Porting 添加 tool-mapping reference 和 bootstrap injector；绝不进入 `skills/*/SKILL.md` 交换工具名。

**规则 2：一切通过 harness 的安装机制交付。绝不编辑用户文件。**
> Bootstrap、skills 和 tool mapping 都作为 harness 安装的一部分交付。Port **绝不能** 触及用户的全局或个人配置。

### 8.2 硬性要求

> harness 必须能在**每个会话开始时**，**不需要用户每次选择加入**，注入文本到模型上下文中。这是**唯一不可协商的能力**。

### 8.3 为什么这个文档重要

这份 826 行的文档展示了 Superpowers 的工程哲学：
- **教不变量**（无论机制如何都必须为真的事情）
- **指向活的参考实现**（复制最接近的）
- **当文档和代码冲突时，代码赢**；修复文档

---

## 九、与前一文档的补充关系

本文档是对 `superpowers-complete-analysis.md` 的第三次补充，专注于：

| 本文档覆盖 | 前两篇未覆盖或浅覆盖 |
|-----------|---------------------|
| Anthropic 官方最佳实践对比 | 只提到了 Anthropic 文档存在 |
| 测试反模式完整 5 个模式 | 未覆盖 |
| 防御深度四层模型 | 只提到了 root-cause-tracing |
| 条件等待实现 | 未覆盖 |
| 正向指令设计微测试 | 未覆盖 |
| SDD 审查优化 6 轮迭代 | 只提到了 cost 数据 |
| run-hook.cmd polyglot 设计 | 只提到了 hooks/session-start |
| Porting 文档工程哲学 | 未覆盖 |

---

## 十、源码级核心发现总结

### 10.1 Superpowers vs Anthropic：两种范式

| 维度 | Anthropic | Superpowers |
|------|-----------|------------|
| **Skill 是什么** | 参考文档 | 行为塑造代码 |
| **目标** | 提供指导 | 强制合规 |
| **语气** | 建议 | 命令 |
| **测试** | "Test with models" | RED-GREEN-REFACTOR |
| **抗压** | 不考虑 | 核心设计 |
| **冗余** | 避免 | 故意（4 次重复） |
| **长度** | < 500 行 | 无上限 |
| **变更依据** | 直觉 | 微测试数据 |

### 10.2 微测试：Superpowers 的秘密武器

- ~$0.15-0.30/样本
- 秒级迭代 vs $12/50 分钟全量 eval
- 5+ 次重复捕获方差
- 总是包括无指导对照组
- 手动检查每个标记的匹配
- **效果：** 正向配方 3.0 vs 禁令 4.4 vs 无指导 3.6

### 10.3 成本优化的系统性

从基线 $16.07 到最终 $12.81-14.31：
- 合并 spec+quality reviewer（一次读取，两个判定）
- 文件传递（避免 prompt 污染）
- 模型选择指导（turn count beats token price）
- 进度 Ledger（防止上下文压缩后重跑）
- Omnibus final fixer（一个 fixer 处理所有发现）
- 正向指令设计（禁令适得其反时）

### 10.4 防御深度的工程启示

> "All four layers were necessary. During testing, each layer caught bugs the others missed."

这不是理论——是实测结果。每个层都捕获了其他层遗漏的 bug：
- 不同代码路径绕过了入口验证
- Mock 绕过了业务逻辑检查
- 不同平台的边缘情况需要环境防护
- 调试日志识别了结构性误用
