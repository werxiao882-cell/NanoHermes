"""技能预处理：模板变量替换 + 内联 shell 展开。

在 skill_view 加载技能内容时执行预处理：
1. 模板变量替换：${HERMES_SKILL_DIR} → 技能目录路径
2. 内联 shell 展开：!`command` → 命令输出

安全限制：
- shell 命令超时 5 秒
- 禁止危险命令（rm -rf /、mkfs、dd if=/dev/zero）
- 禁止网络请求（curl、wget）
- 输出截断 4000 字符

参考 hermes-agent-ref: agent/skill_preprocessing.py
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATE_RE = re.compile(r"\$\{(HERMES_SKILL_DIR|HERMES_SESSION_ID|HERMES_HOME)\}")
_INLINE_SHELL_RE = re.compile(r"!`([^`\n]+)`")
_MAX_OUTPUT = 4000
_DEFAULT_TIMEOUT = 5

_DANGEROUS_COMMANDS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"mkfs\.",
    r"dd\s+if=/dev/zero",
    r"curl\s",
    r"wget\s",
    r"nc\s+-[el]",
    r"bash\s+-i\s+>&",
]
_DANGEROUS_RE = re.compile("|".join(_DANGEROUS_COMMANDS), re.IGNORECASE)


def substitute_template_vars(
    content: str,
    skill_dir: Path | None = None,
    session_id: str | None = None,
) -> str:
    """替换模板变量。

    支持的变量：
    - ${HERMES_SKILL_DIR}: 技能目录的绝对路径
    - ${HERMES_SESSION_ID}: 当前会话 ID
    - ${HERMES_HOME}: ~/.nanohermes 路径

    未解析的变量保留原样，便于作者调试。

    Args:
        content: SKILL.md 内容。
        skill_dir: 技能目录路径。
        session_id: 当前会话 ID。

    Returns:
        替换后的内容。
    """
    def replacer(match: re.Match) -> str:
        var = match.group(1)
        if var == "HERMES_SKILL_DIR" and skill_dir:
            return str(skill_dir)
        if var == "HERMES_SESSION_ID" and session_id:
            return session_id
        if var == "HERMES_HOME":
            return str(Path.home() / ".nanohermes")
        return match.group(0)

    return _TEMPLATE_RE.sub(replacer, content)


def expand_inline_shell(
    content: str,
    skill_dir: Path | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    """展开内联 shell 命令。

    语法：!`command` → 命令输出

    安全限制：
    - 超时: timeout 秒（默认 5）
    - 禁止危险命令
    - 输出截断 _MAX_OUTPUT 字符

    Args:
        content: SKILL.md 内容。
        skill_dir: 技能目录路径（用作 CWD）。
        timeout: 命令超时秒数。

    Returns:
        展开后的内容。
    """
    if "!`" not in content:
        return content

    def replacer(match: re.Match) -> str:
        command = match.group(1).strip()
        return _run_shell(command, skill_dir, timeout)

    return _INLINE_SHELL_RE.sub(replacer, content)


def _run_shell(command: str, cwd: Path | None, timeout: int) -> str:
    """执行单个 shell 命令。"""
    if _DANGEROUS_RE.search(command):
        return "[Dangerous command blocked]"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
        )
        output = result.stdout.strip() or result.stderr.strip()
        if len(output) > _MAX_OUTPUT:
            output = output[:_MAX_OUTPUT] + "...[truncated]"
        return output
    except subprocess.TimeoutExpired:
        return f"[inline-shell timeout after {timeout}s: {command}]"
    except FileNotFoundError:
        return "[inline-shell error: shell not found]"
    except Exception as e:
        return f"[inline-shell error: {e}]"


def preprocess_skill_content(
    content: str,
    skill_dir: Path | None = None,
    session_id: str | None = None,
) -> str:
    """预处理技能内容（编排函数）。

    依次执行：
    1. 模板变量替换
    2. 内联 shell 展开（默认禁用，需显式启用）

    Args:
        content: SKILL.md 原始内容。
        skill_dir: 技能目录路径。
        session_id: 当前会话 ID。

    Returns:
        预处理后的内容。
    """
    content = substitute_template_vars(content, skill_dir, session_id)
    return content
