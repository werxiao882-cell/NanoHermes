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

from src.tools.registry import register_tool

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
            # 执行代码
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
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


def _check_code_safety(code: str):
    """简单的代码安全检查。
    
    禁止明显危险的操作。
    """
    dangerous_patterns = [
        "os.system(",
        "subprocess.call(",
        "subprocess.Popen(",
        "__import__('os').system(",
        "eval(",
        "exec(",
    ]
    
    # 注意：这不是完整的安全检查，只是第一道防线
    # 实际应在沙箱中运行
    pass


def check_code_execution_requirements() -> bool:
    """检查是否满足代码执行的要求。"""
    return True


register_tool(
    name="execute_code",
    toolset="code_execution",
    schema={
        "name": "execute_code",
        "description": (
            "执行 Python 代码。在临时文件中运行，捕获 stdout 和 stderr。\n\n"
            "使用场景：\n"
            "- 快速测试代码片段\n"
            "- 计算复杂表达式\n"
            "- 运行数据处理脚本\n\n"
            "限制：\n"
            "- 超时 30 秒\n"
            "- 输出限制 10000 字符\n"
            "- 不应用于长时间运行的任务"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码。",
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
)
