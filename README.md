# NanoHermes

自进化 AI Agent 系统 - 从零构建的完整 AI Agent 框架。

## 项目简介

NanoHermes 是一个参考 Hermes Agent 架构、使用 Python 从零构建的自进化 AI Agent 系统。支持多提供商 LLM 接入、工具调用（延迟加载 + 按需搜索）、会话持久化、跨会话记忆、上下文压缩、多 Agent 委托、技能系统等核心功能。

## 快速开始

### 环境要求

- Python >= 3.11
- 有效的 LLM API Key（如通义千问、OpenAI、Anthropic 等）

### 安装依赖

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple openai anthropic pyyaml pydantic python-dotenv rich prompt_toolkit
```

### 配置

NanoHermes 使用 JSON 配置文件 + `.env` 环境变量管理所有设置。

**优先级**：显式参数 > 项目配置 (`./nanohermes.json`) > 全局配置 (`~/.nanohermes/config.json`) > `.env` > 默认值

#### 配置文件

创建 `nanohermes.json`（项目级）或 `~/.nanohermes/config.json`（全局级）：

```json
{
  "model": {
    "provider": "dashscope",
    "name": "qwen3.6-plus"
  },
  "providers": {
    "dashscope": {
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key_env": "DASHSCOPE_API_KEY"
    }
  },
  "tui": {
    "typing_speed": 10,
    "show_tool_panel": true,
    "tool_panel_position": "right"
  }
}
```

完整示例请参考 `nanohermes.example.json`。

#### 环境变量（密钥）

API Key 等敏感信息通过 `.env` 文件管理（不会被提交到 git）：

```bash
# 通义千问 DashScope
DASHSCOPE_API_KEY=your-api-key-here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen3.6-plus

# OpenAI
# OPENAI_API_KEY=your-api-key-here

# Anthropic
# ANTHROPIC_API_KEY=your-api-key-here
```

### 启动

```bash
# TUI 交互模式（默认）
python -m src.main

# Debug 模式（输出完整请求/响应 JSON + 思考内容）
python -m src.main --debug

# 恢复最近会话
python -m src.main --resume

# 恢复指定会话
python -m src.main --resume <session_id>

# 通过标题恢复会话
python -m src.main --resume-title "My Session"

# 列出所有历史会话
python -m src.main --list-sessions
```

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--debug` | 开启 debug 模式，输出完整请求/响应 JSON 和模型思考内容 |
| `--resume [SESSION_ID]` | 恢复历史会话，不指定 ID 时恢复最近会话 |
| `--resume-title TITLE` | 通过标题恢复历史会话 |
| `--list-sessions` | 列出所有历史会话 |

## 项目结构

```
NanoHermes/
├── src/                              # 源代码
│   ├── main.py                       # 组合根（依赖注入 + 模块组装）
│   ├── __main__.py                   # python -m src.main 入口
│   │
│   ├── config/                       # 统一配置管理
│   ├── provider/                     # LLM 提供商运行时
│   ├── tools/                        # 工具运行时（注册/分发/搜索）
│   ├── mcp/                          # MCP 协议支持
│   ├── session/                      # 会话存储（SQLite + JSONL）
│   ├── memory/                       # 记忆系统
│   ├── skills/                       # 技能系统
│   ├── compression/                  # 上下文压缩
│   ├── prompt/                       # 系统提示组装
│   ├── conversation/                 # 核心对话循环 + 事件总线 + 责任链拦截
│   ├── delegation/                   # 多 Agent 委托
│   ├── insights/                     # 指标引擎
│   ├── auxiliary/                    # 辅助 LLM 客户端
│   ├── cli/                          # TUI 聊天界面
│   └── hooks/                        # 责任链拦截器（危险命令拦截、ScriptHook、配置加载）
│
├── tests/                            # 单元测试
├── openspec/                         # OpenSpec 变更管理
├── nanohermes.example.json           # 完整示例配置
├── pyproject.toml                    # Python 项目配置
└── README.md                         # 本文件
```

