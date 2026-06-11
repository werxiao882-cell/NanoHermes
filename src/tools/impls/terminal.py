"""终端工具。

支持本地命令执行，包含：
1. 工作目录设置
2. 超时保护（默认 300 秒）
3. 危险命令检测和审批流
4. stdout/stderr 流式收集

危险命令模式：
- 递归删除：rm -rf, rd /s /q
- 文件系统格式化：mkfs, format, dd
- SQL 破坏性操作：DROP TABLE, DELETE FROM（无 WHERE）
- 系统配置覆盖：> /etc/, > /boot/
- 远程代码执行：curl | sh, wget | bash
- 进程终止：kill -9, pkill, killall
- Fork 炸弹：:(){ :|:& };:
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """命令执行结果。

    Attributes:
        stdout: 标准输出内容。
        stderr: 标准错误内容。
        exit_code: 进程退出码。
        timed_out: 是否超时。
    """
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False


# ============================================================================
# 危险命令模式
# ============================================================================
# 格式：(正则表达式, 描述)
# 命令执行前逐一匹配，命中则返回审批请求而非执行
# ============================================================================
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*)\b", "递归删除 (rm -rf)"),
    (r"rd\s+/s\s+/q", "递归删除 (Windows rd /s /q)"),
    (r"mkfs\b", "文件系统格式化 (mkfs)"),
    (r"format\s+[A-Z]:", "磁盘格式化 (Windows format)"),
    (r"\bdd\b", "底层磁盘写入 (dd)"),
    (r"DROP\s+TABLE\b", "SQL 删除表 (DROP TABLE)"),
    (r"DELETE\s+FROM\b(?!.+\bWHERE\b)", "SQL 删除记录无 WHERE (DELETE FROM)"),
    (r">\s*/etc/", "覆盖系统配置 (> /etc/)"),
    (r">\s*/boot/", "覆盖启动文件 (> /boot/)"),
    (r"curl\s+.*\|\s*(sh|bash|zsh)", "远程代码执行 (curl | sh)"),
    (r"wget\s+.*\|\s*(sh|bash|zsh)", "远程代码执行 (wget | sh)"),
    (r"kill\s+-9\b", "强制终止进程 (kill -9)"),
    (r"pkill\b", "批量终止进程 (pkill)"),
    (r"killall\b", "批量终止进程 (killall)"),
    (r":\(\)\s*\{\s*:\|:&\s*\}\s*;", "Fork 炸弹"),
]


class TerminalEnvironment(ABC):
    """终端环境抽象基类。

    定义命令执行的统一接口，支持不同后端（本地、Docker、SSH 等）。
    """

    @abstractmethod
    def execute(
        self,
        command: str,
        cwd: str | None = None,
        timeout: float = 300.0,
    ) -> ExecutionResult:
        """执行命令。

        Args:
            command: 要执行的命令字符串。
            cwd: 工作目录，None 时使用当前目录。
            timeout: 超时时间（秒），默认 300 秒。

        Returns:
            ExecutionResult 包含输出、退出码和超时状态。
        """
        ...


class LocalEnvironment(TerminalEnvironment):
    """本地终端环境实现。

    使用 subprocess.Popen 执行命令，支持：
    - stdout/stderr 流式收集
    - 超时后 kill 进程
    - shell=True 支持管道和重定向
    """

    def execute(
        self,
        command: str,
        cwd: str | None = None,
        timeout: float = 300.0,
    ) -> ExecutionResult:
        """在本地执行命令。

        Args:
            command: 要执行的命令。
            cwd: 工作目录。
            timeout: 超时时间（秒）。

        Returns:
            ExecutionResult 包含执行结果。
        """
        effective_cwd = cwd or os.getcwd()

        try:
            # 显式指定 UTF-8 编码，避免 Windows 默认使用 GBK 导致解码失败
            # errors='replace' 将无法解码的字节替换为 ，防止程序崩溃
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=effective_cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return ExecutionResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=process.returncode or 0,
                    timed_out=False,
                )
            except subprocess.TimeoutExpired:
                # 超时后 kill 进程
                process.kill()
                stdout, stderr = process.communicate()
                return ExecutionResult(
                    stdout=stdout or "",
                    stderr=stderr or "",
                    exit_code=-1,
                    timed_out=True,
                )

        except FileNotFoundError:
            return ExecutionResult(
                stderr=f"命令未找到: {command}",
                exit_code=127,
            )
        except Exception as e:
            return ExecutionResult(
                stderr=f"执行失败: {type(e).__name__}: {e}",
                exit_code=1,
            )


def detect_dangerous_command(command: str) -> tuple[bool, str | None]:
    """检测命令是否匹配危险模式。

    Args:
        command: 要检查的命令字符串。

    Returns:
        (is_dangerous, reason) 元组。
        - is_dangerous: True 表示匹配危险模式。
        - reason: 危险原因描述，如果不危险则为 None。
    """
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, description
    return False, None


def execute_command(
    command: str,
    cwd: str | None = None,
    timeout: float = 300.0,
    env: TerminalEnvironment | None = None,
) -> str:
    """执行命令的入口函数。

    流程：
    1. 检测危险命令
    2. 如果危险，返回审批请求
    3. 否则执行命令并返回结果

    Args:
        command: 要执行的命令。
        cwd: 工作目录。
        timeout: 超时时间（秒）。
        env: 终端环境实例，None 时使用 LocalEnvironment。

    Returns:
        JSON 字符串格式的结果。
    """
    # 步骤 1: 危险命令检测
    is_dangerous, reason = detect_dangerous_command(command)
    if is_dangerous:
        return json.dumps({
            "requires_approval": True,
            "command": command,
            "reason": reason,
        })

    # 步骤 2: 执行命令
    effective_env = env or LocalEnvironment()
    result = effective_env.execute(command, cwd=cwd, timeout=timeout)

    return json.dumps({
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
    })


# ============================================================================
# 注册终端工具
# ============================================================================
def _register_terminal_tool() -> None:
    """注册终端工具到全局注册表。"""
    from src.tools.core.registry import register_tool

    register_tool(
        name="terminal",
        toolset="terminal",
        schema={
            "name": "terminal",
            "description": (
                "Execute shell commands on a Linux environment. Filesystem usually persists between calls.\n\n"
                "Do NOT use cat/head/tail to read files — use read_file instead.\n"
                "Do NOT use grep/rg/find to search — use search_files instead.\n"
                "Do NOT use ls to list directories — use search_files(target='files') instead.\n"
                "Do NOT use sed/awk to edit files — use patch instead.\n"
                "Do NOT use echo/cat heredoc to create files — use write_file instead.\n"
                "Reserve terminal for: builds, installs, git, processes, scripts, network, package managers, and anything that needs a shell.\n\n"
                "Foreground (default): Commands return INSTANTLY when done, even if the timeout is high. "
                "Set timeout=300 for long builds/scripts — you'll still get the result in seconds if it's fast. "
                "Prefer foreground for short commands.\n"
                "Background: Set background=true to get a session_id. "
                "Almost always pair with notify_on_complete=true — bg without notify runs SILENTLY and you have no way to learn it finished "
                "short of calling process(action='poll') yourself. "
                "For servers/watchers, do NOT use shell-level background wrappers (nohup/disown/setsid/trailing '&') in foreground mode. "
                "Use background=true so Hermes can track lifecycle and output.\n"
                "After starting a server, verify readiness with a health check or log signal, then run tests in a separate terminal() call. "
                "Avoid blind sleep loops.\n"
                "Use process(action=\"poll\") for progress checks, process(action=\"wait\") to block until done.\n"
                "Working directory: Use 'workdir' for per-command cwd.\n"
                "PTY mode: Set pty=true for interactive CLI tools (Codex, Claude Code, Python REPL).\n\n"
                "Do NOT use vim/nano/interactive tools without pty=true — they hang without a pseudo-terminal. "
                "Pipe git output to cat if it might page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute on the VM"
                    },
                    "background": {
                        "type": "boolean",
                        "description": "Run the command in the background. Almost always pair with notify_on_complete=true.",
                        "default": False
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Max seconds to wait (default: 180, foreground max: 600). Returns INSTANTLY when command finishes.",
                        "minimum": 1
                    },
                    "workdir": {
                        "type": "string",
                        "description": "Working directory for this command (absolute path). Defaults to the session working directory."
                    },
                    "pty": {
                        "type": "boolean",
                        "description": "Run in pseudo-terminal (PTY) mode for interactive CLI tools like Codex, Claude Code, or Python REPL. Default: false.",
                        "default": False
                    },
                    "notify_on_complete": {
                        "type": "boolean",
                        "description": "When true (and background=true), you'll be automatically notified exactly once when the process finishes.",
                        "default": False
                    },
                },
                "required": ["command"],
            },
        },
        handler=lambda command="", cwd=None, timeout=300.0, task_id=None, **kwargs: execute_command(
            command=command,
            cwd=cwd,
            timeout=timeout,
        ),
        description="执行 shell 命令",
    )


# 模块导入时自动注册
_register_terminal_tool()
