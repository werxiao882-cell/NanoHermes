"""配置加载器。

实现文件加载、优先级合并、环境变量解析和完整配置解析链。

设计决策：
- 采用多层级配置来源（项目配置、全局配置、环境变量、显式参数），
  通过优先级合并实现灵活的配置覆盖机制。
- 使用 deep_merge 实现深度合并，避免浅层合并导致的嵌套配置丢失。
- 环境变量凭证延迟解析，支持配置文件中引用环境变量名而非硬编码值。
- 使用 Pydantic 模型验证确保配置完整性，在入口处快速失败。
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
# 项目级配置：位于工作目录，便于版本控制和团队协作
PROJECT_CONFIG = Path("nanohermes.json")
# 全局配置：位于用户主目录，存储个人偏好和跨项目共享设置
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

    合并策略：
    - 对于嵌套字典，递归合并，保留 base 中存在但 override 中不存在的键。
    - 对于列表和标量值，override 完全覆盖 base，不尝试合并列表元素。

    为什么列表不合并？
    - 列表通常表示有序集合（如工具列表、模型列表），合并可能导致重复或顺序混乱。
    - 配置覆盖场景下，用户期望新配置完全替换旧配置，而非追加。

    Args:
        base: 基础字典（低优先级）。
        override: 覆盖字典（高优先级）。

    Returns:
        合并后的字典，base 和 override 的深拷贝结果。
    """
    # 创建 base 的浅拷贝，避免修改原始字典
    result = base.copy()
    for key, value in override.items():
        # 仅当两边都是 dict 时才递归合并
        # 这确保嵌套配置（如 providers.openai.base_url）能正确覆盖
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            # 列表、标量、或 base 中不存在的键：直接覆盖
            result[key] = value
    return result


def resolve_env_credentials(config_dict: dict[str, Any]) -> dict[str, Any]:
    """从环境变量解析 API Key 等凭证。

    工作原理：
    - 遍历配置字典，查找以 _env 结尾的字段（如 api_key_env、proxy_env）。
    - 将这些字段的值视为环境变量名，从 os.environ 中读取实际值。
    - 如果环境变量未设置，保留原始值（可能是默认值或占位符）。

    特殊处理 api_key_env：
    - api_key_env 字段保留环境变量名，不替换为实际值。
    - 原因：_resolve_api_key() 需要知道环境变量名来动态读取，
      而非在配置加载时就固化具体值，这样支持运行时环境变量变化。

    为什么使用 _env 后缀约定？
    - 避免配置文件中硬编码敏感信息（API Key）。
    - 支持不同环境（开发、测试、生产）使用不同的凭证。
    - 配置文件可安全提交到版本控制。

    Args:
        config_dict: 配置字典（可能包含 _env 后缀字段）。

    Returns:
        解析后的配置字典（_env 字段被替换为环境变量实际值，api_key_env 除外）。
    """
    resolved = {}
    for key, value in config_dict.items():
        if isinstance(value, dict):
            # 递归处理嵌套字典（如 providers.openai 配置）
            resolved[key] = resolve_env_credentials(value)
        elif key == "api_key_env":
            # 特殊保留：不替换为实际值，供后续 _resolve_api_key 使用
            resolved[key] = value
        elif key.endswith("_env") and isinstance(value, str):
            # 查找环境变量，如 "DASHSCOPE_API_KEY" -> 实际 key 值
            env_value = os.environ.get(value)
            if env_value:
                resolved[key] = env_value
            else:
                # 环境变量未设置：保留原始值（可能是默认值）
                # 不报错，允许配置有合理的 fallback
                logger.debug(f"环境变量 {value} 未设置")
                resolved[key] = value
        else:
            # 普通字段：直接传递
            resolved[key] = value
    return resolved