> 每个 `src/<module>/` 目录包含 `ARCHITECTURE.md` 架构文档，详细说明模块职责、数据流和设计决策。新增 `src/hooks/` 模块提供责任链拦截机制。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        NanoHermes                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              Conversation Loop (核心引擎)                 │   │
│   │   模型调用 → 工具分发 → 重试 → 动态工具发现 → 压缩触发    │   │
│   └──────────────────────┬──────────────────────────────────┘   │
│                          │                                      │
│    ┌──────────┬──────────┼──────────┬──────────┬──────────┐    │
│    ▼          ▼          ▼          ▼          ▼          ▼    │
│ ┌──────┐ ┌───────┐ ┌────────┐ ┌────────┐ ┌──────┐ ┌───────┐  │
│ │session│ │memory │ │context │ │delegate│ │skill │ │prompt │  │
│ │storage│ │system │ │compress│ │-ation  │ │system│ │assembly│ │
│ └──────┘ └───────┘ └────────┘ └────────┘ └──────┘ └───────┘  │
│    │          │          │          │          │          │    │
│    ▼          │          │          │          │          │    │
│ ┌──────┐      │          │          │          │          │    │
│ │insights│    │          │          │          │          │    │
│ │metrics │    │          │          │          │          │    │
│ └──────┘    │          │          │          │          │    │
│             ▼          ▼          ▼          ▼          ▼    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │           Provider Runtime + Tool Runtime                │   │
│   │     (LLM 提供商适配 + 工具注册/分发/执行/BM25 搜索)        │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         SQLite + JSONL (双存储层)                        │   │
│   │   SQLite: 搜索/统计  |  JSONL: 完整历史/会话恢复         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 核心模块

| 模块 | 职责 | 详细文档 |
|------|------|----------|
| **config** | 统一配置管理、JSON 配置文件加载、优先级解析链 | `src/config/ARCHITECTURE.md` |
| **provider** | 凭证解析、API 路由、客户端封装、回退链、模型元数据 | `src/provider/ARCHITECTURE.md` |
| **tools** | 工具注册表、分发器、BM25+Regex 搜索引擎、延迟加载 | `src/tools/ARCHITECTURE.md` |
| **session** | SQLite 会话存储、FTS5 搜索、JSONL 完整历史 | `src/session/ARCHITECTURE.md` |
| **memory** | 记忆提供者接口、编排器、文件记忆 | `src/memory/ARCHITECTURE.md` |
| **skills** | SKILL.md 解析、Curator 自进化 | `src/skills/ARCHITECTURE.md` |
| **compression** | 上下文压缩、摘要预算、头尾保护 | `src/compression/ARCHITECTURE.md` |
| **conversation** | 核心对话循环、事件总线、责任链拦截机制、错误分类、动态工具管理、三层提示组装 | `src/conversation/ARCHITECTURE.md` |
| **hooks** | 危险命令拦截器、ScriptHook 包装类、配置加载器 | `src/hooks/ARCHITECTURE.md` |
| **delegation** | 委托管理、leaf/orchestrator 角色 | `src/delegation/ARCHITECTURE.md` |
| **insights** | Token 聚合、成本估算、活动趋势 | `src/insights/ARCHITECTURE.md` |
| **auxiliary** | 后台 LLM 任务（摘要生成、记忆刷写） | `src/auxiliary/ARCHITECTURE.md` |
| **cli** | TUI 聊天界面、事件处理器、责任链拦截、流式组件 | `src/cli/ARCHITECTURE.md` |
| **mcp** | MCP 协议支持、服务器/客户端/桥接 | `src/mcp/ARCHITECTURE.md` |

## 工具系统

### 延迟加载机制

NanoHermes 采用 **Tool Search** 机制（参考 Claude Code 2.1.69），将工具分为两类：

**始终加载**（`defer_loading=False`，6 个）：启动时加入 LLM 上下文
| 工具 | 描述 |
|------|------|
| `read_file` | 读取文件内容，支持分页和行号 |
| `write_file` | 写入文件内容，自动创建父目录 |
| `search_files` | 搜索文件内容（正则）或按名称查找 |
| `patch` | 查找替换编辑，支持 replace/patch 模式 |
| `terminal` | 执行 shell 命令，支持后台进程 |
| `search_tools` | 搜索可用的延迟加载工具（BM25 + Regex） |

