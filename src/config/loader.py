"""配置加载器。

实现文件加载、优先级合并、环境变量解析和完整配置解析链。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.config.models import Config

logger = logging.getLogger(__name__)

# 配置文件路径
PROJECT_CONFIG = Path("nanohermes.json")
GLOBAL_CONFIG_DIR = Path.home() / ".nanohermes"
GLOBAL_CONFIG = GLOBAL_CONFIG_DIR / "config.json"


def load_json_file(path: Path) -> dict[str, Any] | None:
    """安全加载 JSON 文件。

    Args:
        path: JSON 文件路径。

    Returns:
        解析后的字典，如果文件不存在或无效则返回 None。
    """
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            logger.warning(f"配置文件 {path} 根节点不是对象，已跳过")
            return None
        logger.debug(f"已加载配置文件: {path}")
        return data
    except json.JSONDecodeError as e:
        logger.warning(f"配置文件 {path} 包含无效 JSON: {e}，已跳过")
        return None
    except Exception as e:
        logger.warning(f"加载配置文件 {path} 失败: {e}，已跳过")
        return None


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """深度合并两个字典。

    列表完全覆盖，不递归合并。

    Args:
        base: 基础字典。
        override: 覆盖字典。

    Returns:
        合并后的字典。
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve_env_credentials(config_dict: dict[str, Any]) -> dict[str, Any]:
    """从环境变量解析 API Key 等凭证。

    遍历配置，查找 *_env 后缀的字段，从环境变量读取实际值。
    注意：api_key_env 字段保留环境变量名，不替换为实际值，
    因为 _resolve_api_key 需要用它来读取环境变量。

    Args:
        config_dict: 配置字典。

    Returns:
        解析后的配置字典。
    """
    resolved = {}
    for key, value in config_dict.items():
        if isinstance(value, dict):
            resolved[key] = resolve_env_credentials(value)
        elif key == "api_key_env":
            resolved[key] = value
        elif key.endswith("_env") and isinstance(value, str):
            env_value = os.environ.get(value)
            if env_value:
                resolved[key] = env_value
            else:
                logger.debug(f"环境变量 {value} 未设置")
                resolved[key] = value
        else:
            resolved[key] = value
    return resolved


def load_env_defaults() -> dict[str, Any]:
    """从 .env 文件加载默认配置。

    Returns:
        从环境变量提取的配置字典。
    """
    load_dotenv()

    config: dict[str, Any] = {}

    # 模型配置
    model_name = os.environ.get("MODEL_NAME")
    if model_name:
        config["model"] = {"name": model_name}

    # 如果设置了通用的 OPENAI_API_KEY，默认 provider 设为 openai
    if os.environ.get("OPENAI_API_KEY"):
        config.setdefault("model", {})["provider"] = "openai"

    # 提供商配置
    providers: dict[str, Any] = {}

    # 优先读取业界通用的 OpenAI 兼容接口变量
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
    if openai_key:
        providers["openai"] = {
            "base_url": openai_url,  # None 时使用 SDK 默认值
            "api_key_env": "OPENAI_API_KEY",
        }

    # 兼容特定厂商的变量
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    dashscope_url = os.environ.get("DASHSCOPE_BASE_URL")
    if dashscope_key:
        providers["dashscope"] = {
            "base_url": dashscope_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key_env": "DASHSCOPE_API_KEY",
        }

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        providers["anthropic"] = {
            "base_url": None,
            "api_key_env": "ANTHROPIC_API_KEY",
        }

    if providers:
        config["providers"] = providers

    return config


def load_config(
    model: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    config_file: str | None = None,
) -> Config:
    """加载并解析完整配置。

    优先级：显式参数 > 项目配置 > 全局配置 > .env 环境变量 > 默认值

    Args:
        model: 显式指定模型名称。
        provider: 显式指定提供商。
        api_key: 显式指定 API Key。
        base_url: 显式指定 Base URL。
        config_file: 显式指定配置文件路径（覆盖项目配置）。

    Returns:
        完整的 Config 对象。
    """
    # 1. 加载全局配置
    global_data = load_json_file(GLOBAL_CONFIG) or {}

    # 2. 加载项目配置
    project_path = Path(config_file) if config_file else PROJECT_CONFIG
    project_data = load_json_file(project_path) or {}

    # 3. 加载 .env 默认值
    env_data = load_env_defaults()

    # 4. 合并（优先级：项目 > 全局 > env）
    merged = deep_merge(env_data, global_data)
    merged = deep_merge(merged, project_data)

    # 5. 应用显式参数
    if model:
        merged.setdefault("model", {})["name"] = model
    if provider:
        merged.setdefault("model", {})["provider"] = provider
    if api_key:
        merged.setdefault("providers", {})["__explicit_api_key__"] = api_key
    if base_url:
        merged.setdefault("providers", {})["__explicit_base_url__"] = base_url

    # 6. 解析环境变量凭证
    merged = resolve_env_credentials(merged)

    # 7. 创建 Config 对象
    try:
        config = Config.from_dict(merged)
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        raise ValueError(f"配置验证失败: {e}")

    # 8. 验证 API Key
    if not api_key:
        api_key = _resolve_api_key(config)
        if not api_key:
            logger.warning("未找到 API Key，请检查 .env 文件或配置中的 api_key_env")

    logger.info(f"配置已加载: model={config.model.provider}/{config.model.name}")
    return config


def _resolve_api_key(config: Config) -> str | None:
    """从配置解析 API Key。"""
    provider_id = config.model.provider

    # 检查显式传入的 key
    if "__explicit_api_key__" in config.providers:
        return config.providers["__explicit_api_key__"]

    # 从提供商配置获取
    provider_cfg = config.providers.get(provider_id)
    if provider_cfg and provider_cfg.api_key_env:
        return os.environ.get(provider_cfg.api_key_env)

    # 回退：尝试常见环境变量
    for env_var in ["DASHSCOPE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        key = os.environ.get(env_var)
        if key:
            return key

    return None


def get_api_key(config: Config) -> str | None:
    """获取解析后的 API Key。"""
    return _resolve_api_key(config)


def get_base_url(config: Config) -> str | None:
    """获取解析后的 Base URL。"""
    provider_id = config.model.provider

    # 检查显式传入的 URL
    if "__explicit_base_url__" in config.providers:
        return config.providers["__explicit_base_url__"]

    # 从提供商配置获取
    provider_cfg = config.providers.get(provider_id)
    if provider_cfg and provider_cfg.base_url:
        return provider_cfg.base_url

    # 回退到 provider 注册表
    try:
        from src.provider.profile import get_provider_profile
        profile = get_provider_profile(provider_id)
        if profile and profile.base_url:
            return profile.base_url
    except Exception:
        pass

    return None
