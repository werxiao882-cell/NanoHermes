"""工具集定义和解析。

工具集是命名的工具分组，用于：
1. 按平台启用/禁用不同的工具组合
2. 控制发送给 LLM 的工具 schema 数量
3. 限制子 Agent 可访问的工具

解析逻辑：
- enabled_toolsets: 只包含列出的工具集（白名单）
- disabled_toolsets: 排除列出的工具集（黑名单）
- 两者都为空：包含所有工具集
"""

from __future__ import annotations

# ============================================================================
# 工具集定义
# ============================================================================
# 格式：toolset_name → [tool_name1, tool_name2, ...]
#
# 每个工具集代表一组功能相关的工具。平台（CLI、Telegram 等）选择
# 不同的工具集组合来暴露给 Agent。
# ============================================================================
TOOLSETS: dict[str, list[str]] = {
    # 终端工具集：命令执行
    "terminal": ["terminal"],

    # 文件工具集：文件读写、搜索
    "file": ["read_file", "write_file", "search_files"],

    # 搜索工具集：网络搜索
    "search": ["web_search"],

    # 安全工具集：只读操作
    "safe": ["read_file", "search_files", "web_search"],
}

# 旧版工具集名称映射（向后兼容）
# 例如："terminal_tools" → "terminal"
_LEGACY_TOOLSET_MAP: dict[str, str] = {
    "terminal_tools": "terminal",
    "file_tools": "file",
    "search_tools": "search",
    "safe_tools": "safe",
}


def resolve_toolset(
    toolset_name: str,
    enabled_toolsets: list[str] | None = None,
    disabled_toolsets: list[str] | None = None,
) -> set[str]:
    """解析工具集为工具名称集合。

    解析逻辑：
    1. 如果 enabled_toolsets 不为空，只返回这些工具集中的工具
    2. 如果 disabled_toolsets 不为空，返回所有工具集排除禁用的
    3. 如果两者都为空，返回所有工具集中的所有工具

    Args:
        toolset_name: 要解析的工具集名称（或逗号分隔的多个名称）。
        enabled_toolsets: 启用的工具集列表（白名单）。
        disabled_toolsets: 禁用的工具集列表（黑名单）。

    Returns:
        工具名称集合。
    """
    # 处理旧版名称
    toolset_name = _LEGACY_TOOLSET_MAP.get(toolset_name, toolset_name)

    # 获取工具集中的工具名称
    tool_names: set[str] = set()
    for name in toolset_name.split(","):
        name = name.strip()
        name = _LEGACY_TOOLSET_MAP.get(name, name)
        if name in TOOLSETS:
            tool_names.update(TOOLSETS[name])

    return tool_names


def resolve_enabled_toolsets(
    enabled_toolsets: list[str] | None = None,
    disabled_toolsets: list[str] | None = None,
) -> set[str]:
    """解析启用/禁用的工具集为最终的工具名称集合。

    Args:
        enabled_toolsets: 启用的工具集列表。
        disabled_toolsets: 禁用的工具集列表。

    Returns:
        最终的工具名称集合。
    """
    if enabled_toolsets:
        # 白名单模式：只包含启用的
        result: set[str] = set()
        for ts in enabled_toolsets:
            ts = _LEGACY_TOOLSET_MAP.get(ts, ts)
            if ts in TOOLSETS:
                result.update(TOOLSETS[ts])
        return result

    if disabled_toolsets:
        # 黑名单模式：所有工具集排除禁用的
        disabled_set = {_LEGACY_TOOLSET_MAP.get(ts, ts) for ts in disabled_toolsets}
        result = set()
        for ts_name, tools in TOOLSETS.items():
            if ts_name not in disabled_set:
                result.update(tools)
        return result

    # 默认：所有工具
    result = set()
    for tools in TOOLSETS.values():
        result.update(tools)
    return result