**延迟加载**（`defer_loading=True`，11 个）：通过 `search_tools` 工具按需发现
| 工具 | 描述 | 触发场景 |
|------|------|----------|
| `execute_code` | 执行 Python 代码 | 多步骤处理需要 3+ 工具调用 |
| `process` | 后台进程管理 | 管理 terminal 启动的后台进程 |
| `todo` | 任务列表管理 | 复杂任务有 3+ 步骤 |
| `memory` | 持久记忆 | 保存用户偏好或环境信息 |
| `session_search` | 历史会话搜索 | 回忆过去的工作 |
| `clarify` | 向用户提问 | 任务存在歧义需要澄清 |
| `skill_view` | 查看技能内容 | 加载特定技能的详细指导 |
| `skills_list` | 列出可用技能 | 发现相关技能 |
| `skill_manage` | 技能管理 | 创建/更新技能 |
| `delegate_task` | 子 Agent 委托 | 并行或推理密集型子任务 |
| `cronjob` | 定时任务管理 | 设置周期性任务 |

### 搜索引擎

`search_tools` 使用 BM25（自然语言）+ Regex（精确匹配）双引擎，Auto 模式自动选择策略：
- **BM25**: 适合自然语言查询（"send a message to a user"）
- **Regex**: 适合精确模式匹配（"get_.*_data"）
- **Auto**: 检测查询中是否包含正则特征字符（`.*+?^$` 等），自动选择策略

> 详细实现原理请参考 `src/tools/ARCHITECTURE.md`。

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/provider/ -v
python -m pytest tests/tools/ -v

# 运行端到端测试
python -m pytest tests/test_e2e.py -v -s
```

## 开发规范

每个 `src/<module>/` 目录必须包含 `ARCHITECTURE.md` 架构文档，内容包括：
- 模块职责和边界
- 核心类/函数关系图
- 数据流和调用链
- 关键设计决策
- 外部依赖

详见 `openspec/specs/project-conventions/spec.md`。

## Vibe Coding 最佳实践

基于 NanoHermes 项目的实际开发经验，总结出以下 Vibe Coding 最佳实践：

### 1. 探索先行，谋定后动

在开始编码前，先进入 explore mode 讨论：
- 项目整体架构和模块依赖关系
- 实现优先级和关键路径
- 技术选型和替代方案对比
- 潜在风险和未知因素

> **经验**: NanoHermes 的 16 个核心模块在实现前都经过了充分的架构讨论，避免了返工。

### 2. 小步快跑，频繁提交

- 每个小功能一个 commit，保持提交粒度小
- 提交信息清晰描述变更内容
- 功能实现后立即提交，不要堆积

```bash
# 好的提交示例
feat(provider-runtime): 实现 ProviderProfile 数据结构和注册表
test(provider-runtime): 添加 Provider Registry 单元测试
fix(session-storage): 修复 JSONL 保存工具调用结果
```

### 3. 测试驱动，质量保障

- 每个功能模块都要有对应的单元测试
- 测试失败立即修复，不要遗留
- 不仅单元测试，还要端到端测试验证完整流程
- 并发测试验证多线程/多进程场景

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/provider/ -v

# 运行端到端测试
python -m pytest tests/test_e2e.py -v -s
```

### 4. 文档同步，知识沉淀

- 代码实现的同时更新 OpenSpec 规范
- 每个模块包含 `ARCHITECTURE.md` 架构文档
- README 持续更新，反映最新功能
- 提交信息包含 OpenSpec 更新说明

### 5. 详细注释，中文优先

- 所有代码添加详细中文注释
- 类、函数、关键逻辑块都要有注释
- 注释说明"为什么"而不仅仅是"做什么"

```python
def resolve_credentials(env_vars: list[str], ...) -> CredentialResult:
    """按优先级链解析凭证。

    解析顺序：
    1. 显式传入的 API Key（最高优先级）
    2. 环境变量（按配置的优先级顺序查找）
    3. 配置文件中的值
    4. 提供商默认值

    安全检查：
    - 在检查环境变量时，会验证该 Key 是否与目标 base_url 兼容
    """
```

### 6. 参考实现，站在巨人肩膀上

- 参考成熟项目（如 Hermes Agent）的架构设计
- 学习优秀的代码模式和最佳实践
- 根据项目实际情况进行适配和优化

> **经验**: NanoHermes 的技能管理系统参考了 Hermes Agent 的 `skill_manager_tool.py`，实现了创建、编辑、补丁、删除等完整功能。

### 7. 统一规范，保持一致性

- 统一文件命名格式（如 `<category>_tool.py`）
- 统一代码风格和注释格式
- 统一错误处理和返回格式
- 统一测试结构和命名

