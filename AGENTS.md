# AGENTS.md - NanoHermes

## 项目概况

Python 自进化 AI Agent 系统，参考 Hermes Agent 架构。10 个核心模块，~166 个测试。

## 关键命令

```bash
# 启动
python -m src.main              # 交互对话模式
python -m src.main --test-api   # 测试 API 连接
python -m src.main --debug      # debug 模式（输出完整请求/响应 JSON + 思考内容）
python -m src.main --resume     # 恢复最近会话
python -m src.main --resume <id>  # 按 ID 恢复
python -m src.main --resume-title "标题"  # 按标题恢复
python -m src.main --list-sessions  # 列出所有历史会话
python -m src.main --tui        # 启动 TUI 聊天界面

# 快速 API 测试（独立脚本）
python test_api.py

# MCP 服务器启动
python -m src.mcp.server                    # Stdio 模式（默认）
python -m src.mcp.server --transport streamable-http --port 8000  # HTTP 模式
python -m src.mcp.server --transport sse --port 8000              # SSE 兼容模式

# 测试
python -m pytest tests/ -v              # 全部测试
python -m pytest tests/provider/ -v     # 单个模块
python -m pytest tests/tools/ -v
python -m pytest tests/test_e2e.py -v -s  # 端到端（-s 显示输出）
```

## 环境与配置

