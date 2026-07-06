# 不靠谱的 Claude Code

> **作者**：吴师兄学大模型  
> **发布时间**：2026年6月28日 22:41  
> **地点**：广东  
> **阅读量**：4353  
> **原文链接**：https://mp.weixin.qq.com/s/jr_V7IRawelz70rp44o4uw

---

先说个我自己踩了挺久才认清的事：**Claude Code 写代码很猛，但让它自查代码，经常不靠谱。**

不是它完全查不出问题，而是它对自己刚写完的东西太宽容，同一个模型，前脚把代码写出来，后脚你再让它 review，很多时候它会很自然地告诉你：逻辑没问题，可以合并。

自己埋的坑、漏掉的边界，它不一定看不见，但很容易轻轻放过去。

我之前在 AlgoMooc 改一段算法动画的调度逻辑，就遇到过一次，Claude 改完之后说已经修复，自测通过。

我不太放心，又让它 review 一遍。它看完之后继续确认：边界处理没问题。

结果一上线，某道题的数据一为空，页面直接白屏。

最后查下来，根因就是它自己写的循环少判了一个空数组。

这个坑是它亲手埋的，自审的时候却当成"符合预期"放过去了。

这事其实不难理解。

让写代码的人给自己判卷，他脑子里已经有了一个预设：这段代码大概率是对的。

带着这个预设去审，很多时候不是在找问题，而是在给自己的结论找证据。

人会这样，模型也会这样。

从那以后，我对单模型自审就没那么信了。

后来我换了个思路：别让它自己审，找个外人来审。

我把 Codex 拉进来，当 Claude Code 的交叉审查员。

Claude 负责写，Codex 专门挑刺。

关键是它们不是同一个模型。Codex 看 Claude 写的代码，没有"这是我刚写的"那层包袱，就当外人代码来审。

该指出问题就指出问题，该说边界不够就说边界不够。

模型体系不同，盲区也不完全一样。

很多 Claude 自己放过去的问题，Codex 反而能一眼拎出来。

我后来干脆把它固定进流程里。

两边各盯一个共享状态文件接力，Claude 写完，把状态切到 Codex 待审，Codex 审完，把问题和结论写回去，再把状态切回 Claude。

谁也不直接指挥谁，全靠状态机往下推进。

这样一来，交叉审查就不再靠我每次手动提醒，流程里天然卡着这一道关。

当然，代价也要讲清楚。

多一个模型审，token 基本会多一截，时间也会慢一点。

跑下来最大的体感是：它不是让 Codex 变得多神，而是让整个流程更稳。

真正起作用的，不是某个模型突然聪明了，而是**"异构 + 交叉"这个结构**。

一个模型写，一个模型审，本来就比自己审自己更靠谱。

所以我的结论很简单：别让写代码的那个，给自己判卷。

不管是人还是模型，自审都有盲区。

真正能兜住问题的，往往不是更用力地提醒它认真检查，而是换一个没包袱的视角，站在旁边专门挑刺。

---

## 💬 留言 18

### 吴易易
换个 skill 就行了吧，专门给它一个 review 的 skill 集
> **吴师兄学大模型**：我试下效果看看

### 余努力
可以试试 `superpowers/requesting-code-review`，开新对话用
> *(作者未回复)*

### zyh
开新对话就行了吧，效果应该和换模型差不多
> **吴师兄学大模型**：试过了，效果不如 Codex

### 海星海星
没必要吧，纯纯浪费 token。不如把 Agent 管理做好，Claude 本身有子 Agent 功能和并行 worktree
> **吴师兄学大模型**：现在也是自动化了，但 Claude 的 quota 经常不够用，Codex 的 quota 重置频繁，所以"PUA" Codex 干更多活
> 
> **吴师兄学大模型**：[附图] 大概就这个效果 👍

### 小张
是 codex to claude 这种插件吗？怎么设置的？
> **吴师兄学大模型**：就是共享一个文件夹，约定好协议。你把这篇文章分别喂给 cc 和 codex 就会帮你弄了
> 
> **小张**：我目前是 codex 写代码然后给 claude 去测试，我去试试你的方式

### 零一
模型已经学会人类摸鱼了，加约束只会让他们更努力摸鱼 😂
> *(作者未回复)*

### Mistletoe
brook skill，或者类似的 review skill
> *(作者未回复)*

### 陈立 Leo
Multi-Agent 就要不同模型，不然开发者和测试者是同一角色，伪协作
> *(作者未回复)*

### 江米
最好换个模型，差异越大效果越好
> *(作者未回复)*

### 小zh
是不是重启对话就可以了，感觉是当前上下文的问题
> **吴师兄学大模型**：我试过了，效果一般般

---

## 📚 专业词汇通俗解释

### 1. Claude Code

