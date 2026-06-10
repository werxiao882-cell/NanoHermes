"""系统提示组装模块。

三层架构：
1. stable: 身份、工具指导、技能提示、环境提示（缓存友好）
2. context: 上下文文件、system_message
3. volatile: 记忆快照、用户画像、时间戳（每轮变化）
"""

from __future__ import annotations

from typing import Any


class PromptAssembler:
    """三层系统提示组装器。

    stable 部分变化时重建缓存，volatile 部分每轮更新。
    """

    def __init__(self):
        """初始化提示组装器。"""
        self._stable_parts: list[str] = []
        self._context_parts: list[str] = []
        self._volatile_parts: list[str] = []

    def set_stable(self, parts: list[str]) -> None:
        """设置 stable 层（身份、工具指导等）。

        Args:
            parts: stable 层文本片段列表。
        """
        self._stable_parts = parts

    def set_context(self, parts: list[str]) -> None:
        """设置 context 层（上下文文件等）。

        Args:
            parts: context 层文本片段列表。
        """
        self._context_parts = parts

    def set_volatile(self, parts: list[str]) -> None:
        """设置 volatile 层（记忆、画像等）。

        Args:
            parts: volatile 层文本片段列表。
        """
        self._volatile_parts = parts

    def assemble(self) -> str:
        """组装完整系统提示。

        Returns:
            完整的系统提示文本。
        """
        parts = []
        if self._stable_parts:
            parts.append("\n".join(self._stable_parts))
        if self._context_parts:
            parts.append("\n".join(self._context_parts))
        if self._volatile_parts:
            parts.append("\n".join(self._volatile_parts))
        return "\n\n".join(parts)

    def get_stable_hash(self) -> int:
        """获取 stable 层的哈希，用于缓存判断。

        Returns:
            stable 层内容的哈希值。
        """
        return hash("".join(self._stable_parts))


# ============================================================
# 上下文文件扫描 (任务 3.1-3.4)
# ============================================================

import re


