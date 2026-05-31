## Why

NanoHermes 当前配置散落在 `.env`、`main.py` 硬编码、dataclass 默认值和 JSON 状态文件中，`main.py` 直接绕过 provider 模块的完整配置体系。MCP 支持即将引入更多配置项（服务器列表、传输模式等）。需要统一的 JSON 配置文件 + 配置管理模块，实现一处配置、全局消费。

## What Changes

- 新增 `src/config/` 模块：配置加载、验证、解析的集中管理
- 新增 `nanohermes.json` 配置文件：支持模型、提供商、MCP、TUI、辅助 LLM 等全部配置
- `main.py` 迁移到使用配置模块，消除重复代码
- TUI、provider、auxiliary 模块改为从配置模块读取配置
- 保留 `.env` 用于密钥（gitignored），配置文件用于结构配置（可提交）
- 配置优先级：显式参数 > 配置文件 > `.env` 环境变量 > 模块默认值

## Capabilities

### New Capabilities

- `config-management`: 配置管理核心能力，包括 JSON 配置文件加载、配置验证、优先级解析链、配置数据类定义
- `config-file-format`: 配置文件格式规范，定义 `nanohermes.json` 的 schema 和各配置段结构

### Modified Capabilities

<!-- 无现有 spec 级别需求变更，仅实现层变化 -->

## Impact

- 新增模块：`src/config/`（`__init__.py`, `loader.py`, `schema.py`, `models.py`）
- 新增配置文件：项目根目录 `nanohermes.json`（含示例）
- 修改 `src/main.py`：移除重复配置代码，使用配置模块
- 修改 `src/cli/tui.py`：从配置模块读取 TUI 配置
- 修改 `src/auxiliary/client.py`：从配置模块读取辅助 LLM 配置
- 修改 `src/provider/` 相关模块：与配置模块集成
- 新增依赖：无（使用 Python 内置 `json` 模块）
- 不影响现有 `.env` 文件（密钥仍通过环境变量管理）
