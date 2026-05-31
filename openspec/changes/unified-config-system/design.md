## Context

NanoHermes 当前配置管理采用混合模式：
- `.env` 存储 API 密钥和基础 URL
- `main.py` 中硬编码配置读取逻辑（重复 2 次）
- provider 模块有完整的配置体系（ProviderProfile、CredentialResult、客户端工厂）但未被 main.py 使用
- TUI 配置通过 dict 硬编码传递
- Auxiliary 配置通过 dataclass 默认值
- MCP 支持即将引入更多配置项（服务器列表、传输模式等）

## Goals / Non-Goals

**Goals:**
- 统一 JSON 配置文件作为结构配置的唯一来源
- 新建 `src/config/` 模块提供配置加载、验证、解析能力
- 配置优先级：显式参数 > 项目配置 > 全局配置 > `.env` > 默认值
- 保持 `.env` 用于密钥管理（安全最佳实践）
- 支持 MCP 服务器配置
- 所有现有配置项均可迁移到配置文件

**Non-Goals:**
- 不替代 `.env` 文件（密钥仍通过环境变量）
- 不改变 provider 模块的内部架构（Profile、CredentialResult 等保持不变）
- 不支持热重载配置
- 不支持配置文件的加密存储

## Decisions

### 1. 配置文件格式：JSON

选择 JSON 而非 YAML/TOML：
- Python 3.11+ 内置 `json` 模块，零额外依赖
- 程序化读写简单可靠
- 缺点是无注释，但通过 schema 验证和示例文件弥补

### 2. 配置文件位置：双层级

```
~/.nanohermes/config.json    # 全局配置（用户级默认）
./nanohermes.json            # 项目配置（覆盖全局）
```

项目配置覆盖全局配置，实现"项目特定配置可提交，个人偏好放全局"。

### 3. 配置优先级链

```
显式参数 (CLI args)
    ↓
项目配置 (./nanohermes.json)
    ↓
全局配置 (~/.nanohermes/config.json)
    ↓
环境变量 (.env)
    ↓
模块默认值
```

每层只覆盖上层的未设置值（deep merge）。

### 4. 配置数据模型：Pydantic

使用 Pydantic 定义配置数据类，提供：
- 类型验证
- 默认值
- 嵌套配置结构
- 序列化/反序列化

项目已有 pydantic 依赖。

### 5. 模块结构

```
src/config/
├── __init__.py      # load_config(), Config 入口
├── models.py        # Pydantic 数据模型
├── loader.py        # 文件加载 + 优先级合并
└── schema.py        # JSON Schema 定义（可选，用于验证）
```

### 6. 与 provider 模块的集成

配置模块输出 `ResolvedConfig` 包含：
- `model`: 模型名称
- `provider`: 提供商 ID
- `api_key`: 解析后的 API Key（从 env 读取）
- `base_url`: 解析后的 Base URL

provider 模块的 `ProviderProfile` 注册表保持不变，配置模块通过提供商 ID 查找 profile，然后解析凭证。

### 7. 向后兼容

- `.env` 文件继续有效
- 如果配置文件不存在，回退到当前行为（.env + 默认值）
- `main.py` 中原有的 `os.environ.get()` 调用替换为 `load_config()`

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| JSON 无注释，用户可能不理解配置项 | 提供示例文件 `nanohermes.example.json` + 文档 |
| 配置文件包含敏感信息 | 明确文档说明 API Key 通过 `_env` 后缀引用环境变量，不直接存储 |
| Pydantic 验证错误信息不友好 | 自定义验证错误处理器，输出中文提示 |
| 迁移期间 main.py 和 config 模块并存 | 一次性替换，不保留旧代码路径 |
| 全局配置和项目配置 deep merge 复杂 | 使用简单的 dict merge，不递归合并列表（列表完全覆盖） |

## Migration Plan

1. 创建 `src/config/` 模块和数据模型
2. 创建 `nanohermes.example.json` 示例文件
3. 修改 `main.py` 使用配置模块
4. 修改 `src/cli/tui.py` 从配置读取
5. 修改 `src/auxiliary/client.py` 从配置读取
6. 更新文档
7. 测试验证

Rollback: 如果配置文件加载失败，回退到 `.env` + 默认值行为。