**一句话解释**：Anthropic 公司推出的命令行 AI 编程助手，能在你的终端里直接写代码、改代码、跑测试。

**通俗类比**：就像一个坐在你电脑前的程序员实习生——你告诉他要做什么，他直接在终端里敲代码、跑命令、改 bug。但他也是"人"，会犯"自己写的代码自己看不出问题"的毛病，就像本文作者亲身经历的那样。

**NanoHermes 中的对应**：NanoHermes 的 `provider/` 模块可以配置 Anthropic 的 Claude 模型作为 LLM 后端（通过 `DASHSCOPE_BASE_URL` 或直接使用 Anthropic SDK），配合 `tools/` 中的 `terminal`、`read_file`、`write_file` 等工具，就能实现类似 Claude Code 的能力——让 AI 直接操作代码文件、执行命令。

**关键代码路径**：
- `src/provider/client_factory.py`：构建 Claude/OpenAI 客户端
- `src/provider/anthropic_client.py`：Anthropic API 调用封装
- `src/tools/terminal.py`：让 AI 能执行 shell 命令
- `src/tools/patch.py`：让 AI 能精准修改代码文件

### 2. Codex（OpenAI Codex CLI）

**一句话解释**：OpenAI 推出的命令行 AI 编程工具，与 Claude Code 定位类似，但底层模型不同。

**通俗类比**：另一个公司的程序员实习生。跟 Claude 不是同一个"脑子"，所以看问题的角度不一样。让 Codex 审查 Claude 写的代码，就像让 B 公司的工程师review A 公司的代码——没有"面子包袱"，该挑刺就挑刺。

**NanoHermes 中的对应**：NanoHermes 同样支持 OpenAI 兼容的 API（通过 `DASHSCOPE_BASE_URL` 和 `MODEL_NAME` 配置），可以调用 GPT 系列模型。`src/provider/provider_fallback.py` 实现了回退链机制，可以在不同模型之间切换。

### 3. 交叉审查（Cross-Review）

**一句话解释**：用一个 AI 模型写代码，用另一个完全不同的模型来审查代码。

**通俗类比**：就像公司里的 code review——写代码的人和审代码的人不是同一个人。如果同一个人写+审，很容易"自己给自己打分"；换个人来看，就能发现之前忽略的 bug。

**NanoHermes 中的对应**：NanoHermes 的 `src/delegation/` 模块实现了多 Agent 委托机制。可以通过 `delegate_task` 让不同的子 Agent 使用不同的模型（通过 `model` 参数指定），天然支持"一个写、一个审"的模式。

**关键代码路径**：
- `src/delegation/`：多 Agent 委托系统
- `delegate_task` 工具：支持为子 Agent 指定不同模型
- `src/conversation/conversation_loop.py`：核心对话循环，支持多轮对话

### 4. 状态机（State Machine）

**一句话解释**：一种流程控制机制，系统在任何时刻都处于某个明确的"状态"，通过状态切换来控制流程走向。

**通俗类比**：就像一个交通灯——红灯、黄灯、绿灯三种状态，每个状态对应不同的规则。Claude 写完代码就把"灯"从"写"切换到"待审"，Codex 审完再把"灯"切回"待改"或"通过"。谁也不指挥谁，全靠"灯的颜色"来协调。

**NanoHermes 中的对应**：NanoHermes 的 `src/conversation/conversation_loop.py` 本身就是一个大状态机——有 `idle`、`thinking`、`tool_calling`、`waiting` 等状态。`src/hooks/` 中的责任链拦截机制也是一种状态机模式。

**关键代码路径**：
- `src/conversation/conversation_loop.py`：对话状态管理
- `src/hooks/`：责任链拦截器（`EventBus.intercept()`）
- `src/tools/todo.py`：任务状态管理工具

### 5. Token

**一句话解释**：AI 模型处理文本的基本单位，一个 Token 大约相当于一个汉字或英文单词的一部分。

**通俗类比**：就像计程车的"里程计费"——Token 越多，"车费"越贵。用两个模型交叉审查，相当于请了两个律师看同一份合同，费用自然翻倍。

**NanoHermes 中的对应**：NanoHermes 的 `src/insights/` 模块专门做 token 用量统计和成本估算。

**关键代码路径**：
- `src/insights/`：指标引擎，token 聚合 + 成本估算
- `src/compression/`：上下文压缩，控制 token 用量

### 6. Quota（配额）

**一句话解释**：AI 服务的使用额度限制，通常按时间周期（如每小时、每天）计算。

**通俗类比**：就像手机话费套餐——每个月有固定的通话分钟数，用完了就得等下个月或者加钱。Claude 的配额经常不够用，Codex 的配额重置更频繁，所以作者"PUA" Codex 来干更多活。