def load_env_defaults() -> dict[str, Any]:
    """从 .env 文件加载默认配置。

    为什么需要这个函数？
    - .env 文件是业界标准的本地配置方式，便于开发和部署。
    - 支持多种环境变量命名约定（OPENAI_API_KEY、DASHSCOPE_API_KEY 等）。
    - 自动检测已设置的变量，构建对应的提供商配置。

    环境变量优先级：
    1. OPENAI_API_KEY：业界通用标准，设置后默认 provider 为 openai。
    2. DASHSCOPE_API_KEY：阿里云 DashScope，国内常用。
    3. ANTHROPIC_API_KEY：Anthropic Claude。

    兼容特定厂商变量：
    - OPENAI_BASE_URL / OPENAI_API_BASE：两者都支持，前者是新标准。
    - DASHSCOPE_BASE_URL：可选，未设置时使用默认 URL。

    Returns:
        从环境变量提取的配置字典（可能为空）。
    """
    # 加载 .env 文件到 os.environ
    # 如果 .env 不存在，load_dotenv 静默失败，不影响后续逻辑
    load_dotenv()

    config: dict[str, Any] = {}

    # 模型配置：MODEL_NAME 是项目约定的环境变量名
    model_name = os.environ.get("MODEL_NAME")
    if model_name:
        config["model"] = {"name": model_name}

    # 如果设置了通用的 OPENAI_API_KEY，默认 provider 设为 openai
    # 这是业界惯例：OPENAI_API_KEY 存在时，默认使用 OpenAI 兼容接口
    if os.environ.get("OPENAI_API_KEY"):
        config.setdefault("model", {})["provider"] = "openai"

    # 提供商配置：动态构建已设置凭证的提供商
    providers: dict[str, Any] = {}

    # 优先读取业界通用的 OpenAI 兼容接口变量
    # 支持任何 OpenAI 兼容的 API（包括本地模型、第三方代理等）
    openai_key = os.environ.get("OPENAI_API_KEY")
    # 兼容 OPENAI_BASE_URL（新标准）和 OPENAI_API_BASE（旧标准）
    openai_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
    if openai_key:
        providers["openai"] = {
            "base_url": openai_url,  # None 时使用 SDK 默认值（api.openai.com）
            "api_key_env": "OPENAI_API_KEY",  # 保留变量名，延迟解析
        }

    # 兼容特定厂商的变量
    # DashScope：阿里云灵积，国内常用，有默认 base_url
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    dashscope_url = os.environ.get("DASHSCOPE_BASE_URL")
    if dashscope_key:
        providers["dashscope"] = {
            # 未设置 base_url 时使用 DashScope 兼容接口默认地址
            "base_url": dashscope_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key_env": "DASHSCOPE_API_KEY",
        }

    # Anthropic：Claude API，不需要 base_url（使用 SDK 默认值）
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        providers["anthropic"] = {
            "base_url": None,  # Anthropic SDK 使用默认端点
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

    配置优先级（从高到低）：
    1. 显式参数（命令行/代码调用直接传入）
    2. 项目配置（nanohermes.json 或 --config 指定文件）
    3. 全局配置（~/.nanohermes/config.json）
    4. .env 环境变量（自动检测常见变量）
    5. 代码默认值（Pydantic 模型 default）

    为什么采用这种优先级？
    - 显式参数最高：用户明确指定，应覆盖所有配置。
    - 项目配置次之：团队共享配置，针对特定项目优化。
    - 全局配置再次：个人偏好，跨项目使用。
    - .env 最低：环境相关，便于部署和 CI/CD。

    合并策略：
    - 使用 deep_merge 从低到高逐层合并，高优先级覆盖低优先级。
    - 显式参数通过特殊键（__explicit_api_key__）注入，避免与配置文件冲突。

    Args:
        model: 显式指定模型名称（覆盖所有配置来源）。
        provider: 显式指定提供商（如 "openai"、"dashscope"）。
        api_key: 显式指定 API Key（不写入配置文件，仅本次使用）。
        base_url: 显式指定 Base URL（用于自定义 API 端点）。
        config_file: 显式指定配置文件路径（覆盖默认项目配置）。

    Returns:
        完整的 Config 对象（通过 Pydantic 验证）。

    Raises:
        ValueError: 配置验证失败时抛出，包含具体错误信息。
    """
    # 1. 加载全局配置（用户级偏好）
    # 可能为 None（文件不存在或无效），用 {} 兜底
    global_data = load_json_file(GLOBAL_CONFIG) or {}

    # 2. 加载项目配置
    # 如果传入了 config_file，使用指定路径；否则使用默认 nanohermes.json
    project_path = Path(config_file) if config_file else PROJECT_CONFIG
    project_data = load_json_file(project_path) or {}

    # 3. 加载 .env 默认值
    # 从环境变量自动提取已知配置（MODEL_NAME、*_API_KEY 等）
    env_data = load_env_defaults()

    # 4. 合并配置（优先级：项目 > 全局 > env）
    # deep_merge 确保嵌套配置正确覆盖（如 providers.openai.base_url）
    merged = deep_merge(env_data, global_data)
    merged = deep_merge(merged, project_data)

    # 5. 应用显式参数
    # 使用 setdefault 避免覆盖已存在的嵌套结构
    # 特殊键 __explicit_api_key__ 和 __explicit_base_url__ 用于传递参数值，
    # 这些键不会出现在最终 Config 中，仅在 _resolve_api_key 中读取
    if model:
        merged.setdefault("model", {})["name"] = model
    if provider:
        merged.setdefault("model", {})["provider"] = provider
    if api_key:
        # 存储到 providers 下，避免与模型配置混淆
        merged.setdefault("providers", {})["__explicit_api_key__"] = api_key
    if base_url:
        merged.setdefault("providers", {})["__explicit_base_url__"] = base_url

    # 6. 解析环境变量凭证
    # 将 *_env 字段替换为环境变量实际值（api_key_env 除外）
    merged = resolve_env_credentials(merged)

    # 7. 创建 Config 对象
    # 使用 Pydantic 验证确保配置完整性和类型正确性
    # 验证失败时快速失败，避免后续运行时出现难以调试的错误
    try:
        config = Config.from_dict(merged)
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        raise ValueError(f"配置验证失败: {e}")

    # 8. 验证 API Key
    # 如果未显式传入 api_key，从配置中解析
    # 解析失败不抛异常，仅警告（允许无 key 启动，后续调用时再失败）
    if not api_key:
        api_key = _resolve_api_key(config)
        if not api_key:
            logger.warning("未找到 API Key，请检查 .env 文件或配置中的 api_key_env")

    logger.info(f"配置已加载: model={config.model.provider}/{config.model.name}")
    return config


def _resolve_api_key(config: Config) -> str | None:
    """从配置解析 API Key。

    解析优先级（从高到低）：
    1. 显式传入的 key（__explicit_api_key__）：命令行/代码直接传入。
    2. 提供商配置中的 api_key_env：从配置文件指定的环境变量读取。
    3. 回退到常见环境变量：DASHSCOPE_API_KEY > OPENAI_API_KEY > ANTHROPIC_API_KEY。

    为什么需要多级回退？
    - 用户可能通过不同方式配置 API Key（配置文件、.env、命令行）。
    - 回退机制确保在各种配置场景下都能找到 key。
    - 常见环境变量回退兼容未配置 providers 的简单场景。

    Args:
        config: 已验证的 Config 对象。

    Returns:
        解析后的 API Key，如果未找到则返回 None。
    """
    provider_id = config.model.provider

    # 1. 检查显式传入的 key（最高优先级）
    # 通过 load_config(api_key="...") 传入，仅本次会话有效
    if "__explicit_api_key__" in config.providers:
        return config.providers["__explicit_api_key__"]

    # 2. 从提供商配置获取
    # 配置文件中定义了该 provider 的 api_key_env，从中读取
    provider_cfg = config.providers.get(provider_id)
    if provider_cfg and provider_cfg.api_key_env:
        # api_key_env 存储的是环境变量名，如 "DASHSCOPE_API_KEY"
        return os.environ.get(provider_cfg.api_key_env)

    # 3. 回退：尝试常见环境变量
    # 按项目默认顺序：DashScope（国内默认）> OpenAI（业界标准）> Anthropic
    for env_var in ["DASHSCOPE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        key = os.environ.get(env_var)
        if key:
            return key

    return None


def get_api_key(config: Config) -> str | None:
    """获取解析后的 API Key。

    公开接口，封装 _resolve_api_key 的调用。
    外部模块不应直接调用 _resolve_api_key，通过此函数获取。

    Args:
        config: 已验证的 Config 对象。

    Returns:
        API Key 字符串，未找到则返回 None。
    """
    return _resolve_api_key(config)


def get_base_url(config: Config) -> str | None:
    """获取解析后的 Base URL。

    解析优先级：
    1. 显式传入的 base_url（__explicit_base_url__）。
    2. 提供商配置中的 base_url。
    3. 回退到 provider 注册表中的默认 URL（从 profile 获取）。

    为什么需要 provider 注册表回退？
    - 某些提供商（如 OpenAI、Anthropic）有固定的默认端点。
    - 用户未配置 base_url 时，自动使用 SDK 默认值。
    - 避免配置文件中重复定义标准端点。

    Args:
        config: 已验证的 Config 对象。

    Returns:
        Base URL 字符串，未找到则返回 None（SDK 将使用默认值）。
    """
    provider_id = config.model.provider

    # 1. 检查显式传入的 URL（最高优先级）
    if "__explicit_base_url__" in config.providers:
        return config.providers["__explicit_base_url__"]

    # 2. 从提供商配置获取
    provider_cfg = config.providers.get(provider_id)
    if provider_cfg and provider_cfg.base_url:
        return provider_cfg.base_url

    # 3. 回退到 provider 注册表
    # 从 provider.profile 模块获取内置提供商的默认配置
    # 使用 try-except 避免循环导入和模块未加载时的错误
    try:
        from src.provider.profile import get_provider_profile
        profile = get_provider_profile(provider_id)
        if profile and profile.base_url:
            return profile.base_url
    except Exception:
        # 忽略导入失败或 profile 不存在的情况
        # 这不会导致配置加载失败，仅表示无默认 URL
        pass

    return None
