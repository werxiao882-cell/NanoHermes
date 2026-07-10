# 解决"Claude Code 自审不靠谱"——7 种方案细节全解

> 基于文章「不靠谱的 Claude Code」+ 评论区 18 条留言，逐一展开每种方案的**具体操作、配置、代码示例、优缺点**。

---

## 方案 1：开新对话让 Claude 自审

### 1.1 核心原理

清除上下文中的"我刚刚写了这段代码"的记忆，让 Claude 以"失忆"状态重新审查。虽然底层模型没变，但至少没有了"刚写完"的心理包袱。

### 1.2 具体操作

**Claude Code 中**：
```bash
# 写完代码后，退出当前对话
/exit

# 重新进入 Claude Code
claude

# 在新对话中贴入代码要求 review
请审查以下代码，重点关注边界条件、空值处理、异常场景：

[粘贴代码]
```

**NanoHermes 中**：
```bash
# 列出会话
python -m src.main --list-sessions

# 开新会话（直接启动就是新的）
python -m src.main

# 或者按标题恢复之前的会话继续工作
python -m src.main --resume-title "某个功能开发"
```

### 1.3 为什么效果有限

| 原因 | 说明 |
|------|------|
| 模型偏好不变 | 同一个 Claude，训练数据相同，推理模式相同，盲区重叠 |
| 代码是同一份 | 即使没有上下文记忆，代码本身的"写法风格"还是 Claude 自己的 |
| 缺乏外部视角 | 就像让同一个老师隔一周再批同一份卷子，标准不会变 |

### 1.4 实测数据（作者反馈）

> "试过了，效果一般般"——不如换模型

### 1.5 适用场景

- 快速小改，不值得引入第二个模型
- 临时应急，没时间配置
- 作为第一道轻量级检查

### 1.6 优缺点

| ✅ 优点 | ❌ 缺点 |
|---------|---------|
| 零成本，不需要任何配置 | 效果有限，盲区依旧存在 |
| 操作简单，30 秒搞定 | 对复杂 bug 几乎无效 |
| 不消耗额外 token（相对） | 无法发现模型系统性缺陷 |

---

## 方案 2：用 Review Skill 约束 Claude

### 2.1 核心原理

通过结构化的 SKILL.md 文件，强制 Claude 按照预定义的 checklist 逐项检查，而不是泛泛地说"没问题"。

### 2.2 SKILL.md 模板

```yaml
---
name: code-review
description: 严格的代码审查技能，强制逐项检查
trigger: 用户要求 review 代码时自动加载
---

# 代码审查清单

## 审查原则
1. **假设代码有 bug**：带着"找问题"的心态，而不是"验证没问题"
2. **不考虑上下文**：就当这是别人写的代码，你没有参与开发
3. **宁可误报不可漏报**：不确定的问题也要标记出来

## 必查项（每项必须回答）

### 空值处理
- [ ] 所有输入参数是否检查了 null/undefined/None？
- [ ] 数组/列表为空时是否会 crash？
- [ ] 字符串为空时是否有默认值？
- [ ] 字典/对象缺少 key 时是否处理？

### 边界条件
- [ ] 输入为 0、-1、最大值、最小值时是否正确？
- [ ] 循环的起始和结束条件是否正确？
- [ ] 递归是否有终止条件？

### 异常处理
- [ ] 网络请求失败时是否有 fallback？
- [ ] 文件读写失败时是否 catch 异常？
- [ ] 超时场景是否处理？

### 并发安全
- [ ] 共享变量是否有锁或原子操作？
- [ ] 异步操作是否有竞态条件？

### 资源泄漏
- [ ] 文件句柄、数据库连接、网络连接是否关闭？
- [ ] 定时器、订阅者、监听器是否正确销毁？

## 输出格式
对每个检查项，必须给出：
1. **状态**：✅ 通过 / ⚠️ 可疑 / ❌ 确认有 bug
2. **位置**：具体到文件名 + 行号
3. **说明**：为什么有问题，什么场景会触发
4. **建议修复**：给出修改后的代码片段

## 禁止行为
- ❌ 不要说"整体看起来没问题"
- ❌ 不要跳过任何检查项
- ❌ 不要用"在正常场景下没问题"来敷衍
```