### 8. 用户反馈循环

- 用户提出需求 → 快速实现 → 测试验证 → 用户反馈 → 持续改进
- 保持沟通畅通，及时响应问题
- 根据反馈调整实现方向

### 9. 模块化设计，职责清晰

- 每个模块职责单一，高内聚低耦合
- 每个类别独立文件，便于维护
- 清晰的依赖关系，避免循环依赖

```
src/tools/
├── registry.py              # 注册表（核心）
├── dispatcher.py            # 分发器（核心）
├── search_tool.py           # BM25 + Regex 搜索引擎 + search_tools
├── terminal.py              # 终端工具
├── file_tool.py             # 文件工具
├── clarify_tool.py          # 澄清提问
├── code_execution_tool.py   # 代码执行
└── ...                      # 其他工具类别
```

### 10. 持续集成，自动化验证

- 每次提交前运行测试
- 使用 CI/CD 自动化测试流程
- 测试覆盖率作为质量指标

---

**NanoHermes 项目统计**:
- 🏗️ 16 个核心模块（含 hooks 责任链拦截系统）
- 🧪 ~960 个测试
- 📝 100+ 源文件
- 🔄 持续迭代中

## Vibe Coding 环境

本项目使用以下工具和环境进行开发：

| 类别 | 工具/框架 | 说明 |
|------|-----------|------|
| **Agent 框架** | opencode | 命令行 AI 编程助手，支持 explore mode 和 change proposal 工作流 |
| **主要模型** | Qwen3.6-Plus (通义千问) | 通过 DashScope API 调用，支持工具调用和长上下文 |
| **API 端点** | `https://dashscope.aliyuncs.com/compatible-mode/v1` | OpenAI 兼容模式 |
| **编程语言** | Python 3.14 | 主要开发语言 |
| **测试框架** | pytest + pytest-asyncio | 单元测试和异步测试 |
| **UI 库** | rich + prompt_toolkit | TUI 聊天界面 |
| **数据库** | SQLite (Python 标准库) | 会话持久化存储 |
| **LLM SDK** | openai + anthropic | 多提供商支持 |
| **配置管理** | JSON 配置文件 + python-dotenv + Pydantic 验证 | 统一配置管理 |
| **版本控制** | Git + GitHub | 代码托管和协作 |
| **包管理** | pip + pyproject.toml | Python 依赖管理 |
| **镜像源** | 清华大学 PyPI 镜像 | 加速依赖下载 |

### 配置示例

**nanohermes.json**（结构配置）：
```json
{
  "model": {
    "provider": "dashscope",
    "name": "qwen3.6-plus"
  },
  "providers": {
    "dashscope": {
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key_env": "DASHSCOPE_API_KEY"
    }
  }
}
```

**.env**（密钥）：
```bash
DASHSCOPE_API_KEY=sk-xxx
```

### opencode 工作流

```bash
# 探索模式 - 讨论架构和设计
/opsx-explore

# 创建变更提案
/opsx-propose add-new-feature

# 实现变更
/opsx-apply add-new-feature

# 归档完成的变更
/opsx-archive add-new-feature
```

## AI Agent 集成测试设计原则

NanoHermes 的集成测试遵循以下核心原则，确保 AI Agent 系统在真实环境下可靠运行：

### 1. 真实 API 测试，拒绝 Mock

集成测试使用**真实 LLM API 请求**，不使用 Mock。Mock 测试无法发现工具链集成 bug、API 响应格式变化、以及端到端流程中的实际问题。

### 2. PTY 驱动的对话模拟

通过 PTY（伪终端）启动 Agent，模拟真实用户交互：
- 启动 Agent 并等待 TUI 渲染完成
- 发送用户消息并等待 AI 响应
- 验证工具调用链和输出正确性
- 测试多轮对话上下文保持能力

### 3. 从 OpenSpec 推导测试用例

每个完成的 OpenSpec 变更都映射为测试用例：
- **核心功能**：验证 spec 要求的主要行为
- **边界情况**：异常输入、空值、极限条件
- **集成测试**：与其他模块的交互验证

### 4. 工具链全覆盖

