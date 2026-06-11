"""上下文修改器。

设计参考: Claude Code context modifier system — tools register context
modifications during batch execution, applied after dispatch_batch() completes.

职责:
- 跟踪工具执行期间产生的上下文修改（文件附件、工作目录、环境变量、技能等）
- 在批量工具调用结束后统一应用，返回修改摘要
- 支持自动检测：write_file/patch → 文件附件更新，terminal cd → 工作目录变更

设计决策:
1. 单例模式:
   使用类变量 _instance 而非模块级全局变量，便于测试时重置状态。
   测试中通过 ContextModifier.reset() 清除单例实例。

2. 延迟应用:
   修改在 register() 时仅记录，不立即生效。apply_all() 在
   dispatch_batch() 结束后调用，确保批量执行期间的修改不会
   互相干扰（同一次 batch 中的多次 cd 只取最后一次）。

3. 去重策略:
   同类型 (mod_type) 只保留最后一次注册，覆盖之前的记录。
   这符合直觉：连续两次 cd 命令，只有最终目录有效。

依赖关系:
- 无外部模块依赖（纯标准库）
- 被 dispatcher.py 的 dispatch_batch() 调用
- 可被个别工具（write_file, terminal 等）通过 register() 注册修改
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModifierType(str, Enum):
    """上下文修改类型。

    每个枚举值对应一种上下文修改语义，字符串值用于序列化/日志。
    """

    FILE_ATTACHMENT_UPDATE = "file_attachment_update"
    WORKING_DIRECTORY_CHANGE = "working_directory_change"
    ENVIRONMENT_VARIABLE_CHANGE = "environment_variable_change"
    SKILL_UPDATE = "skill_update"


@dataclass
class ContextModification:
    """单个上下文修改记录。

    Attributes:
        mod_type: 修改类型（见 ModifierType）。
        detail: 修改详情，语义因类型而异：
            - FILE_ATTACHMENT_UPDATE: 被修改的文件路径
            - WORKING_DIRECTORY_CHANGE: 目标目录路径
            - ENVIRONMENT_VARIABLE_CHANGE: "VAR_NAME=new_value" 格式
            - SKILL_UPDATE: 技能名称
        tool_name: 触发此修改的工具名称（如 "write_file", "terminal"）。
    """

    mod_type: ModifierType
    detail: str
    tool_name: str


# ---------------------------------------------------------------------------
# 自动检测规则
# ---------------------------------------------------------------------------

# terminal 工具中 cd 命令的匹配模式
# 支持: cd path, cd /abs/path, cd ../rel, cd ~, cd -, pushd, popd
_CD_PATTERN = re.compile(
    r"^\s*(?P<cmd>cd|pushd|popd)"
    r"(?:\s+(?P<arg>[^\s;|&]+))?"
    r"\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def detect_cd_command(command: str) -> str | None:
    """检测 shell 命令是否为 cd 并返回目标目录。

    支持的格式:
    - cd /absolute/path
    - cd relative/path
    - cd ~
    - cd - (回到上一个目录)
    - cd (无参数 → HOME)
    - pushd / popd（也改变工作目录，但语义更复杂，暂只返回标记）

    Args:
        command: 完整的 shell 命令字符串。

    Returns:
        目标目录路径，如果命令不是 cd 则返回 None。
        注意：这里只做静态检测，不实际执行命令。
    """
    # 多行命令中，只看最后一行（前面的 cd 可能被 ; 或 && 分隔）
    # 实际上我们需要考虑复合命令，为保守起见只检测纯 cd 命令
    command = command.strip()

    # 纯 cd（无参数）→ HOME 目录
    if re.match(r"^\s*cd\s*$", command, re.IGNORECASE):
        return os.path.expanduser("~")

    match = _CD_PATTERN.match(command)
    if match:
        cmd = match.group("cmd").lower()
        arg = match.group("arg")

        if cmd == "cd":
            if arg is None:
                return os.path.expanduser("~")
            if arg == "-":
                # OLDPWD，静态无法确定，返回标记
                return "<previous_directory>"
            return os.path.expanduser(arg)
        elif cmd in ("pushd", "popd"):
            # pushd/popd 改变目录栈，静态分析复杂
            if arg:
                return os.path.expanduser(arg)
            return "<directory_stack_change>"

    return None


# ---------------------------------------------------------------------------
# 工具 → 修改类型映射
# ---------------------------------------------------------------------------

# 这些工具执行成功后应自动注册对应类型的上下文修改
_AUTO_REGISTER_TOOLS: dict[str, ModifierType] = {
    "write_file": ModifierType.FILE_ATTACHMENT_UPDATE,
    "patch": ModifierType.FILE_ATTACHMENT_UPDATE,
}


def get_auto_modifier(tool_name: str, result: Any) -> ContextModification | None:
    """根据工具名称和返回值自动推断上下文修改。

    设计理由:
    与其在每个工具内部手动调用 context_modifier.register()，
    不如在 dispatcher 层统一拦截。这符合单一职责原则 —
    工具只关心自身逻辑，上下文修改由分发器自动追踪。

    Args:
        tool_name: 工具名称。
        result: 工具执行结果（用于提取文件路径等详情）。

    Returns:
        自动生成的 ContextModification，或 None（无自动修改）。
    """
    mod_type = _AUTO_REGISTER_TOOLS.get(tool_name)
    if mod_type is None:
        return None

    if mod_type == ModifierType.FILE_ATTACHMENT_UPDATE:
        # 从结果中提取文件路径
        file_path = _extract_file_path(result)
        if file_path:
            return ContextModification(
                mod_type=mod_type,
                detail=file_path,
                tool_name=tool_name,
            )

    return None


def _extract_file_path(result: Any) -> str | None:
    """从工具返回值中提取文件路径。

    支持格式:
    - 字符串: 直接作为路径
    - 字典: 尝试 result.get("path") 或 result.get("file")
    - JSON 字符串: 解析后递归处理
    """
    if isinstance(result, str):
        # 可能是 JSON 字符串
        import json as _json_mod

        try:
            parsed = _json_mod.loads(result)
            return _extract_file_path(parsed)
        except (_json_mod.JSONDecodeError, ValueError):
            # 纯字符串作为路径
            return result.strip() if result.strip() else None
    elif isinstance(result, dict):
        for key in ("path", "file", "filepath", "file_path"):
            val = result.get(key)
            if val and isinstance(val, str):
                return val.strip()
    return None


# ---------------------------------------------------------------------------
# ContextModifier 单例
# ---------------------------------------------------------------------------


class ContextModifier:
    """上下文修改器单例。

    工作流程:
    1. dispatch_batch() 开始前，调用 clear() 清空待处理修改
    2. 每个工具执行后，dispatcher 调用 register() 或 get_auto_modifier()
       注册上下文修改（同类型覆盖旧记录）
    3. dispatch_batch() 结束后，调用 apply_all() 返回修改摘要
    4. 摘要注入到下一轮 LLM 请求的系统提示中

    线程安全:
    当前实现非线程安全。如果未来需要并发 batch 执行，
    需在 register/clear/apply_all 中加锁。
    """

    _instance: ContextModifier | None = None

    def __init__(self) -> None:
        self._pending: list[ContextModification] = []

    # -- 单例访问 ----------------------------------------------------------

    @classmethod
    def get_instance(cls) -> ContextModifier:
        """获取或创建单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例（仅用于测试）。"""
        cls._instance = None

    # -- 便捷函数（模块级 API）----------------------------------------------

    @classmethod
    def register(
        cls,
        mod_type: ModifierType | str,
        detail: str,
        tool_name: str,
    ) -> None:
        """注册一个上下文修改。

        同类型修改会被覆盖（保留最后一次）。

        Args:
            mod_type: 修改类型（ModifierType 枚举或字符串）。
            detail: 修改详情。
            tool_name: 触发修改的工具名称。
        """
        instance = cls.get_instance()
        if isinstance(mod_type, str):
            mod_type = ModifierType(mod_type)

        # 移除同类型的旧记录
        instance._pending = [
            m for m in instance._pending if m.mod_type != mod_type
        ]
        instance._pending.append(
            ContextModification(
                mod_type=mod_type,
                detail=detail,
                tool_name=tool_name,
            )
        )

    @classmethod
    def clear(cls) -> None:
        """清空所有待处理的上下文修改。

        应在 dispatch_batch() 开始前调用。
        """
        instance = cls.get_instance()
        instance._pending.clear()

    @classmethod
    def apply_all(cls) -> str:
        """应用所有待处理的修改并返回摘要。

        应在 dispatch_batch() 结束后调用。
        摘要格式示例:
            "Context modifications: write_file → file_attachment_update (src/main.py); "
            "terminal → working_directory_change (/home/user/project)"

        Returns:
            人类可读的修改摘要。无修改时返回空字符串。
        """
        instance = cls.get_instance()
        if not instance._pending:
            return ""

        parts: list[str] = []
        for mod in instance._pending:
            parts.append(
                f"{mod.tool_name} → {mod.mod_type.value} ({mod.detail})"
            )

        summary = "Context modifications: " + "; ".join(parts)

        # 执行实际的环境变更（如工作目录切换）
        cls._apply_side_effects(instance._pending)

        # 清空 pending（已应用）
        instance._pending.clear()

        return summary

    @classmethod
    def get_pending(cls) -> list[ContextModification]:
        """返回当前所有待处理的修改（不消费）。

        用于调试和测试。
        """
        return list(cls.get_instance()._pending)

    # -- 内部实现 ----------------------------------------------------------

    @staticmethod
    def _apply_side_effects(mods: list[ContextModification]) -> None:
        """执行修改的副作用（如实际切换工作目录）。

        设计理由:
        register() 只是记录，不立即生效。apply_all() 时才
        执行实际的环境变更，确保批量执行期间环境稳定。

        Args:
            mods: 待应用的修改列表。
        """
        for mod in mods:
            if mod.mod_type == ModifierType.WORKING_DIRECTORY_CHANGE:
                target = mod.detail
                # 跳过特殊标记（无法静态解析的路径）
                if target.startswith("<") and target.endswith(">"):
                    continue
                try:
                    os.chdir(target)
                except OSError as e:
                    # 目录不存在或无权限，记录但不停止
                    import logging

                    logging.getLogger(__name__).warning(
                        "Failed to change directory to %s: %s", target, e
                    )