- **Python >= 3.11**，依赖通过 `pyproject.toml` 管理
- **`.env` 文件**（gitignored）：`DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`、`MODEL_NAME`
- 支持多提供商：DashScope（默认）、OpenAI、Anthropic
- 代码中调用 `load_dotenv()` 自动加载 `.env`
- 安装依赖（国内用清华镜像）：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple openai anthropic pyyaml pydantic python-dotenv rich prompt_toolkit better-sqlite3`
- 开发依赖：`pip install pytest pytest-asyncio pytest-cov`

## 数据存储路径（不在项目目录内）

- **SQLite**: `~/.nanohermes/sessions.db`（会话元数据、FTS5 搜索）
- **JSONL**: `~/.nanohermes/sessions/<session_id>.jsonl`（完整消息历史）
- **Memory**: `~/.nanohermes/memory/`（MEMORY.md / USER.md）
- **MCP Config**: `~/.nanohermes/mcp_servers.json`（外部 MCP 服务配置）

## 架构边界

```
src/
├── main.py / __main__.py    # 入口（耦合所有模块）
├── provider/                # LLM 提供商运行时（凭证/API路由/客户端/回退链）
├── tools/                   # 工具运行时（注册表/分发器/终端/文件/澄清/技能等）
├── mcp/                     # MCP 协议支持（服务器/客户端/桥接/注册表）
├── session/                 # 会话存储（SQLite + JSONL 双存储）
├── memory/                  # 记忆系统（文件提供者 + 编排器）
├── skills/                  # 技能系统（SKILL.md 解析 + Curator 自进化）
├── compression/             # 上下文压缩（摘要预算 + 头尾保护）
├── prompt/                  # 系统提示组装（三层：stable/context/volatile）
├── conversation/            # 核心对话循环 + 错误分类
├── delegation/              # 多 Agent 委托（leaf/orchestrator 角色）
├── insights/                # 指标引擎（token 聚合 + 成本估算）
├── auxiliary/               # 辅助 LLM 客户端（后台任务）
└── cli/                     # TUI 聊天界面 + 流式 CLI
```

## 重要约定

- **每个 `src/<module>/` 必须包含 `ARCHITECTURE.md`**（详见 `openspec/specs/project-conventions/spec.md`）
- 工具通过 AST 自动发现：`discover_tools(tools_dir)` 扫描 `src/tools/` 下的模块
- 代码注释使用**中文**，说明"为什么"而非仅"做什么"
- pytest 配置 `asyncio_mode = "auto"`，无需手动标记异步测试

## 编码规范

### 核心原则：低耦合、高聚合、单一职责

所有代码必须遵循以下原则：

#### 1. 单一职责原则 (SRP)

- **每个类/函数只做一件事**：一个类只有一个改变的理由，一个函数只完成一个明确的任务
- **模块职责清晰**：每个模块有明确的边界，不越权处理其他模块的职责
- **入口文件瘦身**：`main.py` 只负责依赖注入和模块组装，不包含业务逻辑或直接操作 SDK
- **文件大小控制**：单个文件不超过 300 行，超过需拆分

#### 2. 低耦合

- **通过接口交互**：模块间通过抽象类/协议交互，不直接依赖具体实现
- **依赖注入**：对象通过构造函数或参数注入，不在内部创建其他模块实例
- **事件驱动解耦**：使用 `EventBus` 解耦核心循环与外部处理器（记忆、调试、TUI 等）
- **禁止跨模块调用**：不直接调用其他模块的内部方法或访问私有属性

#### 3. 高聚合

- **相关功能放在一起**：将职责相关的代码组织在同一模块中
- **消除重复定义**：相同的数据类型、枚举、常量只定义一次，在共享模块中维护
- **避免数据冗余**：定价数据、模型元数据、配置类型等集中管理，不多处维护

#### 4. 代码简洁易读

- **函数简短**：单个函数不超过 50 行，复杂逻辑拆分为多个小函数
- **命名清晰**：变量/函数名自解释，减少注释依赖
- **减少嵌套**：使用提前返回 (early return) 减少 if/else 嵌套层级
- **避免魔法数字**：使用命名常量替代硬编码的数字和字符串

### 具体规范

#### 模块职责划分

| 模块 | 职责 | 不应包含 |
|------|------|----------|
| `main.py` | 依赖注入、模块组装、CLI 参数解析 | 业务逻辑、SDK 操作、UI 渲染 |
| `provider/` | 凭证解析、客户端构建、API 调用、回退链 | UI 逻辑、会话管理、工具分发 |
| `tools/` | 工具注册、分发、执行 | 对话逻辑、会话存储、记忆管理 |
| `session/` | 会话生命周期、消息存储、搜索 | UI 格式化、对话循环、压缩逻辑 |
| `memory/` | 记忆读写、提供者编排 | 会话管理、工具调用、提示组装 |
| `skills/` | 技能加载、启用/禁用、CRUD | 对话逻辑、UI 渲染、工具分发 |
| `compression/` | 上下文压缩、摘要生成 | 直接操作数据库（通过事件） |
| `prompt/` | 系统提示组装、缓存控制 | 威胁检测（独立安全模块）、文件搜索 |
| `conversation/` | 核心对话循环、事件总线、错误分类 | UI 渲染、工具实现、记忆管理 |
| `cli/` | UI 渲染、用户输入、命令展示 | 对话逻辑、压缩实现、技能管理 |
| `insights/` | 数据聚合、指标计算 | UI 格式化（独立 formatter）、定价数据 |
| `delegation/` | 多 Agent 委托、并发控制 | 工具实现、会话管理 |
| `mcp/` | MCP 协议支持、服务器/客户端 | 工具实现、对话逻辑 |
| `config/` | 配置加载、模型定义、凭证解析 | 业务逻辑、SDK 操作 |
| `auxiliary/` | 后台 LLM 任务（摘要、记忆刷写） | 主对话逻辑、UI 渲染 |

#### 禁止行为

1. **入口文件直接操作 SDK**：使用 `provider/client_factory.py` 的 `build_client()` 工厂
2. **TUI 实现业务逻辑**：命令处理委托给专门的服务层或命令处理器
3. **模块内部创建其他模块实例**：通过依赖注入传入
4. **重复定义相同类型**：共享类型放在相关模块的 `__init__.py` 或独立模块
5. **单文件超过 300 行**：按职责拆分为多个文件
6. **函数超过 50 行**：拆分为多个小函数，每个有明确职责
7. **跨模块直接调用**：通过公共 API 或事件总线交互

#### 推荐模式

```python
# ✅ 正确：通过工厂创建依赖
from src.provider.client_factory import build_client
client = build_client(config)

# ✅ 正确：依赖注入
class TUIApp:
    def __init__(self, session_db: SessionDB, jsonl_store: JsonlSessionStore):
        self.session_db = session_db
        self.jsonl_store = jsonl_store

# ✅ 正确：事件驱动解耦
loop.events.on(EventType.TOOL_START, self._on_tool_start)

# ❌ 错误：内部创建其他模块实例
class TUIApp:
    def __init__(self):
        self.session_db = SessionDB(db_path)  # 应该注入

# ❌ 错误：入口文件直接操作 SDK
from openai import OpenAI
client = OpenAI(api_key=api_key)  # 应该用 build_client()
```

## OpenSpec 工作流

```bash
# 探索模式（讨论架构）
/opsx-explore

# 创建变更提案
/opsx-propose <name>

# 实现变更
/opsx-apply <name>

# 归档完成变更
/opsx-archive <name>
```

变更规范位于 `openspec/changes/<name>/`，项目规范位于 `openspec/specs/`。

## 测试注意

- 测试框架：pytest + pytest-asyncio（auto 模式）
- 端到端测试需要有效 API Key 和 `.env` 配置
- 并发测试验证多线程场景（`test_concurrent.py`）
- 集成测试验证完整启动流程（`test_main_integration.py`）
