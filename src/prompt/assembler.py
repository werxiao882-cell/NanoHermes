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
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化提示组装器。

        Args:
            config: 配置字典。
        """
        self._config = config or {}
        self._stable_parts: list[PromptPart] = []
        self._context_parts: list[PromptPart] = []
        self._volatile_parts: list[PromptPart] = []
        self._soul_content: str = ""
        self._skill_registry: dict[str, Any] = {}
        self._tool_registry: dict[str, Any] = {}
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
        """构建系统提示片段列表。

        Args:
            model: 模型名称。
            skills: 技能列表。
            toolsets: 工具集列表。
            context_files: 上下文文件路径列表。
            include_memory: 是否包含记忆上下文。
            include_user_profile: 是否包含用户画像。

        Returns:
            提示片段列表（三层结构）。
        """
        all_parts: list[PromptPart] = []

        # ── Stable 层 ──
        # 1. Soul/Identity
        soul = self.load_soul_md()
        if soul:
            all_parts.append(PromptPart(content=soul, layer="stable"))

        # 2. 工具指导
        tool_guidance = self.build_tool_guidance(toolsets)
        if tool_guidance:
            all_parts.append(PromptPart(content=tool_guidance, layer="stable"))

        # 3. 技能提示
        skills_prompt = self.build_skills_prompt(skills)
        if skills_prompt:
            all_parts.append(PromptPart(content=skills_prompt, layer="stable"))

        # 4. 模型操作指导
        model_guidance = self.build_model_operational_guidance(model)
        if model_guidance:
            all_parts.append(PromptPart(content=model_guidance, layer="stable"))

        # ── Context 层 ──
        # 上下文文件
        if context_files:
            context_prompt = self.build_context_files_prompt(context_files)
            if context_prompt:
                all_parts.append(PromptPart(content=context_prompt, layer="context"))

        # ── Volatile 层 ──
        # 记忆上下文
        if include_memory:
            memory_ctx = self.build_memory_context()
            if memory_ctx:
                all_parts.append(PromptPart(content=memory_ctx, layer="volatile"))

        # 用户画像
        if include_user_profile:
            user_profile = self.build_user_profile()
            if user_profile:
                all_parts.append(PromptPart(content=user_profile, layer="volatile"))

        # 时间戳
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

    # ── 工具指导 ──

    def build_tool_guidance(self, toolsets: list[str] | None = None) -> str:
        """构建工具指导文本。

        Args:
            toolsets: 工具集列表。

        Returns:
            工具指导文本。
        """
        if not toolsets:
            toolsets = ["terminal", "file", "memory"]

        guidance_parts = [
            "# Tool Usage Guidelines",
            "",
            "## General Principles",
            "- 优先使用最简洁有效的方式完成任务",
            "- 在执行破坏性操作前确认影响范围",
            "- 合理使用工具缓存避免重复工作",
            "",
        ]

        tool_guidance_map = {
            "terminal": [
                "## Terminal",
                "- 使用 terminal 工具执行 shell 命令",
                "- 避免长时间运行的阻塞命令",
                "- 对不确定的命令先使用 echo 测试",
                "",
            ],
            "file": [
                "## File Operations",
                "- 使用 read_file 读取文件内容",
                "- 使用 write_file 创建或覆盖文件",
                "- 使用 patch 进行增量编辑",
                "- 避免不必要的大文件读写",
                "",
            ],
            "memory": [
                "## Memory",
                "- 使用 memory 工具记录和检索上下文",
                "- 重要信息应持久化到 MEMORY.md",
                "- 定期清理过期的记忆条目",
                "",
            ],
            "delegation": [
                "## Delegation",
                "- 使用 delegate_task 委托子任务",
                "- 为子 Agent 提供清晰的目标和上下文",
                "- 合理使用 leaf 和 orchestrator 角色",
                "",
            ],
            "skills": [
                "## Skills",
                "- 使用 skills 工具加载和使用技能",
                "- 技能提供专业领域知识",
                "- 优先使用已有技能而非从头实现",
                "",
            ],
        }

        for ts in toolsets:
            if ts in tool_guidance_map:
                guidance_parts.extend(tool_guidance_map[ts])

        return "\n".join(guidance_parts)

    # ── 技能提示 ──

    def build_skills_prompt(self, skills: list[str] | None = None) -> str:
        """构建技能提示文本。

        Args:
            skills: 技能名称列表。

        Returns:
            技能提示文本。
        """
        if not skills:
            return ""

        parts = [
            "# Active Skills",
            "",
            "以下技能已激活，将在任务执行中提供专业指导：",
            "",
        ]

        for skill in skills:
            skill_info = self._skill_registry.get(skill, {})
            description = skill_info.get("description", f"Skill: {skill}")
            parts.append(f"## {skill}")
            parts.append(description)
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

        Args:
            memory_data: 记忆数据。如果为 None 则使用内部数据。

        Returns:
            记忆上下文文本。
        """
        data = memory_data or self._memory_context
        if not data:
            return ""

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

    def set_memory_context(self, data: dict[str, Any]) -> None:
        """设置记忆上下文数据。

        Args:
            data: 记忆数据。
        """
        self._memory_context = data

    # ── 用户画像 ──

    def build_user_profile(self, profile: dict[str, Any] | None = None) -> str:
        """构建用户画像。

        Args:
            profile: 用户画像数据。如果为 None 则使用内部数据。

        Returns:
            用户画像文本。
        """
        data = profile or self._user_profile
        if not data:
            return ""

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
