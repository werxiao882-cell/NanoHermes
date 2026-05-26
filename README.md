# NanoHermes

自进化 AI Agent 系统 - 从零构建的完整 AI Agent 框架。

## 项目简介

NanoHermes 是一个参考 Hermes Agent 架构、使用 Python 从零构建的自进化 AI Agent 系统。支持多提供商 LLM 接入、工具调用、会话持久化、跨会话记忆、上下文压缩、多 Agent 委托、技能系统等核心功能。

## 快速开始

### 环境要求

- Python >= 3.11
- 有效的 LLM API Key（如通义千问、OpenAI、Anthropic 等）

### 安装依赖

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple openai anthropic pyyaml pydantic python-dotenv
```

### 配置

在项目根目录创建 `.env` 文件（已包含在 `.gitignore` 中，不会被提交）：

```bash
# 通义千问 DashScope
DASHSCOPE_API_KEY=your-api-key-here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen3.6-plus

# OpenAI
# OPENAI_API_KEY=your-api-key-here
# MODEL_NAME=gpt-4o

# Anthropic
# ANTHROPIC_API_KEY=your-api-key-here
# MODEL_NAME=claude-sonnet-4-20250514
```

### 启动

```bash
# 测试 API 连接
python -m src.main --test-api

# 交互对话模式
python -m src.main

# Debug 模式（输出请求体/响应体 JSON + 思考内容）
python -m src.main --debug

# 恢复最近会话
python -m src.main --resume

# 恢复指定会话
python -m src.main --resume <session_id>

# 通过标题恢复会话
python -m src.main --resume-title "My Session"
```

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--test-api` | 测试 API 连接 |
| `--debug` | 开启 debug 模式，输出完整请求体/响应体 JSON 和模型思考内容 |
| `--resume [SESSION_ID]` | 恢复历史会话，不指定 ID 时恢复最近会话 |
| `--resume-title TITLE` | 通过标题恢复历史会话 |
| `quit` / `exit` | 退出对话 |
| `clear` | 清空当前对话历史 |
| `status` | 查看当前会话状态（模型、token 用量） |

## 项目结构

```
NanoHermes/
├── src/                              # 源代码
│   ├── main.py                       # 启动入口（交互模式 + API 测试 + 会话恢复）
│   ├── __main__.py                   # python -m src.main 入口
│   │
│   ├── provider/                     # Provider Runtime - LLM 提供商运行时
│   │   ├── ARCHITECTURE.md           # 架构文档
│   │   ├── profile.py                # ProviderProfile 数据结构和注册表
│   │   ├── builtins.py               # 内置提供商配置 (OpenAI, Anthropic, OpenRouter)
│   │   ├── credentials.py            # 凭证解析链 + Key 隔离检查
│   │   ├── api_mode.py               # API Mode 路由 (chat_completions/anthropic_messages)
│   │   ├── client_factory.py         # 客户端工厂 (OpenAI/Anthropic SDK)
│   │   ├── openai_client.py          # OpenAI 客户端封装 (聊天/流式/中断/错误分类)
│   │   ├── anthropic_adapter.py      # Anthropic 适配器 (OpenAI ↔ Anthropic 格式转换)
│   │   ├── fallback.py               # 回退模型链 (一次性激活语义)
│   │   └── model_metadata.py         # 模型元数据 (上下文长度 + 定价 + 成本估算)
│   │
│   ├── tools/                        # Tool Runtime - 工具运行时
│   │   ├── ARCHITECTURE.md           # 架构文档
│   │   ├── registry.py               # 工具注册表 (自注册模型 + AST 发现)
│   │   ├── toolsets.py               # 工具集定义和解析 (enabled/disabled 过滤)
│   │   ├── availability.py           # 工具可用性检查 (缓存 + 去重)
│   │   ├── dispatcher.py             # 工具分发器 (JSON 参数解析 + 错误包装)
│   │   ├── terminal.py               # 终端工具 (subprocess + 危险命令检测)
│   │   ├── file_tools.py             # 文件工具 (read_file/write_file/search_files)
│   │   └── async_bridge.py           # 异步桥接 (持久 loop + 新线程策略)
│   │
│   ├── session/                      # Session Storage - 会话存储
│   │   ├── ARCHITECTURE.md           # 架构文档
│   │   ├── schema.py                 # SQLite Schema (sessions/messages/state_meta/FTS5)
│   │   ├── session_db.py             # SessionDB (WAL 模式 + 生命周期管理)
│   │   └── jsonl_store.py            # JsonlSessionStore (JSONL 完整历史 + 会话恢复)
│   │
│   ├── memory/                       # Memory System - 记忆系统
│   │   ├── provider.py               # MemoryProvider 抽象基类
│   │   ├── managers.py               # MemoryManager 编排器
│   │   └── file_provider.py          # FileMemoryProvider (MEMORY.md/USER.md)
│   │
│   ├── skills/                       # Skill System - 技能系统
│   │   ├── loader.py                 # SkillLoader (SKILL.md 解析)
│   │   └── curator.py                # Curator (后台自进化)
│   │
│   ├── compression/                  # Context Compression - 上下文压缩
│   │   └── compressor.py             # ContextCompressor (摘要预算 + 头尾保护)
│   │
│   ├── prompt/                       # Prompt Assembly - 系统提示组装
│   │   └── assembler.py              # PromptAssembler (三层架构)
│   │
│   ├── conversation/                 # Conversation Loop - 对话循环
│   │   ├── loop.py                   # ConversationLoop (核心循环 + debug 模式)
│   │   └── error_classifier.py       # ErrorClassifier (错误分类)
│   │
│   ├── delegation/                   # Multi-Agent Delegation - 多 Agent 委托
│   │   └── manager.py                # DelegationManager (单任务/批量委托)
│   │
│   ├── insights/                     # Insights Metrics - 洞察指标
│   │   └── engine.py                 # InsightsEngine (token 聚合 + 成本估算)
│   │
│   └── auxiliary/                    # Auxiliary Client - 辅助 LLM
│       ├── ARCHITECTURE.md           # 架构文档
│       └── client.py                 # AuxiliaryClient (后台任务调用)
│
├── tests/                            # 单元测试 (135 个测试)
│   ├── provider/                     # Provider Runtime 测试 (7 个文件)
│   ├── tools/                        # Tool Runtime 测试 (5 个文件)
│   ├── test_main_integration.py      # 集成测试 (14 个测试)
│   ├── test_concurrent.py            # 并发测试 (6 个测试)
│   ├── test_e2e.py                   # 端到端测试 (1 个测试)
│   └── test_jsonl_store.py           # JSONL 存储测试 (17 个测试)
│
├── openspec/                         # OpenSpec 变更管理
│   ├── changes/                      # 活跃变更
│   │   ├── provider-runtime/
│   │   ├── tool-runtime/
│   │   ├── session-storage/
│   │   ├── memory-system/
│   │   ├── skill-system/
│   │   ├── context-compression/
│   │   ├── system-prompt-assembly/
│   │   ├── conversation-loop/
│   │   ├── multi-agent-delegation/
│   │   └── insights-metrics/
│   └── specs/                        # 项目规范
│       └── project-conventions/      # 架构文档规范
│
├── .env                              # 本地配置 (不提交到 git)
├── .gitignore
├── pyproject.toml                    # Python 项目配置
├── test_api.py                       # 快速 API 测试脚本
└── README.md                         # 本文件
```

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        NanoHermes                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              Conversation Loop (核心引擎)                 │   │
│   │   模型调用 → 工具分发 → 重试 → 压缩触发 → 后台审查        │   │
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
│   │     (LLM 提供商适配 + 工具注册/分发/执行)                  │   │
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