### 2.3 NanoHermes 中使用方式

```bash
# 1. 创建 skill
mkdir -p /mnt/d/code/NanoHermes/skills/code-review/
# 将上面的内容保存为 SKILL.md

# 2. 在对话中使用
请 review 这段代码，加载 code-review 技能

# 3. 或者让系统自动加载
# 当用户说"review"、"审查"、"检查代码"时，技能系统自动匹配加载
```

### 2.4 评论区提到的 Skill

| 提出者 | 推荐 Skill | 说明 |
|--------|-----------|------|
| 余努力 | `superpowers/requesting-code-review` | Superpowers 框架的内置 review 技能 |
| 吴易易 | 自定义 review skill 集 | 针对项目特点定制 |
| Mistletoe | `brook skill` | 可能是某个开源的 review 技能 |

### 2.5 优缺点

| ✅ 优点 | ❌ 缺点 |
|---------|---------|
| 结构化审查，不会漏项 | 仍然受限于同一模型的盲区 |
| 可复用，一次编写多次使用 | 某些隐性问题 checklist 覆盖不到 |
| 成本低，不需要额外模型 | 对于"设计层面"的问题难以发现 |

### 2.6 适用场景

- 日常 code review 的标准化
- 团队统一审查标准
- 作为方案④的前置检查层

---

## 方案 3：Claude 自身 Sub-Agent 并行

### 3.1 核心原理

利用 Claude 自身的多 Agent 能力，把"写"和"审"分配给不同的子 Agent，通过 worktree 隔离工作区。

### 3.2 具体实现（Claude Code 原生）

Claude Code 支持子 Agent 功能，可以通过 prompt 引导：

```
你是一个协调者，请创建两个子 Agent：

1. **开发者 Agent**：负责实现功能，在 worktree A 中工作
2. **审查者 Agent**：负责审查代码，在 worktree B 中工作

两个 Agent 完成后，汇总结果。
```

### 3.3 NanoHermes 实现

```python
# 通过 delegate_task 实现
from src.tools.delegate_task import delegate_task

# 第一个子 Agent：写代码
dev_result = delegate_task(
    goal="实现用户登录功能，包括注册、登录、密码重置",
    toolsets=["terminal", "file"],
    context="项目使用 FastAPI + SQLite，参考现有代码风格"
)

# 第二个子 Agent：审查代码
review_result = delegate_task(
    goal="审查以下代码，重点关注安全性和边界条件",
    toolsets=["terminal", "file"],
    context=dev_result.get("code_files", ""),
    # 注意：这里仍然使用相同的 model
)
```

### 3.4 Worktree 隔离

```bash
# 主分支
git worktree add ../worktree-dev dev-branch

# 审查分支
git worktree add ../worktree-review review-branch

# 开发者在 dev-branch 工作
# 审查者在 review-branch 查看并提意见
# 通过共享的 status.json 协调
```

### 3.5 作者回应的问题

> "Claude 的 quota 经常不够用"

**Quota 消耗分析**：

| 操作 | 预估 Token | 说明 |
|------|-----------|------|
| 开发者 Agent 写代码 | 5,000-15,000 | 取决于代码复杂度 |
| 审查者 Agent 审查 | 3,000-10,000 | 读取代码 + 生成报告 |
| 协调者 Agent 汇总 | 1,000-3,000 | 整合结果 |
| **总计** | **9,000-28,000** | 单次功能开发 |

### 3.6 优缺点

| ✅ 优点 | ❌ 缺点 |
|---------|---------|
| 同一个模型，配置简单 | Quota 消耗大 |
| worktree 隔离，安全 | 盲区可能重叠（同模型） |
| 适合 Claude 生态深度用户 | Claude quota 经常不够用 |

### 3.7 适用场景

- Claude quota 充足时
- 不想引入其他模型的场景
- 快速并行开发

---

## 方案 4：异构模型交叉审查 ⭐ 推荐

### 4.1 核心原理