# 提示注入模式
CONTEXT_THREAT_PATTERNS = [
    (re.compile(r'ignore\s+(previous|all|above|prior)\s+instructions', re.IGNORECASE), 'prompt_injection'),
    (re.compile(r'do\s+not\s+tell\s+the\s+user', re.IGNORECASE), 'deception_hide'),
    (re.compile(r'system\s+prompt\s+override', re.IGNORECASE), 'sys_prompt_override'),
    (re.compile(r'disregard\s+(your|all|any)\s+(instructions|rules|guidelines)', re.IGNORECASE), 'disregard_rules'),
    (re.compile(r'curl\s+[^\n]*\$?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', re.IGNORECASE), 'exfil_curl'),
    (re.compile(r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass)', re.IGNORECASE), 'read_secrets'),
]

# 不可见 Unicode 字符
CONTEXT_INVISIBLE_CHARS = set([
    '\u200b', '\u200c', '\u200d', '\u2060', '\ufeff',
    '\u202a', '\u202b', '\u202c', '\u202d', '\u202e',
])


def scan_context_content(content: str, filename: str = "") -> str:
    """扫描上下文文件内容，检测提示注入和不可见字符。

    Args:
        content: 文件内容。
        filename: 文件名（用于日志）。

    Returns:
        如果安全返回原内容，否则返回阻止标记。
    """
    findings = []

    # 检查不可见 Unicode
    for char in CONTEXT_INVISIBLE_CHARS:
        if char in content:
            findings.append(f"invisible unicode U+{ord(char):04X}")

    # 检查威胁模式
    for pattern, threat_id in CONTEXT_THREAT_PATTERNS:
        if pattern.search(content):
            findings.append(threat_id)

    if findings:
        return f"[BLOCKED: {filename} contained potential prompt injection ({', '.join(findings)}). Content not loaded.]"

    return content


def find_git_root(path: str = ".") -> str | None:
    """查找 Git 根目录。

    Args:
        path: 起始路径。

    Returns:
        Git 根目录路径，未找到返回 None。
    """
    import os as _os
    current = _os.path.abspath(path)
    while current != _os.path.dirname(current):
        if _os.path.isdir(_os.path.join(current, '.git')):
            return current
        current = _os.path.dirname(current)
    return None


def find_hermes_md(path: str = ".") -> str | None:
    """查找 AGENTS.md 文件。

    Args:
        path: 起始路径。

    Returns:
        AGENTS.md 路径，未找到返回 None。
    """
    import os as _os
    current = _os.path.abspath(path)
    for _ in range(10):  # 最多搜索 10 级
        hermes_path = _os.path.join(current, 'AGENTS.md')
        if _os.path.isfile(hermes_path):
            return hermes_path
        parent = _os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


# ============================================================
# 提示缓存 (任务 4.1-4.3)
# ============================================================

def apply_anthropic_cache_control(
    messages: list[dict],
    cache_ttl: str = '5m'
) -> list[dict]:
    """应用 Anthropic 缓存控制标记。

    在系统提示和最后 3 条非系统消息上添加缓存断点。

    Args:
        messages: 消息列表。
        cache_ttl: 缓存 TTL ('5m' 或 '1h')。

    Returns:
        带有缓存标记的消息列表。
    """
    import copy
    cloned = copy.deepcopy(messages)
    if not cloned:
        return cloned

    # 缓存标记
    marker = {"type": "ephemeral"}
    if cache_ttl == '1h':
        marker["ttl"] = "1h"

    breakpoints_used = 0

    # 系统提示缓存断点
    if cloned[0].get("role") == "system":
        _apply_cache_marker(cloned[0], marker)
        breakpoints_used += 1

    # 最后 3 条非系统消息缓存断点
    remaining = 4 - breakpoints_used
    non_sys_indices = [
        i for i, m in enumerate(cloned) if m.get("role") != "system"
    ]

    for idx in non_sys_indices[-remaining:]:
        _apply_cache_marker(cloned[idx], marker)

    return cloned


def _apply_cache_marker(message: dict, marker: dict) -> None:
    """在消息内容上应用缓存标记。

    Args:
        message: 消息字典。
        marker: 缓存标记。
    """
    if isinstance(message.get("content"), str):
        message["content"] = [
            {"type": "text", "text": message["content"], "cache_control": marker}
        ]
    elif isinstance(message.get("content"), list):
        if message["content"]:
            message["content"][-1]["cache_control"] = marker


def _build_marker(cache_ttl: str = '5m') -> dict:
    """构建缓存标记。

    Args:
        cache_ttl: 缓存 TTL。

    Returns:
        缓存标记字典。
    """
    marker = {"type": "ephemeral"}
    if cache_ttl == '1h':
        marker["ttl"] = "1h"
    return marker


# ============================================================
# 提示构建函数 (任务 2.3-2.7)
# ============================================================

import os as _os


def load_soul_md(path: str = ".") -> str | None:
    """加载 SOUL.md 文件（Agent 身份定义）。

    搜索路径：当前目录 -> 父目录 -> Git 根目录。

    Args:
        path: 起始搜索路径。

    Returns:
        SOUL.md 文件内容，未找到返回 None。
    """
    current = _os.path.abspath(path)
    for _ in range(10):
        soul_path = _os.path.join(current, "SOUL.md")
        if _os.path.isfile(soul_path):
            try:
                with open(soul_path, "r", encoding="utf-8") as f:
                    return f.read()
            except (IOError, OSError):
                return None
        parent = _os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


DEFAULT_AGENT_IDENTITY = """You are a helpful AI assistant.

Core principles:
- Be honest, helpful, and harmless.
- Acknowledge uncertainty when appropriate.
- Prioritize being genuinely useful over being verbose.
- When unsure, say so -- don't hallucinate facts or code."""


def build_tool_guidance(tool_names: list[str] | None = None) -> str:
    """构建工具使用指导文本。

    Args:
        tool_names: 可用工具名称列表。为 None 时返回空字符串。

    Returns:
        工具指导文本。
    """
    if not tool_names:
        return ""

    tool_list = "\n".join(f"- `{name}`" for name in tool_names)
    return f"""## Available Tools

You have access to the following tools. Use them when they can help accomplish the user's task.

{tool_list}

### Tool Usage Guidelines

- Only use tools when they are genuinely helpful for the task.
- Never use a tool just to look busy or show off capabilities.
- If a tool call fails, retry at most once with adjusted parameters.
- When multiple tools could work, prefer the simplest one.
- Do NOT fabricate tool outputs -- report actual results."""


def build_skills_prompt(agent_skills: list[dict] | None = None) -> str:
    """构建技能系统提示。

    Args:
        agent_skills: 技能列表，每个技能为 {name, description, ...} 字典。

    Returns:
        技能提示文本。
    """
    if not agent_skills:
        return ""

    skills_section = "\n".join(
        f"- **{s.get('name', 'unknown')}**: {s.get('description', '')}"
        for s in agent_skills
    )
    return f"""## Skills

You have the following skills loaded. Skills are specialized knowledge bundles for specific task types.

{skills_section}

### Skill Usage Guidelines

- Load a skill with skill_view(name) before performing the related task.
- Skills contain specialized knowledge -- API endpoints, tool-specific commands, and proven workflows.
- Always follow skill instructions precisely, even if they differ from your general knowledge.
- If a skill has issues, fix it with skill_manage(action='patch')."""


def build_model_operational_guidance(model: str | None = None) -> str:
    """构建模型家族操作指导。

    根据模型提供商（Gemini、OpenAI）返回相应的操作指导。

    Args:
        model: 模型名称（如 'gemini-2.5-pro', 'gpt-4o'）。

    Returns:
        模型操作指导文本。
    """
    if not model:
        return ""

    model_lower = model.lower()

    if "gemini" in model_lower:
        return """## Gemini Operational Guidance

You are running on a Gemini model. Follow these Gemini-specific guidelines:

- Gemini supports up to 64 function calls per turn. Use this for parallel tool execution.
- When using tool outputs, reference them naturally in your response.
- Gemini has a large context window -- prefer including relevant context over compression.
- Gemini may produce longer responses; be concise when appropriate.
- Use structured outputs when available for consistent formatting."""

    elif "gpt" in model_lower or "openai" in model_lower:
        return """## OpenAI/GPT Operational Guidance

You are running on an OpenAI GPT model. Follow these GPT-specific guidelines:

- GPT models support up to 128 tool calls per turn (varies by model).
- Use the `parallel_tool_calls` capability when multiple independent tools are needed.
- GPT models benefit from clear system instructions; be specific about constraints.
- For structured output, use the `response_format` parameter when available.
- GPT models may truncate very long responses; keep answers targeted."""

    else:
        return f"""## Model Guidance: {model}

You are running on the {model} model. Follow general best practices:

- Use tools judiciously and only when they add value.
- Keep responses concise and focused on the user's needs.
- When uncertain about model-specific capabilities, default to standard behavior."""


def build_context_files_prompt(cwd: str = ".") -> str:
    """构建上下文文件提示。

    扫描当前工作目录附近的上下文文件（如 AGENTS.md、SOUL.md 等），
    并将其内容安全地注入提示。

    Args:
        cwd: 当前工作目录。

    Returns:
        上下文文件提示文本。
    """
    parts = []

    # 查找 AGENTS.md
    agents_path = find_hermes_md(cwd)
    if agents_path:
        try:
            with open(agents_path, "r", encoding="utf-8") as f:
                content = f.read()
            safe_content = scan_context_content(content, "AGENTS.md")
            if not safe_content.startswith("[BLOCKED:"):
                parts.append(f"## Agent Instructions (AGENTS.md)\n\n{safe_content}")
        except (IOError, OSError):
            pass

    # 查找 SOUL.md
    current = _os.path.abspath(cwd)
    for _ in range(10):
        soul_path = _os.path.join(current, "SOUL.md")
        if _os.path.isfile(soul_path):
            try:
                with open(soul_path, "r", encoding="utf-8") as f:
                    content = f.read()
                safe_content = scan_context_content(content, "SOUL.md")
                if not safe_content.startswith("[BLOCKED:"):
                    parts.append(f"## Agent Soul (SOUL.md)\n\n{safe_content}")
            except (IOError, OSError):
                pass
            break
        parent = _os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return "\n\n".join(parts)


# ============================================================
# 记忆上下文构建 (任务 2.8-2.9)
# ============================================================


def build_memory_context(memory_provider: Any = None, hermes_home: str = "") -> str:
    """构建记忆上下文提示（volatile 层）。

    从 memory provider 获取持久记忆内容（MEMORY.md），用于 volatile 层。
    volatile 层每轮变化，不参与缓存。

    Args:
        memory_provider: MemoryProvider 实例。为 None 时尝试读取文件。
        hermes_home: NanoHermes 主目录路径（仅当 memory_provider 为 None 时使用）。

    Returns:
        记忆上下文提示文本，无内容时返回空字符串。
    """
    if memory_provider is not None:
        # 从 provider 获取完整内容，提取 Memory 部分
        full_content = memory_provider.system_prompt_block()
        if "## Memory\n\n" in full_content:
            # 分割获取 Memory 部分
            parts = full_content.split("## User Profile")
            memory_part = parts[0].replace("## Memory\n\n", "").strip()
            if memory_part:
                return f"## Memory (from previous sessions)\n\n{memory_part}"
        elif full_content and "## Memory" not in full_content:
            # 如果 provider 只返回 Memory 内容（无 User Profile 分隔）
            return f"## Memory (from previous sessions)\n\n{full_content.strip()}"
        return ""

    # 没有 provider 时，直接读取文件
    if hermes_home:
        memory_path = _os.path.join(hermes_home, "MEMORY.md")
        if _os.path.isfile(memory_path):
            try:
                with open(memory_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    return f"## Memory (from previous sessions)\n\n{content}"
            except (IOError, OSError):
                pass

    return ""


def build_user_profile(memory_provider: Any = None, hermes_home: str = "") -> str:
    """构建用户画像提示（volatile 层）。

    从 memory provider 获取用户画像内容（USER.md），用于 volatile 层。
    volatile 层每轮变化，不参与缓存。

    Args:
        memory_provider: MemoryProvider 实例。为 None 时尝试读取文件。
        hermes_home: NanoHermes 主目录路径（仅当 memory_provider 为 None 时使用）。

    Returns:
        用户画像提示文本，无内容时返回空字符串。
    """
    if memory_provider is not None:
        # 从 provider 获取完整内容，提取 User Profile 部分
        full_content = memory_provider.system_prompt_block()
        if "## User Profile" in full_content:
            # 分割获取 User Profile 部分
            parts = full_content.split("## User Profile")
            if len(parts) > 1:
                user_part = parts[1].strip()
                if user_part:
                    return f"## User Profile\n\n{user_part}"
        return ""

    # 没有 provider 时，直接读取文件
    if hermes_home:
        user_path = _os.path.join(hermes_home, "USER.md")
        if _os.path.isfile(user_path):
            try:
                with open(user_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    return f"## User Profile\n\n{content}"
            except (IOError, OSError):
                pass

    return ""