| 模块 | 职责 | 状态 |
|------|------|------|
| **provider-runtime** | 凭证解析、API 路由、客户端封装、回退链、模型元数据 | ✅ 完成 |
| **tool-runtime** | 工具注册表、工具集、分发器、终端工具、文件工具、异步桥接 | ✅ 完成 |
| **session-storage** | SQLite 会话存储、FTS5 搜索、JSONL 完整历史、会话恢复 | ✅ 完成 |
| **memory-system** | 记忆提供者接口、编排器、文件记忆 | ✅ 完成 |
| **skill-system** | SKILL.md 解析、Curator 自进化 | ✅ 完成 |
| **context-compression** | 上下文压缩、摘要预算、头尾保护 | ✅ 完成 |
| **system-prompt-assembly** | 三层提示组装 (stable/context/volatile) | ✅ 完成 |
| **conversation-loop** | 核心对话循环、错误分类、debug 模式 | ✅ 完成 |
| **multi-agent-delegation** | 委托管理、leaf/orchestrator 角色 | ✅ 完成 |
| **insights-metrics** | 洞察报告、成本估算、活动趋势 | ✅ 完成 |

## 工具列表

| 工具 | 功能 |
|------|------|
| `terminal` | 执行 shell 命令，支持危险命令检测和审批 |
| `read_file` | 读取文件内容，支持分页和行号 |
| `write_file` | 写入文件内容，自动创建父目录 |
| `search_files` | 搜索匹配模式的文件，支持递归 |

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/provider/ -v
python -m pytest tests/tools/ -v

# 运行集成测试
python -m pytest tests/test_main_integration.py -v

# 运行并发测试
python -m pytest tests/test_concurrent.py -v

# 运行端到端测试
python -m pytest tests/test_e2e.py -v -s

# 运行 JSONL 存储测试
python -m pytest tests/test_jsonl_store.py -v
```

## 开发规范

每个 `src/<module>/` 目录必须包含 `ARCHITECTURE.md` 架构文档，内容包括：
- 模块职责和边界
- 核心类/函数关系图
- 数据流和调用链
- 关键设计决策
- 外部依赖

详见 `openspec/specs/project-conventions/spec.md`。

## 许可证

MIT