**不同模型 = 不同训练数据 + 不同架构 + 不同偏好 = 不同盲区**

Claude 和 Codex 看同一段代码，关注点不同：
- Claude（Anthropic）：更关注代码可读性、结构
- Codex（OpenAI）：更关注逻辑正确性、边界条件

两者交叉，盲区覆盖更完整。

### 4.2 工作流（状态机驱动）

```
┌─────────────┐
│   空闲 idle  │
└──────┬──────┘
       │ 用户提出需求
       ▼
┌──────────────────┐
│ Claude 写代码     │
│ 状态: writing    │
└──────┬───────────┘
       │ 写完，更新状态
       ▼
┌──────────────────┐
│ Codex 审查        │
│ 状态: reviewing  │
└──────┬───────────┘
       │ 审查完成
       ▼
   ┌───┴───┐
   │ 有问题？│
   └───┬───┘
  是 /   \ 否
    ▼     ▼
┌─────┐ ┌─────┐
│Claude│ │ Done│
│ 修改 │ └─────┘
└──┬──┘
   │ 改完，状态切回 reviewing
   └──────┐
          ▼
     ┌────────┐
     │ Codex  │
     │ 再审查  │
     └────────┘
```

### 4.3 状态文件协议

```json
// workspace/status.json
{
  "state": "codex_reviewing",
  "last_updated_by": "claude",
  "last_updated_at": "2026-06-28T22:41:00Z",
  "iteration": 3,
  "max_iterations": 5,
  "pending_issues": [
    {
      "file": "src/utils.py",
      "line": 42,
      "severity": "high",
      "description": "空数组未处理",
      "suggested_fix": "if not arr: return []"
    }
  ]
}
```

### 4.4 NanoHermes 实现

```bash
# 1. 配置两个不同的 provider
# .env
DASHSCOPE_BASE_URL=https://api.anthropic.com  # Claude
OPENAI_BASE_URL=https://api.openai.com         # Codex/GPT
```

```python
# 2. 通过 delegate_task 实现交叉审查

# 第一步：Claude 写代码
write_result = delegate_task(
    goal="实现用户登录功能",
    toolsets=["terminal", "file"],
    context="项目使用 FastAPI，参考 src/api/ 下的代码风格"
)

# 第二步：Codex 审查（使用不同模型）
review_result = delegate_task(
    goal="审查以下代码，找出所有潜在 bug",
    toolsets=["terminal", "file"],
    context=f"""
审查以下代码：
{write_result.get("code_summary", "")

重点检查：
1. 空值处理
2. 边界条件
3. 异常场景
4. 并发安全
""",
    model="openai/gpt-4o"  # 关键：指定不同的模型
)

# 第三步：如果有问题，Claude 修改
if review_result.get("has_issues"):
    fix_result = delegate_task(
        goal="根据审查意见修改代码",
        toolsets=["terminal", "file"],
        context=f"""
原始代码：{write_result.get("code_summary", "")}
审查意见：{review_result.get("review_report", "")}

请逐条修复审查意见中提到的问题。
""",
    )
```

### 4.5 作者亲述的实现方式

> "就是共享一个文件夹，约定好协议。你把这篇文章分别喂给 CC 和 Codex 就会帮你弄了。"

**意思是**：直接把这篇文章（或类似的 workflow 描述）分别发给 Claude Code 和 Codex，它们就会自动按照"写→审→改"的循环工作。

### 4.6 Quota 策略优化

| 模型 | Quota 特点 | 使用策略 |
|------|-----------|---------|
| Claude | 经常不够用 | 只用于写代码（核心价值） |
| Codex | 重置频繁 | 承担更多审查工作（"PUA" Codex） |

### 4.7 优缺点

| ✅ 优点 | ❌ 缺点 |
|---------|---------|
| 效果最好，盲区覆盖最全 | Token 消耗增加 |
| 真正的异构审查 | 时间稍慢 |
| 自动化，不需要人工干预 | 需要配置两个模型的 API |

### 4.8 适用场景

- 重要功能开发
- 关键 bug 修复后的验证
- 团队日常 code review 流程

---

