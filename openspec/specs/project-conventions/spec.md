## 架构文档

每个 change 实现的源码目录（如 `src/session/`、`src/memory/`）必须包含一个 `ARCHITECTURE.md` 文件。

### 要求

- **位置**：放在该 change 对应的源码根目录，如 `src/<module>/ARCHITECTURE.md`
- **时机**：在实现代码之前或同步编写，不得事后补写
- **内容**：
  - 模块职责和边界
  - 核心类/函数的关系图（ASCII 或 Mermaid）
  - 数据流和调用链
  - 关键设计决策及原因
  - 外部依赖
- **维护**：代码变更时必须同步更新架构文档

### 示例结构

```
src/
├── session/
│   ├── ARCHITECTURE.md    ← 必须
│   ├── session_db.ts
│   ├── schema.ts
│   └── ...
└── memory/
    ├── ARCHITECTURE.md    ← 必须
    ├── memory_provider.ts
    └── ...
```

### 最小内容要求

```markdown
# <Module Name> Architecture

## Responsibility
一句话说明模块做什么。

## Components
┌──────────┐     ┌──────────┐
│  Comp A  │────▶│  Comp B  │
└──────────┘     └──────────┘

## Data Flow
1. ...
2. ...

## Design Decisions
- **Decision**: ...
- **Reason**: ...

## Dependencies
- Internal: ...
- External: ...
```
