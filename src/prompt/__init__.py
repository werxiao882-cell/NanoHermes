"""系统提示组装模块。

三层架构：stable、context、volatile。
"""

from src.prompt.assembler import (
    PromptAssembler,
    scan_context_content,
    find_git_root,
    find_hermes_md,
    apply_anthropic_cache_control,
    _apply_cache_marker,
    _build_marker,
    load_soul_md,
    DEFAULT_AGENT_IDENTITY,
    build_tool_guidance,
    build_skills_prompt,
    build_model_operational_guidance,
    build_context_files_prompt,
    build_memory_context,
    build_user_profile,
    CONTEXT_THREAT_PATTERNS,
    CONTEXT_INVISIBLE_CHARS,
)

__all__ = [
    "PromptAssembler",
    "scan_context_content",
    "find_git_root",
    "find_hermes_md",
    "apply_anthropic_cache_control",
    "_apply_cache_marker",
    "_build_marker",
    "load_soul_md",
    "DEFAULT_AGENT_IDENTITY",
    "build_tool_guidance",
    "build_skills_prompt",
    "build_model_operational_guidance",
    "build_context_files_prompt",
    "build_memory_context",
    "build_user_profile",
    "CONTEXT_THREAT_PATTERNS",
    "CONTEXT_INVISIBLE_CHARS",
]