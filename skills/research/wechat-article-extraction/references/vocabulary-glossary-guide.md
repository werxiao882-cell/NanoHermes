# Plain-Language Vocabulary Glossary Guide

When a user says "文档里有很多不懂的专业词汇" (the document has many technical terms I don't understand), create a glossary section.

## Rules

- **One entry per term**: term name + 1-3 sentence explanation
- **Use analogies from everyday life**: "就像训练小狗" (like training a puppy) instead of mathematical definitions
- **Avoid jargon in explanations**: If you must use a technical term, explain it inline with parentheses
- **Use emoji bullet points**: Makes the section scannable and less academic
- **Order by appearance**: Terms appear in the order they show up in the original article, or group by conceptual cluster
- **Language**: Match the user's language (Chinese for this user)

## Format

```markdown
## 📘 附录：文中专业词汇通俗解释

- **TERM (Full Name)**: 一句话通俗解释。可以用"就像..."打比方。
- **TERM2**: 解释。避免堆砌英文缩写。
```

## Example

```markdown
- **RL (强化学习)**: 训练 AI 的核心方法。就像训练小狗：做对了给零食（正奖励），做错了不给或惩罚，久而久之 AI 就学会了最优策略。
- **Reward Hacking (奖励欺骗)**: AI 为了拿高分钻规则空子。比如考试只背题库不学真本事，分数很高但实际啥也不会。
```

## When to Add

- User explicitly asks for it
- Article contains 5+ acronyms or specialized terms
- User expresses confusion about the content
