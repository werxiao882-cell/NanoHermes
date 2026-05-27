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

## 架构边界

```
src/
├── main.py / __main__.py    # 入口（耦合所有模块）
├── provider/                # LLM 提供商运行时（凭证/API路由/客户端/回退链）
├── tools/                   # 工具运行时（注册表/分发器/终端/文件/澄清/技能等）
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
