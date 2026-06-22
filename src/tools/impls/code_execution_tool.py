"""Code Execution 工具：运行 Python 脚本。

在隔离的 subprocess 中执行 Python 代码。
支持：
- 标准输出捕获
- 标准错误捕获
- 超时控制
- 返回值检查
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from src.tools.core.registry import register_tool

logger = logging.getLogger(__name__)

# 执行超时（秒）
DEFAULT_TIMEOUT = 30
# 最大输出长度（字符）
MAX_OUTPUT_LENGTH = 10000


def execute_code(
    code: str = "",
    language: str = "python",
    timeout: int = DEFAULT_TIMEOUT,
    task_id: str = None,
    **kwargs,
) -> str:
    """执行 Python 代码。
    
    在临时文件中运行代码，捕获 stdout 和 stderr。
    支持超时控制。
    """
    if not code or not code.strip():
        return json.dumps({
            "status": "error",
            "message": "Code is required."
        }, ensure_ascii=False)
    
    if language.lower() not in ("python", "python3"):
        return json.dumps({
            "status": "error",
            "message": f"Unsupported language: {language}. Only Python is supported."
        }, ensure_ascii=False)
    
    try:
        # 安全检查：禁止危险操作
        _check_code_safety(code)
        
        # 写入临时文件
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # 执行代码，显式指定 UTF-8 编码避免 Windows GBK 解码失败
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=Path.cwd(),
            )
            
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            
            # 截断过长输出
            if len(stdout) > MAX_OUTPUT_LENGTH:
                stdout = stdout[:MAX_OUTPUT_LENGTH] + "\n... [output truncated]"
            if len(stderr) > MAX_OUTPUT_LENGTH:
                stderr = stderr[:MAX_OUTPUT_LENGTH] + "\n... [output truncated]"
            
            return json.dumps({
                "status": "success" if result.returncode == 0 else "error",
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "message": "Code execution completed." if result.returncode == 0 else "Code execution failed."
            }, ensure_ascii=False)
            
        finally:
            # 清理临时文件
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
        
    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "message": f"Code execution timed out after {timeout} seconds."
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Code execution error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Code execution failed: {str(e)}"
        }, ensure_ascii=False)


def _check_code_safety(code: str) -> None:
    """代码安全检查：禁止直接调用系统命令和危险函数。

    设计理由：
    - 作为第一道防线，拦截明显危险的操作
    - 匹配到危险模式时抛出 ValueError，阻止执行
    - 使用字符串匹配而非 AST 解析，保持简单高效
    - 不追求完美覆盖（沙箱才是完整方案），但拦截常见攻击向量

    Args:
        code: 待检查的 Python 代码字符串。

    Raises:
        ValueError: 检测到危险操作时抛出。
    """
    dangerous_patterns = [
        ("os.system(", "禁止直接调用 os.system()"),
        ("os.popen(", "禁止直接调用 os.popen()"),
        ("subprocess.call(", "禁止直接调用 subprocess.call()"),
        ("subprocess.Popen(", "禁止直接调用 subprocess.Popen()"),
        ("subprocess.run(", "禁止直接调用 subprocess.run()"),
        ("__import__('os').system(", "禁止通过 __import__ 调用系统命令"),
        ('__import__("os").system(', "禁止通过 __import__ 调用系统命令"),
        ("shutil.rmtree(", "禁止直接调用 shutil.rmtree()"),
    ]

    for pattern, reason in dangerous_patterns:
        if pattern in code:
            raise ValueError(f"安全检查未通过: {reason}。请使用 Hermes 内置工具（terminal, read_file 等）替代。")


def check_code_execution_requirements() -> bool:
    """检查是否满足代码执行的要求。"""
    return True


register_tool(
    name="execute_code",
    toolset="code_execution",
    schema={
        "name": "execute_code",
        "description": (
            "Run a Python script for data processing and computation. Use this when you need to filter/reduce large outputs, "
            "perform conditional branching (if X then Y else Z), run loops (process N files, retry on failure), or apply complex "
            "transformations between tool calls.\n\n"
            "Use normal tool calls instead when: single tool call with no processing, you need to see the full result and apply complex reasoning, or the task requires interactive user input.\n\n"
            "Available: Python stdlib (json, re, math, csv, datetime, collections, pathlib, etc.) and any installed packages in the project's venv.\n"
            "NOT available: Hermes tools cannot be called from within execute_code. Use normal tool calls for file/terminal operations.\n\n"
            "Limits: 30-second default timeout (configurable), 10KB stdout cap.\n\n"
            "Scripts run in the session's working directory with the active venv's python, so project deps (pandas, etc.) and relative paths work like in terminal().\n\n"
            "Print your final result to stdout."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use stdlib for processing and print your final result to stdout.",
                },
                "language": {
                    "type": "string",
                    "description": "编程语言（默认 python）。",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒，默认 30）。",
                },
            },
            "required": ["code"],
        },
    },
    handler=execute_code,
    check_fn=check_code_execution_requirements,
    description="执行 Python 代码",
    defer_loading=True,
)
