# Explain Abstract Concepts Using User's Own Project

When a user asks "XXX到底是什么" (what exactly is XXX) about an abstract/technical concept, explain it by mapping the concept onto the user's own project context.

## Technique

1. **Identify the user's project context** from memory or the conversation. For this user: NanoHermes / Hermes Agent (Python AI Agent CLI system).

2. **Map the abstract concept to concrete behaviors** the user has seen their agent perform:
   - Concept: "Agentic RL" → Concrete: "Hermes Agent running terminal commands, debugging, using tools"
   - Concept: "Reward function" → Concrete: "Tests passing (+100), tests failing (-10), infinite loop (-50)"
   - Concept: "Credit assignment" → Concrete: "Which specific command in the debug chain actually fixed the bug?"

3. **Use a comparison table** to show progression:
   | Before (basic LLM) | Middle (basic Agent) | After (Agentic RL) |
   |---|---|---|
   | 只能说话 | 能说话+能用工具 | 能自主决策+反思进化 |

4. **Keep it to one concrete scenario** rather than abstract theory. One good example beats three definitions.

## Format

```markdown
### 📘 特别篇：用 [User's Project] 秒懂什么是 [Concept]

1. 先拆解概念（去掉学术定义，用白话）
2. 配合 [User's Project] 的通俗解释（分阶段对比）
3. 核心区别总结表
4. 一句话总结
```

## When to Use

- User asks for explanation of a paper/concept
- Article is highly technical with dense terminology
- User has an existing project that maps well to the concept