## 方案 5：反向交叉（Codex 写 + Claude 审）

### 5.1 核心原理

和方案 4 相反——让 Codex 写代码，Claude 来审查。本质一样，都是异构交叉。

### 5.2 为什么有人用这个方案

| 原因 | 说明 |
|------|------|
| Codex 写代码能力更强 | OpenAI GPT 系列在代码生成上表现突出 |
| Claude 审查更细致 | Anthropic Claude 在安全性、边界条件检查上更严格 |
| 成本考虑 | 取决于各家的 API 定价 |

### 5.3 实现

```python
# 第一步：Codex 写代码
write_result = delegate_task(
    goal="实现用户登录功能",
    toolsets=["terminal", "file"],
    context="项目使用 FastAPI",
    model="openai/gpt-4o"  # Codex 写
)

# 第二步：Claude 审查
review_result = delegate_task(
    goal="审查以下代码",
    toolsets=["terminal", "file"],
    context=write_result.get("code_summary", ""),
    model="anthropic/claude-sonnet-4"  # Claude 审
)
```

### 5.4 小张的实际做法

> "我目前是 codex 写代码然后给 claude 去测试，我去试试你的方式"

说明小张已经在用反向交叉，效果也不错。

### 5.5 优缺点

| ✅ 优点 | ❌ 缺点 |
|---------|---------|
| 和方案 4 一样有效 | 取决于哪个模型写更好 |
| 可以根据场景切换方向 | 需要两套配置 |

---

## 方案 6：多模型轮转审查

### 6.1 核心原理

3 个或更多模型轮流审查，盲区覆盖更全面。

### 6.2 实现

```python
models = [
    "openai/gpt-4o",
    "anthropic/claude-sonnet-4",
    "google/gemini-2.0",
]

review_results = []
for model in models:
    result = delegate_task(
        goal="审查以下代码",
        context=code,
        model=model
    )
    review_results.append(result)

# 汇总所有审查意见
merged_report = merge_reviews(review_results)
```

### 6.3 Token 消耗

| 模型 | 单次审查 Token | 3 模型总计 |
|------|--------------|-----------|
| GPT-4o | ~5,000 | ~15,000 |
| Claude | ~5,000 | ~15,000 |
| Gemini | ~5,000 | ~15,000 |
| **总计** | | **~45,000** |

### 6.4 适用场景

- 安全敏感代码（金融、医疗）
- 核心算法实现
- 开源项目发布前的最终检查

---

## 方案 7：人类 + AI 双重审查

### 7.1 核心原理

AI 负责初筛，人类负责判断"哪些问题是真正需要改的"。

### 7.2 工作流

```
AI 交叉审查 → 生成审查报告 → 资深工程师 review 报告 → 决定哪些要改 → 执行修改 → 再次 AI 验证
```

### 7.3 人类审查的重点

| AI 擅长 | 人类擅长 |
|---------|---------|
| 语法错误、空值检查 | 业务逻辑正确性 |
| 边界条件、异常处理 | 架构设计合理性 |
| 代码风格、规范 | 可维护性、扩展性 |
| 已知漏洞模式 | 新的攻击向量 |

### 7.4 适用场景

- 生产环境上线前
- 安全审计
- 合规要求

---

## 方案对比总表

| 方案 | 配置难度 | Token 消耗 | 效果 | 推荐指数 |
|------|---------|-----------|------|---------|
| ① 开新对话自审 | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ |
| ② Review Skill | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| ③ Claude 子 Agent | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| ④ **异构交叉** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| ⑤ 反向交叉 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| ⑥ 多模型轮转 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| ⑦ 人类+AI | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 最终建议

**日常开发**：方案 ②（Review Skill）+ 方案 ④（异构交叉）组合

**重要功能**：方案 ④（异构交叉）作为主力，方案 ⑦（人类把关）作为最终关卡

**NanoHermes 用户**：
1. 先创建 `code-review` 技能（方案 ②）
2. 配置两个不同模型的 provider
3. 通过 `delegate_task` 实现异构交叉（方案 ④）
4. 重要上线前人工 review（方案 ⑦）
