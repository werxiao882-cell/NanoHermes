"""工具注册表。

本模块实现自注册工具模型，核心设计决策如下：

1. 为什么用 AST 解析扫描工具模块？
   - 传统方案：维护一个硬编码的工具模块列表，每次新增工具都需要修改此文件
   - AST 方案：通过解析 Python 源码的抽象语法树，自动检测哪些文件包含 register_tool() 调用
   - 优势：新增工具只需在对应文件中调用 register_tool()，无需修改注册表代码
   - 边界情况：只检测顶层调用（模块加载时执行），不检测函数内部的调用（避免误判）

2. 为什么用类级别 _tools 字典实现单例？
   - 类变量在所有实例间共享，无需显式创建单例实例
   - 相比模块级全局变量：类变量可以通过子类扩展（虽然当前不需要）
   - 相比 @singleton 装饰器：更简单直观，Python 原生支持
   - 注意：_tools 是可变对象，所有类方法共享同一字典实例

3. 跳过文件列表的维护说明：
   - __init__.py: 包初始化文件，不包含工具注册
   - registry.py: 本文件自身，避免递归导入
   - dispatcher.py: 工具分发器，负责路由而非工具实现
   - toolsets.py: 工具集定义，元数据而非具体工具
   - availability.py: 可用性检查逻辑，辅助模块
   - async_bridge.py: 异步桥接层，基础设施
   - terminal.py: 终端工具因注册逻辑在函数内部，AST 无法检测，需特殊处理

4. 工具自动发现机制：
   - discover_tools() 扫描 src/tools/ 目录下所有 .py 文件
   - 通过 AST 解析判断文件是否包含顶层 register_tool() 调用
   - 动态导入符合条件的模块，触发模块加载时的注册逻辑
   - 这种设计实现了"约定优于配置"：文件名即工具标识

5. 工具注册的策略模式：
   - 每个工具通过 ToolEntry 封装完整元数据
   - handler 是执行策略，check_fn 是可用性检查策略
   - 注册表不关心工具如何实现，只管理注册条目
   - 支持运行时覆盖（后注册覆盖先注册），便于测试和扩展
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ToolEntry:
    """工具注册条目。

    为什么使用 dataclass？
    - 自动生成 __init__、__repr__、__eq__ 等方法
    - 比 namedtuple 更灵活，支持默认值和类型提示
    - 比手动编写类更简洁，减少样板代码

    设计决策：
    - handler 返回字符串：统一工具输出格式，便于下游处理
    - check_fn 可选：不是所有工具都需要可用性检查（如文件工具始终可用）
    - is_async 标记：用于分发器决定如何调用 handler（await 或直接调用）
    - defer_loading 标记：控制工具是否在启动时加载到 LLM 上下文

    Attributes:
        name: 工具的唯一名称（如 "terminal", "read_file"）。
              作为注册表的键，必须全局唯一。
        toolset: 工具所属的工具集名称（如 "terminal", "file"）。
                 用于按功能分组和权限控制。
        schema: OpenAI 格式的工具 schema（name, description, parameters）。
                直接传递给 LLM API，描述工具的功能和参数。
        handler: 工具执行函数，接受 args dict 和可选的 task_id，返回字符串。
                 是工具的核心逻辑，注册表不关心其实现细节。
        check_fn: 可选的可用性检查函数，返回 True/False。
                  用于动态启用/禁用工具（如检查 API Key 是否存在）。
        is_async: handler 是否为异步函数。
                  分发器根据此标记决定调用方式。
        description: 人类可读的工具描述。
                     用于调试、日志和 UI 展示。
        defer_loading: 是否延迟加载。True 时工具不在启动时加载到上下文，
                       只能通过 search_tools 工具动态发现。
    """
    name: str
    toolset: str
    schema: dict[str, Any]
    handler: Callable[..., str]
    check_fn: Callable[[], bool] | None = None
    is_async: bool = False
    description: str = ""
    defer_loading: bool = False


class ToolRegistry:
    """工具注册表单例。

    为什么使用类方法而非实例方法？
    - 类变量 _tools 在所有实例间共享，天然实现单例
    - 无需显式创建实例，直接通过类名调用
    - 避免多个实例导致的状态不一致问题

    管理所有已注册的工具，支持：
    - 按名称注册和查找（O(1) 时间复杂度）
    - 工具名冲突检测（后注册覆盖先注册，记录警告）
    - 按 toolset 过滤获取 schema（用于动态工具集）
    - 列出所有工具（用于调试和监控）

    类变量:
        _tools: 存储 name → ToolEntry 的映射。
                注意：这是类变量，所有类方法共享同一字典。
                可变类变量在类方法中修改会影响所有实例。
    """

    # 类级别字典：所有 ToolRegistry 实例共享同一字典
    # 这是 Python 实现单例的最简方式，无需装饰器或元类
    _tools: dict[str, ToolEntry] = {}

    @classmethod
    def register(cls, entry: ToolEntry) -> None:
        """注册一个工具条目。

        策略模式体现：
        - 注册表不关心工具如何实现，只管理注册条目
        - handler 是执行策略，check_fn 是可用性检查策略
        - 新策略可以随时替换旧策略（通过覆盖注册）

        为什么允许覆盖而非抛出异常？
        1. 测试场景：测试用例可以注册 mock 工具覆盖真实实现
        2. 扩展场景：用户可以自定义工具覆盖默认实现
        3. 热更新：运行时可以动态替换工具实现

        Args:
            entry: 要注册的 ToolEntry 实例。
        """
        if entry.name in cls._tools:
            # 工具名冲突：记录警告并覆盖
            # 这是设计决策：允许覆盖而非阻止，便于测试和扩展
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
        exclude_deferred: bool = False,
    ) -> list[dict[str, Any]]:
        """获取工具 schema 列表（OpenAI 格式）。

        为什么返回 schema 而非 ToolEntry？
        - LLM API 只需要 schema 来理解工具功能
        - 隐藏实现细节（handler、check_fn 等）
        - 减少数据传输量

        过滤策略：
        - toolset_filter 为 None：返回所有工具（默认行为）
        - toolset_filter 为 set：只返回属于这些工具集的工具
        - exclude_deferred 为 True：排除 defer_loading=True 的工具
        - 使用 set 而非 list：O(1) 查找时间复杂度

        Args:
            toolset_filter: 工具集名称集合，只返回属于这些工具集的工具。
                           None 表示返回所有工具的 schema。
            exclude_deferred: 是否排除延迟加载的工具。True 时只返回
                             defer_loading=False 的工具（用于初始上下文）。

        Returns:
            OpenAI 格式的工具 schema 列表。
        """
        schemas = []
        for entry in cls._tools.values():
            if exclude_deferred and entry.defer_loading:
                continue
            if toolset_filter and entry.toolset not in toolset_filter:
                continue
            schemas.append(entry.schema)
        return schemas

    @classmethod
    def get_deferred_tools(cls) -> list[ToolEntry]:
        """获取所有延迟加载的工具条目。

        延迟加载的工具不在启动时加载到 LLM 上下文，
        只能通过 search_tools 工具动态发现。

        Returns:
            defer_loading=True 的 ToolEntry 列表。
        """
        return [entry for entry in cls._tools.values() if entry.defer_loading]

    @classmethod
    def clear(cls) -> None:
        """清除所有注册。仅用于测试。"""
        cls._tools.clear()

    @classmethod
    def init_all_tools(cls) -> None:
        """初始化所有工具模块。

        为什么需要显式导入而非完全依赖 AST 发现？
        - terminal.py 的注册逻辑在函数内部，AST 无法检测顶层调用
        - 某些工具可能有复杂的初始化逻辑，需要显式控制顺序
        - 提供兜底方案：即使 AST 发现失败，也能确保所有工具加载

        显式导入所有工具模块，触发自动注册。
        包括 terminal（需要特殊处理，因为注册在函数内）。

        注意：此方法与 discover_tools() 互斥，不应同时调用。
        - discover_tools()：自动发现，适合开发阶段
        - init_all_tools()：显式控制，适合生产环境
        """
        import importlib

        # 所有工具模块列表
        # 维护说明：新增工具时添加到此列表
        # 如果工具使用顶层 register_tool() 调用，discover_tools() 会自动发现
        # 此列表主要用于 AST 无法检测的场景（如 terminal.py）
        tool_modules = [
            "src.tools.terminal",
            "src.tools.file_tool",
            "src.tools.clarify_tool",
            "src.tools.code_execution_tool",
            "src.tools.cronjob_tool",
            "src.tools.delegation_tool",
            "src.tools.memory_tool",
            "src.tools.session_search_tool",
            "src.tools.skills_tool",
            "src.tools.process_tool",
            "src.tools.todo_tool",
            "src.tools.tool_search",
        ]

        for module_name in tool_modules:
            try:
                importlib.import_module(module_name)
                logger.debug(f"已初始化工具模块: {module_name}")
            except Exception as e:
                # 单个工具初始化失败不影响其他工具
                logger.warning(f"初始化工具模块失败 {module_name}: {e}")

    @classmethod
    def get_tool_categories(cls) -> dict[str, list[str]]:
        """按工具集分类所有已注册的工具。

        为什么需要分类？
        - UI 展示：按功能分组展示工具（如终端、文件、记忆等）
        - 权限控制：按工具集启用/禁用工具
        - 调试监控：快速查看每个工具集包含哪些工具

        返回结构示例：
        {
            "terminal": ["terminal", "run_command"],
            "file": ["read_file", "write_file", "search_files"],
            "memory": ["read_memory", "write_memory"],
        }

        Returns:
            工具集名称到工具名称列表的映射。
        """
        categories: dict[str, list[str]] = {}
        for tool in cls._tools.values():
            category = tool.toolset
            # 如果工具集不存在，初始化为空列表
            if category not in categories:
                categories[category] = []
            categories[category].append(tool.name)
        return categories

    @classmethod
    def get_tool_categories_with_info(cls) -> dict[str, list[dict[str, Any]]]:
        """按工具集分类所有已注册的工具，包含详细信息。

        返回结构示例：
        {
            "terminal": [
                {"name": "terminal", "description": "执行 shell 命令", "defer_loading": False},
                {"name": "process", "description": "后台进程管理", "defer_loading": True},
            ],
        }

        Returns:
            工具集名称到工具信息列表的映射，每个工具包含 name、description、defer_loading。
        """
        categories: dict[str, list[dict[str, Any]]] = {}
        for tool in cls._tools.values():
            category = tool.toolset
            if category not in categories:
                categories[category] = []
            categories[category].append({
                "name": tool.name,
                "description": tool.description or "",
                "defer_loading": tool.defer_loading,
            })
        return categories
        return categories


def register_tool(
    name: str,
    toolset: str,
    schema: dict[str, Any],
    handler: Callable[..., str],
    check_fn: Callable[[], bool] | None = None,
    is_async: bool = False,
    description: str = "",
    defer_loading: bool = False,
) -> None:
    """便捷函数：注册一个工具。

    为什么提供模块级函数而非直接调用 ToolRegistry.register()？
    - 减少导入层级：工具模块只需 from src.tools.registry import register_tool
    - 隐藏实现细节：工具开发者不需要知道 ToolEntry 的存在
    - 统一注册接口：所有工具使用相同的注册方式，便于维护

    使用示例（在工具模块顶层）：
        from src.tools.registry import register_tool

        def my_handler(args, task_id=None):
            return "result"

        register_tool(
            name="my_tool",
            toolset="custom",
            schema={...},
            handler=my_handler,
        )

    Args:
        name: 工具名称。必须唯一，重复注册会覆盖并记录警告。
        toolset: 工具集名称。用于分组和权限控制（如 "terminal", "file"）。
        schema: OpenAI 格式的工具 schema。直接传递给 LLM API。
        handler: 工具执行函数。接受 args dict 和可选 task_id，返回字符串。
        check_fn: 可用性检查函数（可选）。返回 True 表示工具可用。
        is_async: 是否为异步工具。影响分发器的调用方式。
        description: 人类可读描述。用于调试和日志。
        defer_loading: 是否延迟加载。True 时工具不在启动时加载到上下文，
                      只能通过 search_tools 工具动态发现。默认 False。
    """
    entry = ToolEntry(
        name=name,
        toolset=toolset,
        schema=schema,
        handler=handler,
        check_fn=check_fn,
        is_async=is_async,
        description=description,
        defer_loading=defer_loading,
    )
    ToolRegistry.register(entry)


def get_tool(name: str) -> ToolEntry | None:
    """便捷函数：根据名称获取工具。"""
    return ToolRegistry.get_tool(name)


def get_all_tools() -> list[ToolEntry]:
    """便捷函数：获取所有工具。"""
    return ToolRegistry.get_all_tools()


def get_tool_schemas(toolset_filter: set[str] | None = None, exclude_deferred: bool = False) -> list[dict[str, Any]]:
    """便捷函数：获取工具 schema 列表。"""
    return ToolRegistry.get_tool_schemas(toolset_filter, exclude_deferred)


def get_deferred_tools() -> list[ToolEntry]:
    """便捷函数：获取所有延迟加载的工具。"""
    return ToolRegistry.get_deferred_tools()


def discover_tools(tools_dir: str | None = None) -> None:
    """发现并导入工具模块。

    为什么用 AST 解析而非直接导入所有 .py 文件？
    1. 安全性：避免导入包含副作用或错误的文件
    2. 精确性：只导入真正包含工具注册的文件
    3. 性能：减少不必要的模块加载
    4. 可维护性：新增工具无需修改此文件

    AST 解析的设计理由：
    - ast.parse() 将 Python 源码解析为抽象语法树
    - 遍历顶层节点，查找 register_tool() 或 ToolRegistry.register() 调用
    - 只检测顶层调用（模块加载时执行），不检测函数内部调用
    - 边界情况：如果工具在函数内注册（如 terminal.py），AST 无法检测，
      需要手动添加到 tool_modules 列表或使用 init_all_tools()

    动态导入的机制：
    - importlib.util.spec_from_file_location() 创建模块规范
    - importlib.util.module_from_spec() 创建模块对象
    - spec.loader.exec_module() 执行模块代码，触发 register_tool() 调用
    - 这种方式比 importlib.import_module() 更灵活，支持任意路径

    Args:
        tools_dir: 工具目录路径。None 时使用默认路径（src/tools/）。
    """
    import importlib
    import importlib.util
    import ast
    from pathlib import Path

    if tools_dir is None:
        # 使用当前文件所在目录作为默认工具目录
        tools_dir = str(Path(__file__).parent)

    tools_path = Path(tools_dir)
    if not tools_path.is_dir():
        logger.warning(f"工具目录不存在: {tools_dir}")
        return

    # 跳过的文件列表及原因：
    # __init__.py: 包初始化，不包含工具注册
    # registry.py: 本文件自身，避免递归导入
    # dispatcher.py: 工具分发器，负责路由而非工具实现
    # toolsets.py: 工具集定义，元数据而非具体工具
    # availability.py: 可用性检查逻辑，辅助模块
    # async_bridge.py: 异步桥接层，基础设施
    # terminal.py: 终端工具的注册逻辑在函数内部，AST 无法检测
    skip_files = {"__init__.py", "registry.py", "dispatcher.py", "toolsets.py",
                  "availability.py", "async_bridge.py", "terminal.py", "search_tool.py"}

    for py_file in sorted(tools_path.glob("*.py")):
        if py_file.name in skip_files:
            continue
        if py_file.name.startswith("_"):
            # 跳过私有文件（如 _utils.py）
            continue

        # AST 解析检查是否包含顶层 register_tool() 调用
        # 这是"约定优于配置"的核心：文件名即工具标识
        try:
            if _module_registers_tools(py_file):
                # 动态导入模块，触发模块加载时的 register_tool() 调用
                spec = importlib.util.spec_from_file_location(
                    f"src.tools.{py_file.stem}",
                    py_file,
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    logger.debug(f"已导入工具模块: {py_file.stem}")
        except Exception as e:
            # 捕获所有异常，避免单个工具失败影响其他工具
            logger.warning(f"导入工具模块失败 {py_file.name}: {e}")


def _module_registers_tools(filepath: Path) -> bool:
    """使用 AST 解析检查文件是否包含顶层 register_tool() 调用。

    为什么只检测顶层调用？
    - 工具注册通常在模块加载时执行（顶层代码）
    - 函数内部的调用可能是辅助函数，不应触发自动导入
    - 避免误判：如测试文件中的 mock 注册

    AST 解析的步骤：
    1. 读取文件源码
    2. ast.parse() 解析为抽象语法树
    3. ast.iter_child_nodes() 遍历顶层节点（不递归到函数/类内部）
    4. 检查节点是否是表达式（ast.Expr）且值是函数调用（ast.Call）
    5. 判断调用是否是 register_tool() 或 ToolRegistry.register()

    边界情况处理：
    - 文件编码错误：捕获异常，返回 False
    - 语法错误：ast.parse() 抛出 SyntaxError，捕获后返回 False
    - 别名导入：如 from registry import register_tool as reg，无法检测
      （当前约定不使用别名）

    Args:
        filepath: Python 文件路径。

    Returns:
        True 如果文件包含顶层 register_tool() 或 ToolRegistry.register() 调用。
    """
    try:
        # 读取文件源码，指定 UTF-8 编码
        source = filepath.read_text(encoding="utf-8")
        # 解析为抽象语法树
        # filename 参数用于错误报告，实际不影响解析结果
        tree = ast.parse(source, filename=str(filepath))

        # 只遍历顶层节点（模块直接子节点）
        # 不递归到函数、类、if 块内部
        for node in ast.iter_child_nodes(tree):
            # 顶层表达式节点（如函数调用、赋值等）
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                # 检查是否是 register_tool(...) 调用
                # ast.Name 表示简单名称（如 register_tool）
                if isinstance(call.func, ast.Name) and call.func.id == "register_tool":
                    return True
                # 检查是否是 ToolRegistry.register(...) 调用
                # ast.Attribute 表示属性访问（如 ToolRegistry.register）
                if isinstance(call.func, ast.Attribute) and call.func.attr == "register":
                    # 验证属性所属的对象是 ToolRegistry
                    if isinstance(call.func.value, ast.Name) and call.func.value.id == "ToolRegistry":
                        return True
    except Exception:
        # 捕获所有异常（SyntaxError、UnicodeDecodeError 等）
        # 解析失败时保守返回 False，不导入该文件
        pass
    return False
