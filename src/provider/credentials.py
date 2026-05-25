"""凭证解析链。

本模块负责从环境变量或显式配置中解析 LLM 提供商的 API Key 和基础 URL。

解析优先级：
1. 显式传入的 API Key（最高优先级）
2. 环境变量（按配置的优先级顺序查找）
3. 配置文件中的值
4. 提供商默认值

安全特性：
- API Key 隔离：防止将某个提供商的 Key 发送到错误的端点
  例如：OPENROUTER_API_KEY 不应该发送到自定义端点
- 凭证来源追踪：记录 Key 来自哪里（env/config/explicit），便于调试
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class CredentialResult:
    """凭证解析结果，包含 API Key、基础 URL 和来源信息。

    Attributes:
        api_key: 解析得到的 API Key 字符串。
        base_url: 解析得到的基础 URL，可能为 None（使用 SDK 默认值）。
        source: 凭证来源标识：
            - "env": 来自环境变量
            - "config": 来自配置文件
            - "explicit": 显式传入
            - "default": 使用默认值
    """
    api_key: str
    base_url: str | None
    source: str  # "env", "config", "explicit", "default"


# API Key 与端点的绑定关系，用于防止 Key 泄露到错误的端点。
# 例如：OPENROUTER_API_KEY 只应该发送到包含 "openrouter.ai" 的 URL。
_KEY_ENDPOINT_BINDINGS: dict[str, str] = {
    "OPENROUTER_API_KEY": "openrouter.ai",
    "ANTHROPIC_API_KEY": "api.anthropic.com",
}


def resolve_credentials(
    env_vars: list[str],
    base_url: str | None = None,
    explicit_key: str | None = None,
) -> CredentialResult:
    """按优先级链解析凭证。

    解析顺序：
    1. 如果传入了 explicit_key，直接使用该 Key（最高优先级）
    2. 按 env_vars 列表中的顺序查找环境变量，返回第一个非空值
    3. 如果所有来源都没有找到 Key，抛出 ValueError

    安全检查：
    - 在检查环境变量时，会验证该 Key 是否与目标 base_url 兼容
      例如：如果 base_url 指向自定义端点，不会使用 OPENROUTER_API_KEY

    Args:
        env_vars: 环境变量名称列表，按优先级排序。
            例如：["MY_API_KEY", "FALLBACK_API_KEY"]
        base_url: 目标基础 URL，用于 Key 隔离检查。
        explicit_key: 显式传入的 API Key（最高优先级）。

    Returns:
        CredentialResult，包含解析后的 api_key、base_url 和 source。

    Raises:
        ValueError: 当所有来源都没有找到 API Key 时抛出。
    """
    # 最高优先级：显式传入的 Key
    if explicit_key:
        return CredentialResult(
            api_key=explicit_key,
            base_url=base_url,
            source="explicit",
        )

    # 按优先级顺序检查环境变量
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            # Key 隔离检查：确保该 Key 可以安全地用于目标端点
            # 例如：OPENROUTER_API_KEY 不应该发送到非 OpenRouter 的端点
            if base_url and not _is_key_compatible(var, base_url):
                continue  # Key 与端点不匹配，跳过
            return CredentialResult(
                api_key=value,
                base_url=base_url,
                source="env",
            )

    # 所有来源都没有找到 Key
    raise ValueError(
        f"未找到 API Key。已检查环境变量: {', '.join(env_vars)}。"
        f"请设置其中一个环境变量，或传入 explicit_key 参数。"
    )


def resolve_base_url(
    config_url: str | None = None,
    profile_url: str | None = None,
    env_var: str | None = None,
) -> str | None:
    """按优先级解析基础 URL。

    解析顺序：
    1. 配置文件中显式指定的 URL（最高优先级）
    2. 提供商配置文件中的默认 URL
    3. 环境变量中指定的 URL
    4. 返回 None（使用 SDK 默认值）

    Args:
        config_url: 配置文件中指定的基础 URL。
        profile_url: 提供商配置文件中的默认 URL。
        env_var: 包含基础 URL 的环境变量名称。

    Returns:
        解析后的基础 URL，如果所有来源都没有值则返回 None。
    """
    if config_url:
        return config_url
    if profile_url:
        return profile_url
    if env_var:
        return os.environ.get(env_var)
    return None


def _is_key_compatible(env_var: str, base_url: str) -> bool:
    """检查 API Key 是否与目标端点兼容（防泄露检查）。

    某些 API Key 只能用于特定的端点。例如：
    - OPENROUTER_API_KEY 只能发送到 openrouter.ai
    - ANTHROPIC_API_KEY 只能发送到 api.anthropic.com

    如果 Key 没有绑定关系（不在 _KEY_ENDPOINT_BINDINGS 中），
    则认为它是通用的，可以用于任何端点。

    Args:
        env_var: 环境变量名称（如 "OPENROUTER_API_KEY"）。
        base_url: 目标基础 URL。

    Returns:
        True 表示 Key 可以用于该端点，False 表示不兼容。
    """
    expected_endpoint = _KEY_ENDPOINT_BINDINGS.get(env_var)
    if not expected_endpoint:
        return True  # 没有绑定关系，Key 是通用的
    return expected_endpoint in base_url