**NanoHermes 中的对应**：NanoHermes 的 `src/provider/provider_fallback.py` 实现了回退链——当一个模型的 API 额度用完或报错时，自动切换到备用模型。

**关键代码路径**：
- `src/provider/provider_fallback.py`：回退链机制
- `src/provider/credentials.py`：API 密钥管理

### 7. Multi-Agent（多智能体）

**一句话解释**：多个 AI 代理协作完成复杂任务，每个代理负责不同的角色。

**通俗类比**：就像一个项目组——有人负责写代码（开发者），有人负责测试（QA），有人负责架构设计（架构师）。如果开发者和测试者是同一个"人"（同一个模型），就变成了"自导自演"，很难发现自己的问题。

**NanoHermes 中的对应**：NanoHermes 的 `src/delegation/` 模块完整实现了多 Agent 系统，支持 `leaf`（执行者）和 `orchestrator`（协调者）两种角色。

**关键代码路径**：
- `src/delegation/`：多 Agent 委托系统
- `src/tools/delegate_task.py`：任务分发工具
- `src/conversation/event_bus.py`：Agent 间通信机制

### 8. Skill（技能）

**一句话解释**：AI 代理的专业知识包，用 Markdown 文件定义，告诉 AI 在特定场景下该怎么做。

**通俗类比**：就像游戏里的"技能书"——吃了"Python 技能书"就会写 Python，吃了"代码审查技能书"就会 review 代码。评论区有人建议"换个 skill 就行了"，意思是给 Claude 一个专门的 code review 技能包，而不需要换模型。

**NanoHermes 中的对应**：NanoHermes 的 `src/skills/` 模块实现了完整的技能系统。

**关键代码路径**：
- `src/skills/`：技能系统
- `src/tools/skill_manage.py`：技能的创建/更新/删除
- `src/tools/skills_list.py`：列出可用技能
- `src/tools/skill_view.py`：加载技能内容
- `SKILL.md`：技能定义文件

### 9. Worktree（工作树）

**一句话解释**：Git 的一种功能，允许在同一仓库的多个分支上并行工作，互不干扰。

**通俗类比**：就像同一个工地上的多个独立施工区域——A 队在修东边的路，B 队在修西边的路，各自干活互不影响。Claude 的子 Agent 可以用 worktree 实现并行开发。

**NanoHermes 中的对应**：NanoHermes 目前没有显式的 worktree 管理，但 `src/delegation/` 中的子 Agent 有独立的 working directory（通过 `workdir` 参数），实现了类似的隔离效果。

### 10. 共享文件夹 + 协议（Shared Folder + Protocol）

**一句话解释**：两个 AI 代理通过读写同一个文件夹中的文件来协调工作，约定好文件格式（协议）来传递信息。

**通俗类比**：就像两个不在同一个办公室的同事，通过一个共享的在线文档来交接工作——A 写完把状态改成"待审"，B 看到后开始审，审完把结果写上去再把状态改回来。

**NanoHermes 中的对应**：NanoHermes 的 `src/session/` 使用 JSONL 文件存储会话消息，`src/memory/` 使用 Markdown 文件存储记忆。多 Agent 之间可以通过文件系统进行异步通信。

---

## 📊 NanoHermes vs 文章理念的对照

| 文章概念 | NanoHermes 实现 | 状态 | 说明 |
|---------|----------------|------|------|
| 交叉审查（不同模型） | `delegate_task` 支持指定不同 model | ⬜ 部分支持 | 需要用户手动为子 Agent 指定不同模型 |
| 状态机流程控制 | `conversation_loop.py` 状态机 + `EventBus` | ✅ 已实现 | 完整的对话状态管理 |
| 技能系统（Review Skill） | `src/skills/` 完整技能系统 | ✅ 已实现 | 可以创建专门的 code review 技能 |
| 多 Agent 协作 | `src/delegation/` 模块 | ✅ 已实现 | 支持 leaf/orchestrator 角色 |
| 回退链（Quota 管理） | `provider_fallback.py` | ✅ 已实现 | 模型间自动回退 |
| Token 用量监控 | `src/insights/` | ✅ 已实现 | token 聚合 + 成本估算 |
| 上下文压缩 | `src/compression/` | ✅ 已实现 | 摘要预算 + 头尾保护 |

## 💡 可以借鉴文章改进的方向

1. **内置交叉审查技能**：在 `skills/` 中增加一个 `cross-model-review` 技能，自动配置两个不同模型的子 Agent，一个写、一个审
2. **状态文件驱动的多 Agent 工作流**：实现基于文件的 Agent 协调协议，让多个 Agent 通过共享状态文件自动接力
3. **模型异构性检测**：在 `delegate_task` 中增加提醒——如果子 Agent 和主 Agent 使用相同模型，提示用户考虑切换不同模型以获得更好的审查效果
