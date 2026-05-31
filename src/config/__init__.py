"""配置管理模块。

NanoHermes 统一配置系统，支持 JSON 配置文件、环境变量和显式参数。

优先级：显式参数 > 项目配置 (./nanohermes.json) > 全局配置 (~/.nanohermes/config.json) > .env > 默认值
"""

from src.config.models import (
    Config,
    ModelConfig,
    ProviderConfig,
    McpConfig,
    McpServerConfig,
    TuiConfig,
    AuxiliaryConfig,
)
from src.config.loader import (
    load_config,
    get_api_key,
    get_base_url,
    load_json_file,
    deep_merge,
)

__all__ = [
    "Config",
    "ModelConfig",
    "ProviderConfig",
    "McpConfig",
    "McpServerConfig",
    "TuiConfig",
    "AuxiliaryConfig",
    "load_config",
    "get_api_key",
    "get_base_url",
    "load_json_file",
    "deep_merge",
]
