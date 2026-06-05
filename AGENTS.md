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

### 注释规范

#### 核心原则：解释"为什么"而非仅"做什么"

代码注释使用**中文**，重点解释设计决策、边界情况和潜在陷阱，而非简单描述代码功能。

#### 必须添加注释的场景

1. **复杂 Python 语法**：
   - 生成器（`yield` 语义、背压、调用栈连续性）
   - 装饰器（工作原理、适用场景、副作用）
   - 异步代码（`async/await` 使用理由、事件循环管理）
   - 闭包（词法作用域、状态捕获、生命周期）
   - 类型注解（泛型、联合类型、可调用类型的设计理由）

2. **设计模式实现**：
   - 工厂模式（为什么选择工厂而非直接实例化）
   - 单例模式（类变量 vs 实例变量、线程安全）
   - 观察者模式（事件订阅机制、解耦理由）
   - 策略模式（算法选择依据、扩展点）
   - 责任链模式（链式调用、回退策略）

3. **架构决策**：
   - 模块边界划分理由
   - 依赖注入 vs 内部创建
   - 同步 vs 异步选择
   - 缓存策略设计
   - 错误处理和恢复机制

4. **算法和公式**：
   - 数学公式的推导过程
   - 阈值选择的理论依据
   - 性能优化的权衡
   - 边界情况处理

5. **安全考量**：
   - 输入验证和防护策略
   - 权限控制机制
   - 数据隔离和隐私保护
   - 原子操作和并发安全

#### 注释格式要求

```python
# ✅ 正确：解释设计决策
# 设计理由：
# 使用 SHA256 哈希判断 stable 层内容是否变化。
# - SHA256 碰撞概率极低，适合缓存失效判断
# - 只取前 16 位（64 bit），足够唯一性且节省存储空间
# - 64 bit 的碰撞概率约为 1/2^64，对于实际应用足够安全

# ✅ 正确：解释边界情况
# 注意：当 stable 层为空时，返回空字符串而非 None
# 这样调用方无需检查返回值类型，简化使用

# ❌ 错误：仅描述功能
# 计算哈希值
hash = hashlib.sha256(content.encode()).hexdigest()
```

#### 模块级文档字符串

每个模块文件开头必须包含文档字符串，说明：
- 模块职责和边界
- 主要组件和数据流
- 关键设计决策
- 依赖关系

```python
"""系统提示组装模块。

三层架构：
1. stable: 身份、工具指导、技能提示、环境提示（缓存友好）
2. context: 上下文文件、system_message
3. volatile: 记忆快照、用户画像、时间戳（每轮变化）

设计理由：
- stable 层变化少，适合 Anthropic prompt caching
- context 层每会话变化
- volatile 层每轮变化，不适合缓存

安全特性：
- 上下文威胁检测（10 种模式）
- 不可见 Unicode 字符检测
- 严重程度分级（critical/high/medium/low）
"""
```

#### 函数和方法注释

复杂函数必须包含：
- 设计理由（为什么这样实现）
- 参数说明（类型、用途、边界情况）
- 返回值说明
- 异常说明
- 边界情况和潜在陷阱

```python
def apply_anthropic_cache_control(
    self,
    parts: list[PromptPart],
    *,
    ttl: int = 300,
) -> list[PromptPart]:
    """应用 Anthropic prompt caching 标记。

    设计理由：
    Anthropic Claude 支持 prompt caching 功能，可以缓存 100K+ tokens 的系统提示。
    缓存策略：将 stable 层的最后一个部分标记为缓存断点（cache breakpoint）。
    
    为什么选择最后一个 stable 部分？
    - Anthropic 的缓存机制要求缓存的内容必须在 prompt 的前面部分
    - stable 层是不变的内容（身份、工具指导等），最适合缓存
    - 标记最后一个 stable 部分可以缓存所有 stable 内容
    - context 和 volatile 层每轮变化，不适合缓存
    
    缓存 TTL 默认 300 秒（5 分钟），这是 Anthropic 的最小缓存时间。
    超过 TTL 后缓存会被清除，需要重新构建。

    Args:
        parts: 提示片段列表。
        ttl: 缓存 TTL（秒），默认 300 秒。

    Returns:
        标记后的片段列表。
    """
```

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