| 测试类型 | 验证内容 |
|----------|----------|
| 基础对话 | AI 正确响应和自我介绍 |
| 读取工具 | read_file 调用、内容展示 |
| 写入工具 | write_file 调用、文件创建 |
| 编辑工具 | patch 调用、内容更新 |
| 搜索工具 | search_files 调用、结果正确 |
| 执行工具 | execute_code 调用、计算正确 |
| 多轮上下文 | AI 能引用之前的对话内容 |
| 错误处理 | 优雅的错误消息而非崩溃 |
| 记忆持久化 | MEMORY.md 正确更新 |
| TUI 命令 | /tools、/sessions、/skills 正确输出 |

### 5. 持久化验证

测试完成后验证数据持久化：
```bash
# 会话存储
ls ~/.nanohermes/sessions/*.jsonl
sqlite3 ~/.nanohermes/sessions.db "SELECT count(*) FROM sessions;"

# 记忆系统
cat ~/.nanohermes/memory/MEMORY.md
cat ~/.nanohermes/memory/USER.md
```

### 6. 已知陷阱

- **API 签名假设**：始终使用 `inspect.signature()` 检查实际参数，不要假设 API 签名
- **PTY 缓冲**：使用 `process(action='log')` 查看完整输出，避免缓冲截断
- **记忆去重**：`add_entry` 不去重，频繁提及的事实会出现多次，这是已知限制而非 bug
- **AI 过度搜索**：当要求"测试工具"时，AI 可能多次调用 search_files，这是预期行为
- **清理**：始终发送 `/quit` 后再终止进程

### 7. 测试文档化

测试执行过程中实时记录：
```markdown
## 测试: [ID] [描述]
**用户输入**: "..."
**AI 行为**: 调用 [工具]，结果: ...
**结果**: 通过 / 失败
```

---

## 测试体系

### PTY 端到端测试 Skill

NanoHermes 内置 PTY 测试 skill，位于 `skills/nanohermes-pty-testing/`，用于真实环境下的端到端功能验证。

#### 设计原理

**渐进式披露**：SKILL.md 仅保留 7 阶段测试流程和方法论（182 行），324 个详细用例按功能域拆分到 7 个 reference 文件中，在执行到对应阶段时按需加载，避免一次性注入过多 token。

```
skills/nanohermes-pty-testing/
├── SKILL.md                      # 核心导航 — 7 阶段流程 + 方法论
├── references/                   # 详细用例（按需加载）
│   ├── session-storage.md        # 70 用例 — SessionDB 全功能验证
│   ├── core-tools.md             # 79 用例 — 工具运行时 + Dispatcher
│   ├── provider-config.md        # 56 用例 — Provider + 配置 + 提示组装
│   ├── conversation.md           # 48 用例 — 对话循环 + 事件系统 + 委托
│   ├── advanced.md               # 44 用例 — 技能/压缩/指标/MCP/辅助
│   ├── cli-tui.md                # 18 用例 — TUI 界面
│   └── memory-system.md          # 12 用例 — 记忆系统
├── templates/report-template.md  # 测试报告模板
└── scripts/validate-sessions.py  # 会话存储验证脚本
```

#### 用例分级

| 标记 | 含义 | 数量 | 执行方式 |
|------|------|------|---------|
| `[PTY]` | 直接可执行 | 120 | PTY 对话 + 命令 + 文件验证 |
| `[DEBUG]` | 需 --debug 模式 | 30 | 观察完整请求/响应 JSON |
| `[FAULT]` | 需故障注入 | 18 | 临时改 Key/断网触发错误 |
| `[MANUAL]` | 仅手动 TUI | 8 | 真实终端键盘交互 |
| `[UNIT]` | 仅单元测试 | 148 | pytest 或压力测试 |

#### 作用

1. **版本发布验收**：每次发布前执行 P0 用例，确保核心功能正常
2. **Bug 回归验证**：修复 bug 后重新执行相关用例，防止回退
3. **新功能验收**：新功能开发完成后，补充对应用例并执行
4. **测试自动化基础**：为后续 CI/CD 集成提供用例清单和执行流程

#### 使用方式

AI Agent 加载此 skill 后，按 7 阶段流程自动执行。详细用例在对应阶段通过 `skill_view(name='nanohermes-pty-testing', file_path='references/xxx.md')` 按需加载。

```bash
# 快速执行 P0 用例（约 5 分钟）
# 阶段 1: 环境准备 → 阶段 2: 启动验证 → 阶段 3: 基础对话+工具链 → 阶段 5: 存储验证
```

## 许可证

MIT
