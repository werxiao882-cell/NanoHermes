## 1. Config 模块基础结构

- [x] 1.1 创建 `src/config/` 目录和 `__init__.py`
- [x] 1.2 创建 `src/config/models.py` - 定义 Pydantic 数据模型（ModelConfig, ProviderConfig, McpConfig, TuiConfig, AuxiliaryConfig, Config）
- [x] 1.3 创建 `src/config/loader.py` - 实现文件加载和优先级合并逻辑
- [x] 1.4 创建 `src/config/ARCHITECTURE.md` - 模块架构文档

## 2. 配置数据模型实现

- [x] 2.1 实现 `ModelConfig` - provider, name, context_length 字段
- [x] 2.2 实现 `ProviderConfig` - base_url, api_key_env 字段
- [x] 2.3 实现 `McpServerConfig` 和 `McpConfig` - servers 数组，transport 类型
- [x] 2.4 实现 `TuiConfig` - typing_speed, show_tool_panel, tool_panel_position
- [x] 2.5 实现 `AuxiliaryConfig` - provider, model, max_tokens, temperature
- [x] 2.6 实现 `Config` 根模型 - 包含所有子section + 默认值

## 3. 配置加载器实现

- [x] 3.1 实现 `load_json_file()` - 安全加载 JSON 文件，处理不存在和无效 JSON
- [x] 3.2 实现 `deep_merge()` - 两层配置文件的深度合并（列表完全覆盖）
- [x] 3.3 实现 `resolve_env_credentials()` - 从环境变量解析 API Key
- [x] 3.4 实现 `load_config()` 主函数 - 完整优先级链：显式参数 > 项目配置 > 全局配置 > .env > 默认值
- [x] 3.5 实现配置验证和错误提示（中文）

## 4. 示例配置文件

- [x] 4.1 创建 `nanohermes.example.json` - 完整示例配置（含注释说明）
- [x] 4.2 创建 `nanohermes.example.minimal.json` 的最小版本示例

## 5. main.py 迁移

- [x] 5.1 在 `main.py` 中导入配置模块
- [x] 5.2 删除 `test_api()` 和 `main_chat()` 中重复的 `os.environ.get()` 配置代码
- [x] 5.3 使用 `load_config()` 替换所有配置读取
- [x] 5.4 使用 provider 模块的客户端工厂替代直接 `OpenAI()` 调用

## 6. TUI 模块迁移

- [x] 6.1 修改 `src/cli/tui.py` 从 Config 对象读取 TUI 配置
- [x] 6.2 移除硬编码的 `config={"typing_speed": 10}` 传递

## 7. Auxiliary 模块迁移

- [ ] 7.1 修改 `src/auxiliary/client.py` 从 Config 对象读取辅助 LLM 配置
- [ ] 7.2 移除硬编码的默认值回退逻辑

## 8. Provider 模块集成

- [ ] 8.1 确保配置模块与 `src/provider/builtins.py` 注册表集成
- [ ] 8.2 配置模块通过 provider ID 查找 ProviderProfile 获取 base_url 默认值

## 9. 测试

- [ ] 9.1 编写 `tests/config/test_models.py` - 数据模型验证测试
- [ ] 9.2 编写 `tests/config/test_loader.py` - 配置加载和优先级测试
- [ ] 9.3 编写 `tests/config/test_integration.py` - 集成测试（完整加载流程）
- [ ] 9.4 运行全部测试确保通过

## 10. 文档

- [ ] 10.1 更新 `src/cli/ARCHITECTURE.md` 反映配置模块
- [ ] 10.2 更新 `docs/TUI_V2_GUIDE.md` 中的配置说明
