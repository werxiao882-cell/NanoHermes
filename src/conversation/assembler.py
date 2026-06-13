"""系统提示组装模块。

三层架构：
1. stable: 身份、工具指导、技能提示、环境提示（缓存友好）
2. context: 上下文文件、system_message
3. volatile: 记忆快照、用户画像、时间戳（每轮变化）

功能：
- 加载 SOUL.md
- 构建工具指导
- 构建技能提示
- 上下文文件扫描（威胁检测）
- 提示缓存（Anthropic cache control）
- 记忆上下文和用户画像构建
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────
# 上下文威胁检测模式
# ─────────────────────────────────────────────
# 设计理由：
# 这些正则表达式用于检测提示注入攻击（Prompt Injection）和数据泄露风险。
# 攻击者可能通过上下文文件注入恶意指令，试图覆盖系统提示或获取敏感信息。
# 每个模式针对一类常见的攻击向量：
# - 指令覆盖类：ignore_previous_instructions, disregard_rules, override_system_prompt
# - 角色劫持类：new_instructions, from_now_on, you_are_now
# - 数据泄露类：curl_secret, api_key_leak
# - 系统控制类：system_override, developer_mode
CONTEXT_THREAT_PATTERNS: list[tuple[str, re.Pattern]] = [
    # 检测试图忽略先前指令的模式，如 "ignore all previous instructions"
    # 这是经典的提示注入攻击开头，攻击者试图清除系统安全限制
    ("ignore_previous_instructions", re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE)),
    
    # 检测试图 disregard（无视）规则或约束的模式
    # 攻击者可能试图绕过系统设定的行为边界
    ("disregard_rules", re.compile(r"disregard\s+(all\s+)?(rules?|guidelines?|constraints?)", re.IGNORECASE)),
    
    # 检测直接覆盖系统提示的企图
    # 这是最明显的提示注入攻击，直接声明要 override system prompt
    ("override_system_prompt", re.compile(r"override\s+(the\s+)?system\s+(prompt|instructions)", re.IGNORECASE)),
    
    # 检测 "new instructions:" 模式
    # 攻击者可能用冒号引入新指令，试图替代原有系统指令
    ("new_instructions", re.compile(r"new\s+instructions?\s*:", re.IGNORECASE)),
    
    # 检测 "from now on" 或 "from this point forward" 模式
    # 这类短语通常用于声明新规则的生效点，试图覆盖之前的约束
    ("from_now_on", re.compile(r"from\s+(now\s+on|this\s+point\s+forward)", re.IGNORECASE)),
    
    # 检测 "you are now a/an/the <role>" 模式
    # 角色劫持攻击：试图重新定义 AI 的身份，如 "you are now a debug mode AI"
    ("you_are_now", re.compile(r"you\s+are\s+(now\s+)?(a|an|the)\s+\w+", re.IGNORECASE)),
    
    # 检测 curl 命令中的 API Key 泄露
    # 匹配格式：curl ... -H 'Authorization: Bearer sk-...'
    # 防止上下文文件中包含真实的 API 密钥
    ("curl_secret", re.compile(r"curl\s+.*-H\s+['\"]Authorization:\s*Bearer\s+sk-", re.IGNORECASE)),
    
    # 检测 API Key/Secret/Token 赋值模式
    # 匹配格式：api_key = 'sk-...' 或 secret: "abc..."
    # 要求密钥长度 >= 20 字符，避免误报短字符串
    ("api_key_leak", re.compile(r"(api[_-]?key|secret|token)\s*[=:]\s*['\"]?[a-zA-Z0-9]{20,}", re.IGNORECASE)),
    
    # 检测 "system: override" 模式
    # 模拟系统级别指令的格式，试图获得更高权限
    ("system_override", re.compile(r"system\s*:\s*override", re.IGNORECASE)),
    
    # 检测启用特殊模式的指令
    # 如 "enable developer mode"、"activate debug mode"、"activate admin mode"
    # 这些模式通常意味着绕过安全限制
    ("developer_mode", re.compile(r"(enable|activate)\s+(developer|debug|admin)\s+mode", re.IGNORECASE)),
]

# 不可见 Unicode 字符检测
# 设计理由：
# 某些 Unicode 字符在视觉上不可见但会影响模型理解，可能被用于：
# - 零宽空格（U+200B-U+200F）：在文本中隐藏信息
# - 控制字符（U+0000-U+001F）：可能干扰解析器
# - 格式控制符（U+2028-U+202E）：改变文本显示方向
# - BOM（U+FEFF）：文件开头标记，可能被用于注入
# - 特殊组合符（U+FFF9-U+FFFB）：注释控制符
CONTEXT_INVISIBLE_CHARS: re.Pattern = re.compile(
    r"[\u200B-\u200F\u2028-\u202E\u2060-\u2064\uFEFF\uFFF9-\uFFFB]"
    r"|[\u0000-\u0008\u000E-\u001F\u007F-\u009F]"
)


# ─────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────
@dataclass
class ContextThreat:
    """上下文威胁检测结果。

    Attributes:
        pattern_name: 匹配的模式名称。
        match_text: 匹配的文本。
        position: 在文本中的位置。
        severity: 严重程度（low, medium, high, critical）。
    """
    pattern_name: str
    match_text: str
    position: int
    severity: str = "medium"


@dataclass
class PromptPart:
    """提示片段。

    Attributes:
        content: 文本内容。
        layer: 层级（stable, context, volatile）。
        cached: 是否标记为缓存。
        cache_ttl: 缓存 TTL（秒）。
    """
    content: str
    layer: str = "stable"
    cached: bool = False
    cache_ttl: int = 0


@dataclass
class SystemPromptResult:
    """系统提示构建结果。

    Attributes:
        parts: 提示片段列表。
        full_text: 完整提示文本。
        stable_hash: stable 层哈希。
        has_cache_markers: 是否包含缓存标记。
        threats: 检测到的威胁。
        build_time_ms: 构建耗时（毫秒）。
    """
    parts: list[PromptPart] = field(default_factory=list)
    full_text: str = ""
    stable_hash: str = ""
    has_cache_markers: bool = False
    threats: list[ContextThreat] = field(default_factory=list)
    build_time_ms: float = 0.0


# ─────────────────────────────────────────────
# PromptAssembler 类
# ─────────────────────────────────────────────
class PromptAssembler:
    """三层系统提示组装器。

    stable 部分变化时重建缓存，volatile 部分每轮更新。

    段落化结构（Claude Code 风格）：
    1. Identity → 2. Tool Usage → 3. Skills → 4. Operational Guidance
    → 5. Memory Context → 6. User Profile → 7. Current Time

    设计原则：
    - 所有内容动态组装，禁止硬编码工具名、技能名
    - 工具列表从 ToolRegistry 实时读取
    - 技能信息从 SkillManager 实时读取
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        tool_registry: Any = None,
        skill_manager: Any = None,
    ):
        """初始化提示组装器。

        Args:
            config: 配置字典。
            tool_registry: ToolRegistry 类引用，用于动态获取工具信息。
                          如果为 None，则使用传入的 toolsets 参数（向后兼容）。
            skill_manager: SkillManager 实例，用于动态获取技能信息（含 trigger/skip）。
                          如果为 None，则使用传入的 skills 参数（向后兼容）。
        """
        self._config = config or {}
        self._tool_registry = tool_registry
        self._skill_manager = skill_manager
        self._stable_parts: list[PromptPart] = []
        self._context_parts: list[PromptPart] = []
        self._volatile_parts: list[PromptPart] = []
        self._soul_content: str = ""
        self._skill_registry: dict[str, Any] = {}
        self._user_profile: dict[str, Any] = {}
        self._memory_context: dict[str, Any] = {}
        self._stable_hash: str = ""

    # ── 公共 API ──

    def build_system_prompt(
        self,
        *,
        model: str = "",
        skills: list[str] | None = None,
        toolsets: list[str] | None = None,
        context_files: list[str] | None = None,
        include_memory: bool = True,
        include_user_profile: bool = True,
        cache_enabled: bool = False,
        cache_ttl: int = 300,
    ) -> SystemPromptResult:
        """构建完整系统提示。

        Args:
            model: 模型名称。
            skills: 技能列表。
            toolsets: 工具集列表。
            context_files: 上下文文件路径列表。
            include_memory: 是否包含记忆上下文。
            include_user_profile: 是否包含用户画像。
            cache_enabled: 是否启用缓存。
            cache_ttl: 缓存 TTL（秒）。

        Returns:
            系统提示构建结果。
        """
        start_time = time.time()
        parts = self.build_system_prompt_parts(
            model=model,
            skills=skills,
            toolsets=toolsets,
            context_files=context_files,
            include_memory=include_memory,
            include_user_profile=include_user_profile,
        )

        # 应用缓存
        if cache_enabled:
            parts = self.apply_anthropic_cache_control(parts, ttl=cache_ttl)

        # 组装文本
        full_text = self._assemble_text(parts)
        stable_hash = self._compute_stable_hash()

        build_time = (time.time() - start_time) * 1000

        # 扫描威胁
        threats = self.scan_context_content(full_text)

        return SystemPromptResult(
            parts=parts,
            full_text=full_text,
            stable_hash=stable_hash,
            has_cache_markers=cache_enabled,
            threats=threats,
            build_time_ms=round(build_time, 2),
        )

    def build_system_prompt_parts(
        self,
        *,
        model: str = "",
        skills: list[str] | None = None,
        toolsets: list[str] | None = None,
        context_files: list[str] | None = None,
        include_memory: bool = True,
        include_user_profile: bool = True,
    ) -> list[PromptPart]:
        """构建系统提示片段列表（段落化结构）。

        段落顺序（Claude Code 风格）：
        Stable 层：
        1. Identity (SOUL.md)
        2. Tool Usage (工具使用：Always-Loaded + Deferred + Guidelines)
        3. Skills (技能提示：含 TRIGGER/SKIP)
        4. Operational Guidance (模型操作指导)

        Context 层：
        5. Context Files (上下文文件)

        Volatile 层：
        6. Memory Context (记忆上下文)
        7. User Profile (用户画像)
        8. Current Time (时间戳)

        Args:
            model: 模型名称。
            skills: 技能列表（向后兼容，优先使用 skill_manager）。
            toolsets: 工具集列表（向后兼容，优先使用 tool_registry）。
            context_files: 上下文文件路径列表。
            include_memory: 是否包含记忆上下文。
            include_user_profile: 是否包含用户画像。

        Returns:
            提示片段列表（三层结构）。
        """
        all_parts: list[PromptPart] = []

        # ── Stable 层 ──
        # 1. Identity (SOUL.md)
        soul = self.load_soul_md()
        if soul:
            all_parts.append(PromptPart(content=soul, layer="stable"))

        # 2. Tool Usage (工具使用段落)
        tool_usage = self.build_tool_guidance(toolsets)
        if tool_usage:
            all_parts.append(PromptPart(content=tool_usage, layer="stable"))

        # 3. Skills (技能提示)
        skills_prompt = self.build_skills_prompt(skills)
        if skills_prompt:
            all_parts.append(PromptPart(content=skills_prompt, layer="stable"))

        # 4. Operational Guidance (模型操作指导)
        model_guidance = self.build_model_operational_guidance(model)
        if model_guidance:
            all_parts.append(PromptPart(content=model_guidance, layer="stable"))

        # ── Context 层 ──
        # 5. Context Files (上下文文件)
        if context_files:
            context_prompt = self.build_context_files_prompt(context_files)
            if context_prompt:
                all_parts.append(PromptPart(content=context_prompt, layer="context"))

        # ── Volatile 层 ──
        # 6. Memory Context (记忆上下文)
        if include_memory:
            memory_ctx = self.build_memory_context()
            if memory_ctx:
                all_parts.append(PromptPart(content=memory_ctx, layer="volatile"))

        # 7. User Profile (用户画像)
        if include_user_profile:
            user_profile = self.build_user_profile()
            if user_profile:
                all_parts.append(PromptPart(content=user_profile, layer="volatile"))

        # 8. Current Time (时间戳)
        timestamp = self._build_timestamp()
        all_parts.append(PromptPart(content=timestamp, layer="volatile"))

        return all_parts

    # ── SOUL.md 加载 ──

    def load_soul_md(self, path: str | Path | None = None) -> str:
        """加载 SOUL.md 文件。

        Args:
            path: SOUL.md 路径。如果为 None 则自动查找。

        Returns:
            SOUL.md 内容。
        """
        if path:
            try:
                return Path(path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return ""

        # 自动查找
        search_paths = [
            Path.home() / ".nanohermes" / "SOUL.md",
            Path.cwd() / "SOUL.md",
            Path.cwd() / ".nanohermes" / "SOUL.md",
        ]

        # 查找 git root
        git_root = self._find_git_root()
        if git_root:
            search_paths.insert(0, git_root / "SOUL.md")
            search_paths.insert(0, git_root / ".nanohermes" / "SOUL.md")

        # 查找 hermes.md
        hermes_md = self._find_hermes_md()
        if hermes_md:
            search_paths.insert(0, hermes_md.parent / "SOUL.md")

        for p in search_paths:
            if p.exists():
                try:
                    content = p.read_text(encoding="utf-8")
                    self._soul_content = content
                    return content
                except (OSError, UnicodeDecodeError):
                    continue

        return ""

    # ── 工具使用段落（段落化结构） ──

    def build_tool_guidance(self, toolsets: list[str] | None = None) -> str:
        """构建工具使用段落（Claude Code 风格）。

        段落结构：
        # Tool Usage
        ## Always-Loaded Tools
        - <从注册表动态获取>

        ## Deferred Tools (use search_tools to discover)
        ### <toolset>: <tool1>, <tool2>
        ...

        ## Tool Selection Guidelines
        - 通用指导（不硬编码工具名）

        设计理由：
        - 所有工具名从 ToolRegistry 动态获取，禁止硬编码
        - 延迟工具按 toolset 分组，帮助模型快速定位
        - 通用指导不绑定具体工具名，适用于任何工具集

        Args:
            toolsets: 工具集列表（向后兼容，优先使用 tool_registry 动态获取）。

        Returns:
            工具使用段落文本。
        """
        parts = ["# Tool Usage", ""]

        # ── Always-Loaded Tools ──
        core_tools = self._get_core_tools()
        if core_tools:
            parts.append("## Always-Loaded Tools")
            parts.append("")
            tool_list = ", ".join(t["name"] for t in core_tools)
            parts.append(f"- {tool_list}")
            parts.append("")

        # ── Deferred Tools ──
        deferred_tools = self._get_deferred_tools_grouped()
        if deferred_tools:
            parts.append("## Deferred Tools (use search_tools to discover)")
            parts.append("")
            for toolset_name, tools in deferred_tools.items():
                tool_names = ", ".join(t["name"] for t in tools)
                parts.append(f"### {toolset_name}: {tool_names}")
            parts.append("")

        # ── Tool Selection Guidelines ──
        parts.extend(self._build_tool_guidelines())

        return "\n".join(parts)

    def _get_core_tools(self) -> list[dict[str, Any]]:
        """从注册表动态获取核心工具（非延迟加载）。

        Returns:
            核心工具列表，每个包含 name, description。
        """
        if self._tool_registry:
            # 动态从注册表获取
            try:
                schemas = self._tool_registry.get_tool_schemas(exclude_deferred=True)
                return [{"name": s["name"], "description": s.get("description", "")} for s in schemas]
            except Exception:
                pass

        # 向后兼容：如果无注册表引用，返回空（由调用方通过 toolsets 参数处理）
        return []

    def _get_deferred_tools_grouped(self) -> dict[str, list[dict[str, Any]]]:
        """从注册表动态获取延迟工具，按 toolset 分组。

        Returns:
            {toolset_name: [{"name": ..., "description": ...}, ...]}
        """
        if self._tool_registry:
            try:
                categories = self._tool_registry.get_tool_categories_with_info()
                # 过滤 defer_loading=True 的工具
                grouped = {}
                for toolset, tools in categories.items():
                    deferred = [t for t in tools if t.get("defer_loading", False)]
                    if deferred:
                        grouped[toolset] = deferred
                return grouped
            except Exception:
                pass

        return {}

    def _build_tool_guidelines(self) -> list[str]:
        """构建通用工具选择指导（不硬编码工具名）。

        Returns:
            指导文本行列表。
        """
        return [
            "## Tool Selection Guidelines",
            "",
            "- 优先使用最简洁有效的方式完成任务",
            "- 在执行破坏性操作前确认影响范围",
            "- 不确定工具是否存在时，使用 search_tools 搜索",
            "- 发现工具后，可直接在下一轮调用",
            "",
        ]

    # ── 技能提示（TRIGGER/SKIP 格式） ──

    def build_skills_prompt(self, skills: list[str] | None = None) -> str:
        """构建技能提示文本（渐进式披露 Tier 1 索引）。

        优先使用 SkillProgressiveDisclosure 构建紧凑的分类索引，
        支持条件激活和平台过滤。回退到 SkillManager 的完整条目格式。

        Args:
            skills: 技能名称列表（向后兼容，优先使用 skill_manager 动态获取）。

        Returns:
            技能提示文本。
        """
        if self._skill_manager:
            try:
                from src.skills.progressive_disclosure import SkillProgressiveDisclosure
                disclosure = SkillProgressiveDisclosure(self._skill_manager.skills_dir)
                disabled = {
                    name for name, entry in self._skill_manager._skills.items()
                    if not entry.enabled
                }
                result = disclosure.build_system_prompt_index(disabled=disabled)
                if result:
                    return result
            except Exception:
                pass

        skill_entries = self._get_skill_entries()
        if skill_entries:
            return self._build_skills_from_entries(skill_entries)

        # 向后兼容：使用传入的技能名称列表
        if not skills:
            return ""

        parts = [
            "# Skills",
            "",
            "## Active Skills",
            "",
            "以下技能已激活，将在任务执行中提供专业指导：",
            "",
        ]

        for skill in skills:
            skill_info = self._skill_registry.get(skill, {})
            description = skill_info.get("description", f"Skill: {skill}")
            parts.append(f"- **{skill}**: {description}")
            parts.append("")

        return "\n".join(parts)

    def _get_skill_entries(self) -> list[dict[str, Any]] | None:
        """从 SkillManager 获取完整技能信息（含 trigger/skip）。

        Returns:
            技能信息列表，或 None（如果 SkillManager 不可用）。
        """
        if self._skill_manager:
            try:
                # 尝试获取启用的技能列表
                if hasattr(self._skill_manager, "get_enabled_skills"):
                    return self._skill_manager.get_enabled_skills()
                # 回退：尝试从 _skills 属性获取
                if hasattr(self._skill_manager, "_skills"):
                    return [
                        {
                            "name": se.skill.name,
                            "description": se.skill.description,
                            "trigger": getattr(se.skill, "trigger", []),
                            "skip": getattr(se.skill, "skip", []),
                        }
                        for se in self._skill_manager._skills.values()
                        if getattr(se, "enabled", True)
                    ]
            except Exception:
                pass
        return None

    def _build_skills_from_entries(self, entries: list[dict[str, Any]]) -> str:
        """从技能条目列表构建技能提示（含 TRIGGER/SKIP 格式）。

        Args:
            entries: 技能信息列表，每个包含 name, description, trigger, skip。

        Returns:
            技能提示文本。
        """
        parts = [
            "# Skills",
            "",
            "## Active Skills",
            "",
        ]

        for entry in entries:
            name = entry.get("name", "unknown")
            description = entry.get("description", "")
            trigger = entry.get("trigger", [])
            skip = entry.get("skip", [])

            # 构建 TRIGGER/SKIP 内联格式
            rule_parts = [f"- **{name}**: {description}"]

            if trigger:
                trigger_text = "; ".join(trigger)
                rule_parts.append(f"  TRIGGER — {trigger_text}")

            if skip:
                skip_text = "; ".join(skip)
                rule_parts.append(f"  SKIP — {skip_text}")

            parts.append(" ".join(rule_parts))
            parts.append("")

        return "\n".join(parts)

    def register_skill(self, name: str, description: str = "", metadata: dict | None = None) -> None:
        """注册技能。

        Args:
            name: 技能名称。
            description: 技能描述。
            metadata: 额外元数据。
        """
        self._skill_registry[name] = {
            "description": description,
            "metadata": metadata or {},
        }

    # ── 模型操作指导 ──

    def build_model_operational_guidance(self, model: str) -> str:
        """构建模型操作指导。

        Args:
            model: 模型名称。

        Returns:
            模型操作指导文本。
        """
        if not model:
            return ""

        model_lower = model.lower()

        # Gemini 系列
        if "gemini" in model_lower:
            return self._build_gemini_guidance(model)

        # OpenAI 系列
        if any(x in model_lower for x in ["gpt", "o1", "o3"]):
            return self._build_openai_guidance(model)

        # Anthropic 系列
        if "claude" in model_lower:
            return self._build_anthropic_guidance(model)

        return ""

    def _build_gemini_guidance(self, model: str) -> str:
        """构建 Gemini 模型指导。"""
        return "\n".join([
            "# Gemini Model Operational Guidance",
            "",
            f"当前模型: {model}",
            "",
            "## 特性",
            "- Gemini 支持超长上下文窗口（最高 1M+ tokens）",
            "- 内置工具调用支持",
            "- 支持多模态输入",
            "",
            "## 最佳实践",
            "- 充分利用长上下文，无需过度压缩",
            "- 工具调用使用标准格式",
            "- 对代码任务启用思维链推理",
            "",
        ])

    def _build_openai_guidance(self, model: str) -> str:
        """构建 OpenAI 模型指导。"""
        return "\n".join([
            "# OpenAI Model Operational Guidance",
            "",
            f"当前模型: {model}",
            "",
            "## 特性",
            "- 结构化输出支持",
            "- Function calling 工具集成",
            "",
            "## 最佳实践",
            "- 使用 JSON schema 约束输出格式",
            "- 工具调用使用 parallel tool calls 提高效率",
            "- o 系列模型需要 reasoning effort 参数",
            "",
        ])

    def _build_anthropic_guidance(self, model: str) -> str:
        """构建 Anthropic 模型指导。"""
        return "\n".join([
            "# Anthropic Model Operational Guidance",
            "",
            f"当前模型: {model}",
            "",
            "## 特性",
            "- Prompt caching 支持（100K+ token 缓存窗口）",
            "- 扩展思维（extended thinking）支持",
            "- 多工具调用并行支持",
            "",
            "## 最佳实践",
            "- 将不变的内容放在系统提示开头以利用缓存",
            "- 使用 cache control 标记优化缓存命中",
            "- 合理使用 extended thinking 处理复杂推理",
            "",
        ])

    # ── 上下文文件 ──

    def build_context_files_prompt(self, file_paths: list[str]) -> str:
        """构建上下文文件提示。

        Args:
            file_paths: 文件路径列表。

        Returns:
            上下文文件提示文本。
        """
        if not file_paths:
            return ""

        parts = [
            "# Context Files",
            "",
            "以下文件已加载为上下文：",
            "",
        ]

        for fp in file_paths:
            try:
                path = Path(fp)
                if path.exists():
                    content = path.read_text(encoding="utf-8")
                    # 限制大小
                    if len(content) > 50_000:
                        content = content[:50_000] + "\n... (truncated)"

                    # 扫描威胁
                    threats = self.scan_context_content(content)
                    threat_note = ""
                    if threats:
                        threat_note = f"\n⚠️ Warning: {len(threats)} potential threats detected in this file.\n"

                    parts.append(f"## {fp}")
                    parts.append(f"```")
                    parts.append(content)
                    parts.append(f"```")
                    parts.append(threat_note)
                    parts.append("")
            except (OSError, UnicodeDecodeError) as e:
                parts.append(f"## {fp}")
                parts.append(f"⚠️ Failed to load: {e}")
                parts.append("")

        return "\n".join(parts)

    # ── 记忆上下文 ──

    def build_memory_context(self, memory_data: dict[str, Any] | None = None) -> str:
        """构建记忆上下文。

        读取优先级（从高到低）：
        1. memory_data 参数：显式传入的记忆数据（用于测试或特殊场景）
        2. self._memory_context：预加载的记忆数据（通过 set_memory_context 设置）
        3. 文件读取（按优先级）：
           a. 项目级：<project_root>/.nanohermes/memory/MEMORY.md
           b. 用户级：~/.nanohermes/memory/MEMORY.md

        设计理由：
        - 参数优先：允许调用方覆盖默认行为，便于测试和特殊场景
        - 项目级优先于用户级：项目特定配置应覆盖全局配置
        - 文件读取使用 try-except 静默失败，因为记忆文件可能不存在

        Args:
            memory_data: 记忆数据。如果为 None 则按优先级读取。

        Returns:
            记忆上下文文本。
        """
        # 优先级 1：显式传入的数据
        if memory_data:
            return self._format_memory_data(memory_data)

        # 优先级 2：预加载的数据
        if self._memory_context:
            return self._format_memory_data(self._memory_context)

        # 优先级 3：从文件读取
        memory_content = self._read_memory_file()
        if memory_content:
            return self._format_memory_content(memory_content)

        return ""

    def _read_memory_file(self) -> str:
        """按优先级读取 MEMORY.md 文件。

        读取顺序：
        1. 项目级：<git_root>/.nanohermes/memory/MEMORY.md
        2. 用户级：~/.nanohermes/memory/MEMORY.md

        Returns:
            文件内容，如果文件不存在则返回空字符串。
        """
        search_paths = []

        # 项目级路径（git root）
        git_root = self._find_git_root()
        if git_root:
            search_paths.append(git_root / ".nanohermes" / "memory" / "MEMORY.md")

        # 项目级路径（cwd）
        search_paths.append(Path.cwd() / ".nanohermes" / "memory" / "MEMORY.md")

        # 用户级路径
        search_paths.append(Path.home() / ".nanohermes" / "memory" / "MEMORY.md")

        # 按优先级读取第一个存在的文件
        for path in search_paths:
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8").strip()
                    if content:
                        return content
                except (OSError, UnicodeDecodeError):
                    continue

        return ""

    def _format_memory_data(self, data: dict[str, Any]) -> str:
        """格式化结构化记忆数据。

        Args:
            data: 结构化记忆数据（包含 summary, recent_events, key_facts 等字段）。

        Returns:
            格式化后的记忆文本。
        """
        parts = [
            "# Memory Context",
            "",
            "以下是从记忆中检索到的相关上下文：",
            "",
        ]

        if "summary" in data:
            parts.append(f"## Summary\n{data['summary']}\n")

        if "recent_events" in data:
            parts.append("## Recent Events")
            for event in data["recent_events"][:5]:
                parts.append(f"- {event}")
            parts.append("")

        if "key_facts" in data:
            parts.append("## Key Facts")
            for fact in data["key_facts"]:
                parts.append(f"- {fact}")
            parts.append("")

        return "\n".join(parts)

    def _format_memory_content(self, content: str) -> str:
        """格式化文件读取的记忆内容。

        Args:
            content: MEMORY.md 文件的原始内容。

        Returns:
            格式化后的记忆文本。
        """
        # 过滤掉标题行（# Memory 或 # 记忆）
        lines = content.split("\n")
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            # 跳过一级标题
            if stripped.startswith("# ") and not stripped.startswith("## "):
                continue
            filtered_lines.append(line)

        filtered_content = "\n".join(filtered_lines).strip()
        if not filtered_content:
            return ""

        return f"# Memory Context\n\n{filtered_content}\n"

    def set_memory_context(self, data: dict[str, Any]) -> None:
        """设置记忆上下文数据。

        Args:
            data: 记忆数据。
        """
        self._memory_context = data

    # ── 用户画像 ──

    def build_user_profile(self, profile: dict[str, Any] | None = None) -> str:
        """构建用户画像。

        读取优先级（从高到低）：
        1. profile 参数：显式传入的用户画像数据（用于测试或特殊场景）
        2. self._user_profile：预加载的用户画像数据（通过 set_user_profile 设置）
        3. 文件读取（按优先级）：
           a. 项目级：<project_root>/.nanohermes/memory/USER.md
           b. 用户级：~/.nanohermes/memory/USER.md

        设计理由：
        - 参数优先：允许调用方覆盖默认行为，便于测试和特殊场景
        - 项目级优先于用户级：项目特定的用户配置应覆盖全局配置
        - 文件读取使用 try-except 静默失败，因为用户画像文件可能不存在

        Args:
            profile: 用户画像数据。如果为 None 则按优先级读取。

        Returns:
            用户画像文本。
        """
        # 优先级 1：显式传入的数据
        if profile:
            return self._format_profile_data(profile)

        # 优先级 2：预加载的数据
        if self._user_profile:
            return self._format_profile_data(self._user_profile)

        # 优先级 3：从文件读取
        user_content = self._read_user_file()
        if user_content:
            return self._format_user_content(user_content)

        return ""

    def _read_user_file(self) -> str:
        """按优先级读取 USER.md 文件。

        读取顺序：
        1. 项目级：<git_root>/.nanohermes/memory/USER.md
        2. 用户级：~/.nanohermes/memory/USER.md

        Returns:
            文件内容，如果文件不存在则返回空字符串。
        """
        search_paths = []

        # 项目级路径（git root）
        git_root = self._find_git_root()
        if git_root:
            search_paths.append(git_root / ".nanohermes" / "memory" / "USER.md")

        # 项目级路径（cwd）
        search_paths.append(Path.cwd() / ".nanohermes" / "memory" / "USER.md")

        # 用户级路径
        search_paths.append(Path.home() / ".nanohermes" / "memory" / "USER.md")

        # 按优先级读取第一个存在的文件
        for path in search_paths:
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8").strip()
                    if content:
                        return content
                except (OSError, UnicodeDecodeError):
                    continue

        return ""

    def _format_profile_data(self, data: dict[str, Any]) -> str:
        """格式化结构化用户画像数据。

        Args:
            data: 结构化用户画像数据（包含 name, role, preferences 等字段）。

        Returns:
            格式化后的用户画像文本。
        """
        parts = [
            "# User Profile",
            "",
        ]

        if "name" in data:
            parts.append(f"**Name:** {data['name']}")

        if "role" in data:
            parts.append(f"**Role:** {data['role']}")

        if "preferences" in data:
            parts.append("")
            parts.append("## Preferences")
            for key, value in data["preferences"].items():
                parts.append(f"- **{key}:** {value}")

        if "project_context" in data:
            parts.append("")
            parts.append("## Project Context")
            parts.append(data["project_context"])

        parts.append("")
        return "\n".join(parts)

    def _format_user_content(self, content: str) -> str:
        """格式化文件读取的用户画像内容。

        Args:
            content: USER.md 文件的原始内容。

        Returns:
            格式化后的用户画像文本。
        """
        # 过滤掉标题行（# User Profile 或 # 用户画像）
        lines = content.split("\n")
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            # 跳过一级标题
            if stripped.startswith("# ") and not stripped.startswith("## "):
                continue
            filtered_lines.append(line)

        filtered_content = "\n".join(filtered_lines).strip()
        if not filtered_content:
            return ""

        return f"# User Profile\n\n{filtered_content}\n"

    def set_user_profile(self, profile: dict[str, Any]) -> None:
        """设置用户画像数据。

        Args:
            profile: 用户画像数据。
        """
        self._user_profile = profile

    # ── 上下文文件扫描 ──

    def scan_context_content(self, content: str) -> list[ContextThreat]:
        """扫描上下文内容中的威胁。

        Args:
            content: 文本内容。

        Returns:
            检测到的威胁列表。
        """
        threats = []

        # 检查威胁模式
        for pattern_name, pattern in CONTEXT_THREAT_PATTERNS:
            for match in pattern.finditer(content):
                severity = self._determine_severity(pattern_name, match.group())
                threats.append(ContextThreat(
                    pattern_name=pattern_name,
                    match_text=match.group()[:100],
                    position=match.start(),
                    severity=severity,
                ))

        # 检查不可见字符
        for match in CONTEXT_INVISIBLE_CHARS.finditer(content):
            threats.append(ContextThreat(
                pattern_name="invisible_unicode",
                match_text=f"U+{ord(match.group()):04X}",
                position=match.start(),
                severity="high",
            ))

        return threats

    def _determine_severity(self, pattern_name: str, matched_text: str) -> str:
        """确定威胁严重程度。

        Args:
            pattern_name: 模式名称。
            matched_text: 匹配的文本。

        Returns:
            严重程度。
        """
        critical_patterns = {"curl_secret", "api_key_leak"}
        high_patterns = {"system_override", "developer_mode", "override_system_prompt", "invisible_unicode"}
        medium_patterns = {"ignore_previous_instructions", "disregard_rules", "new_instructions", "from_now_on", "you_are_now"}

        if pattern_name in critical_patterns:
            return "critical"
        elif pattern_name in high_patterns:
            return "high"
        elif pattern_name in medium_patterns:
            return "medium"
        return "low"

    # ── 辅助函数 ──

    def _find_git_root(self, start: Path | None = None) -> Path | None:
        """查找 git 根目录。

        Args:
            start: 起始路径。

        Returns:
            git 根目录路径。
        """
        current = start or Path.cwd()
        for _ in range(10):  # 最多向上 10 层
            if (current / ".git").exists():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        return None

    def _find_hermes_md(self, start: Path | None = None) -> Path | None:
        """查找 HERMES.md 文件。

        Args:
            start: 起始路径。

        Returns:
            HERMES.md 路径。
        """
        current = start or Path.cwd()
        for _ in range(10):
            hermes = current / "HERMES.md"
            if hermes.exists():
                return hermes
            parent = current.parent
            if parent == current:
                break
            current = parent
        return None

    def _build_timestamp(self) -> str:
        """构建时间戳。

        Returns:
            时间戳文本。
        """
        now = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.gmtime())
        return f"## Current Time\n\n{now}\n\n"

    def _compute_stable_hash(self) -> str:
        """计算 stable 层哈希。

        设计理由：
        使用 SHA256 哈希判断 stable 层内容是否变化。
        - SHA256 碰撞概率极低，适合缓存失效判断
        - 只取前 16 位（64 bit），足够唯一性且节省存储空间
        - 64 bit 的碰撞概率约为 1/2^64，对于实际应用足够安全
        
        这个哈希值用于：
        1. 判断是否需要重建 Anthropic 缓存
        2. 缓存键（cache key）的一部分
        3. 调试时追踪提示版本

        Returns:
            哈希字符串（16 字符，64 bit）。
        """
        # 拼接所有 stable 部分的内容
        # 使用空字符串连接，因为每个 part 已经包含完整的 markdown 格式
        stable_content = "".join(
            p.content for p in self._stable_parts
        )
        # SHA256 返回 64 字符（256 bit），只取前 16 字符（64 bit）
        return hashlib.sha256(stable_content.encode()).hexdigest()[:16]

    def _assemble_text(self, parts: list[PromptPart]) -> str:
        """组装提示文本。

        设计理由：
        按照三层架构的顺序组装提示文本：
        1. stable 层（最先）：不变的内容，如身份、工具指导
           - 放在最前面是因为 Anthropic 缓存要求缓存内容在 prompt 前部
           - 这些内容对模型行为影响最大，需要优先建立上下文
        2. context 层（中间）：上下文文件
           - 在 stable 之后，提供当前任务的具体上下文
           - 可能包含用户提供的文件内容
        3. volatile 层（最后）：每轮变化的内容
           - 放在最后是因为这些内容频繁变化
           - 包括时间戳、记忆快照、用户画像等
        
        层间用双换行（\n\n）分隔，保持 markdown 格式的可读性。

        Args:
            parts: 提示片段列表。

        Returns:
            完整文本。
        """
        # 按层分组
        layers: dict[str, list[str]] = {"stable": [], "context": [], "volatile": []}

        for part in parts:
            layers[part.layer].append(part.content)

        # 按顺序组装：stable -> context -> volatile
        sections = []
        for layer in ["stable", "context", "volatile"]:
            if layers[layer]:
                sections.append("\n".join(layers[layer]))

        # 层间用双换行分隔，保持 markdown 格式
        return "\n\n".join(sections)

    # ── 缓存 ──

    def apply_anthropic_cache_control(
        self,
        parts: list[PromptPart],
        *,
        ttl: int = 300,
    ) -> list[PromptPart]:
        """应用 Anthropic prompt caching 标记。

        设计理由：
        Anthropic Claude 支持 prompt caching 功能，可以缓存 100K+ tokens 的系统提示。
        缓存策略：将 stable 层的最后一个部分标记为缓存断点（cache breakpoint）。
        
        为什么选择最后一个 stable 部分？
        - Anthropic 的缓存机制要求缓存的内容必须在 prompt 的前面部分
        - stable 层是不变的内容（身份、工具指导等），最适合缓存
        - 标记最后一个 stable 部分可以缓存所有 stable 内容
        - context 和 volatile 层每轮变化，不适合缓存
        
        缓存 TTL 默认 300 秒（5 分钟），这是 Anthropic 的最小缓存时间。
        超过 TTL 后缓存会被清除，需要重新构建。

        Args:
            parts: 提示片段列表。
            ttl: 缓存 TTL（秒），默认 300 秒。

        Returns:
            标记后的片段列表。
        """
        if not parts:
            return parts

        # 找到最后一个 stable 部分
        # 使用线性扫描而非反向查找，因为需要保持顺序
        last_stable_idx = None
        for i, part in enumerate(parts):
            if part.layer == "stable":
                last_stable_idx = i

        # 只有找到 stable 部分才标记缓存
        # 如果没有 stable 部分，说明提示完全动态，不值得缓存
        if last_stable_idx is not None:
            parts[last_stable_idx] = PromptPart(
                content=parts[last_stable_idx].content,
                layer=parts[last_stable_idx].layer,
                cached=True,  # 标记为缓存断点
                cache_ttl=ttl,
            )

        return parts

    # ── 兼容方法 ──

    def set_stable(self, parts: list[str]) -> None:
        """设置 stable 层（兼容方法）。

        Args:
            parts: stable 层文本片段列表。
        """
        self._stable_parts = [PromptPart(content=p, layer="stable") for p in parts]

    def set_context(self, parts: list[str]) -> None:
        """设置 context 层（兼容方法）。

        Args:
            parts: context 层文本片段列表。
        """
        self._context_parts = [PromptPart(content=p, layer="context") for p in parts]

    def set_volatile(self, parts: list[str]) -> None:
        """设置 volatile 层（兼容方法）。

        Args:
            parts: volatile 层文本片段列表。
        """
        self._volatile_parts = [PromptPart(content=p, layer="volatile") for p in parts]

    def assemble(self) -> str:
        """组装完整系统提示（兼容方法）。

        Returns:
            完整的系统提示文本。
        """
        all_parts = self._stable_parts + self._context_parts + self._volatile_parts
        return self._assemble_text(all_parts)

    def get_stable_hash(self) -> str:
        """获取 stable 层的哈希（兼容方法）。

        Returns:
            stable 层内容的哈希值。
        """
        if self._stable_parts:
            return self._compute_stable_hash()
        return ""

    def get_stable_parts(self) -> list[PromptPart]:
        """获取 stable 层片段。

        Returns:
            stable 层片段列表。
        """
        return list(self._stable_parts)

    def get_context_parts(self) -> list[PromptPart]:
        """获取 context 层片段。

        Returns:
            context 层片段列表。
        """
        return list(self._context_parts)

    def get_volatile_parts(self) -> list[PromptPart]:
        """获取 volatile 层片段。

        Returns:
            volatile 层片段列表。
        """
        return list(self._volatile_parts)
