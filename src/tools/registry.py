"""工具注册表。

本模块实现自注册工具模型：
1. 每个工具模块在 import 时调用 register_tool() 自动注册
2. 注册表使用 dict 存储，工具名为键，O(1) 查找
3. 支持工具名冲突检测（后注册的覆盖并记录警告）
4. 支持按 toolset 过滤获取工具 schema
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ToolEntry:
    """工具注册条目。

    Attributes:
        name: 工具的唯一名称（如 "terminal", "read_file"）。
        toolset: 工具所属的工具集名称（如 "terminal", "file"）。
        schema: OpenAI 格式的工具 schema（name, description, parameters）。
        handler: 工具执行函数，接受 args dict 和可选的 task_id，返回字符串。
        check_fn: 可选的可用性检查函数，返回 True/False。
        is_async: handler 是否为异步函数。
        description: 人类可读的工具描述。
    """
    name: str
    toolset: str
    schema: dict[str, Any]
    handler: Callable[..., str]
    check_fn: Callable[[], bool] | None = None
    is_async: bool = False
    description: str = ""


class ToolRegistry:
    """工具注册表单例。

    管理所有已注册的工具，支持：
    - 按名称注册和查找
    - 工具名冲突检测
    - 按 toolset 过滤获取 schema
    - 列出所有工具

    类变量:
        _tools: 存储 name → ToolEntry 的映射。
    """

    _tools: dict[str, ToolEntry] = {}

    @classmethod
    def register(cls, entry: ToolEntry) -> None:
        """注册一个工具条目。

        如果工具名已存在，记录警告并覆盖。

        Args:
            entry: 要注册的 ToolEntry 实例。
        """
        if entry.name in cls._tools:
            logger.warning(
                f"工具名冲突: '{entry.name}' 已存在，新注册将覆盖旧注册"
            )
        cls._tools[entry.name] = entry

    @classmethod
    def get_tool(cls, name: str) -> ToolEntry | None:
        """根据工具名获取工具条目。

        Args:
            name: 工具名称。

        Returns:
            对应的 ToolEntry，如果未找到则返回 None。
        """
        return cls._tools.get(name)

    @classmethod
    def get_all_tools(cls) -> list[ToolEntry]:
        """获取所有已注册的工具条目。

        Returns:
            ToolEntry 列表。
        """
        return list(cls._tools.values())

    @classmethod
    def get_tool_schemas(
        cls,
        toolset_filter: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """获取工具 schema 列表（OpenAI 格式）。

        Args:
            toolset_filter: 工具集名称集合，只返回属于这些工具集的工具。
                           None 表示返回所有工具的 schema。

        Returns:
            OpenAI 格式的工具 schema 列表。
        """
        schemas = []
        for entry in cls._tools.values():
            if toolset_filter and entry.toolset not in toolset_filter:
                continue
            schemas.append(entry.schema)
        return schemas

    @classmethod
    def clear(cls) -> None:
        """清除所有注册。仅用于测试。"""
        cls._tools.clear()

    @classmethod
    def init_all_tools(cls) -> None:
        """初始化所有工具模块。

        显式导入所有工具模块，触发自动注册。
        包括 terminal（需要特殊处理，因为注册在函数内）。
        """
        import importlib

        # 所有工具模块列表
        tool_modules = [
            "src.tools.terminal",
            "src.tools.file_tools",
            "src.tools.clarify_tools",
            "src.tools.code_execution_tools",
            "src.tools.cronjob_tools",
            "src.tools.delegation_tools",
            "src.tools.memory_tools",
            "src.tools.session_search_tools",
            "src.tools.skills_tools",
            "src.tools.process_tools",
            "src.tools.todo_tools",
            "src.tools.web_search_tool",
        ]

        for module_name in tool_modules:
            try:
                importlib.import_module(module_name)
                logger.debug(f"已初始化工具模块: {module_name}")
            except Exception as e:
                logger.warning(f"初始化工具模块失败 {module_name}: {e}")

    @classmethod
    def get_tool_categories(cls) -> dict[str, list[str]]:
        """按工具集分类所有已注册的工具。

        Returns:
            工具集名称到工具名称列表的映射。
        """
        categories: dict[str, list[str]] = {}
        for tool in cls._tools.values():
            category = tool.toolset
            if category not in categories:
                categories[category] = []
            categories[category].append(tool.name)
        return categories


def register_tool(
    name: str,
    toolset: str,
    schema: dict[str, Any],
    handler: Callable[..., str],
    check_fn: Callable[[], bool] | None = None,
    is_async: bool = False,
    description: str = "",
) -> None:
    """便捷函数：注册一个工具。

    Args:
        name: 工具名称。
        toolset: 工具集名称。
        schema: OpenAI 格式的工具 schema。
        handler: 工具执行函数。
        check_fn: 可用性检查函数（可选）。
        is_async: 是否为异步工具。
        description: 人类可读描述。
    """
    entry = ToolEntry(
        name=name,
        toolset=toolset,
        schema=schema,
        handler=handler,
        check_fn=check_fn,
        is_async=is_async,
        description=description,
    )
    ToolRegistry.register(entry)


def get_tool(name: str) -> ToolEntry | None:
    """便捷函数：根据名称获取工具。"""
    return ToolRegistry.get_tool(name)


def get_all_tools() -> list[ToolEntry]:
    """便捷函数：获取所有工具。"""
    return ToolRegistry.get_all_tools()


def get_tool_schemas(toolset_filter: set[str] | None = None) -> list[dict[str, Any]]:
    """便捷函数：获取工具 schema 列表。"""
    return ToolRegistry.get_tool_schemas(toolset_filter)


def discover_tools(tools_dir: str | None = None) -> None:
    """发现并导入工具模块。

    扫描指定目录（默认 src/tools/），查找包含 register_tool() 调用的
    Python 文件，并动态导入它们以触发自动注册。

    Args:
        tools_dir: 工具目录路径。None 时使用默认路径。
    """
    import importlib
    import importlib.util
    import ast
    from pathlib import Path

    if tools_dir is None:
        tools_dir = str(Path(__file__).parent)

    tools_path = Path(tools_dir)
    if not tools_path.is_dir():
        logger.warning(f"工具目录不存在: {tools_dir}")
        return

    # 跳过的文件
    skip_files = {"__init__.py", "registry.py", "dispatcher.py", "toolsets.py",
                  "availability.py", "async_bridge.py", "terminal.py"}

    for py_file in sorted(tools_path.glob("*.py")):
        if py_file.name in skip_files:
            continue
        if py_file.name.startswith("_"):
            continue

        # AST 解析检查是否包含顶层 register_tool() 调用
        try:
            if _module_registers_tools(py_file):
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(
                    f"src.tools.{py_file.stem}",
                    py_file,
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    logger.debug(f"已导入工具模块: {py_file.stem}")
        except Exception as e:
            logger.warning(f"导入工具模块失败 {py_file.name}: {e}")


def _module_registers_tools(filepath: Path) -> bool:
    """使用 AST 解析检查文件是否包含顶层 register_tool() 调用。

    Args:
        filepath: Python 文件路径。

    Returns:
        True 如果文件包含顶层 register_tool() 调用。
    """
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                # 检查是否是 register_tool(...) 调用
                if isinstance(call.func, ast.Name) and call.func.id == "register_tool":
                    return True
                # 检查是否是 ToolRegistry.register(...) 调用
                if isinstance(call.func, ast.Attribute) and call.func.attr == "register":
                    if isinstance(call.func.value, ast.Name) and call.func.value.id == "ToolRegistry":
                        return True
    except Exception:
        pass
    return False
