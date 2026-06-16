"""Process 工具：后台进程管理。

管理后台进程的生命周期：
- list: 列出所有活跃进程
- start: 启动后台进程
- stop: 停止进程
- kill: 强制终止进程
- output: 获取进程输出
- status: 查看进程状态

使用 subprocess 模块管理进程。
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from src.tools.core.registry import register_tool

logger = logging.getLogger(__name__)

# 进程注册表（进程 ID -> 进程信息）
_process_registry: dict[str, dict] = {}
_registry_lock = threading.Lock()


def _generate_process_id() -> str:
    """生成唯一的进程 ID。"""
    import uuid
    return str(uuid.uuid4())[:8]


def process(
    action: str = "",
    session_id: str = "",
    data: str = "",
    timeout: int = None,
    offset: int = None,
    limit: int = None,
    task_id: str = None,
    **kwargs,
) -> str:
    """管理后台进程。

    支持的操作：
    - list: 列出所有活跃进程
    - poll: 检查状态和新输出（需要 session_id）
    - log: 获取完整输出（需要 session_id，支持 offset/limit）
    - wait: 阻塞直到完成或超时（需要 session_id，可选 timeout）
    - kill: 强制终止进程（需要 session_id）
    - write: 发送原始 stdin 数据（需要 session_id + data）
    - submit: 发送数据 + 回车（需要 session_id + data）
    - close: 关闭 stdin / 发送 EOF（需要 session_id）
    """
    if not action:
        return json.dumps({
            "status": "error",
            "message": "Action is required. Use: list, poll, log, wait, kill, write, submit, close"
        }, ensure_ascii=False)

    try:
        if action == "list":
            return _list_processes()
        elif action == "poll":
            if not session_id:
                return json.dumps({
                    "status": "error",
                    "message": "session_id is required for 'poll' action."
                }, ensure_ascii=False)
            return _get_process_status(session_id, include_new_output=True)
        elif action == "log":
            if not session_id:
                return json.dumps({
                    "status": "error",
                    "message": "session_id is required for 'log' action."
                }, ensure_ascii=False)
            return _get_process_output(session_id, offset=offset, limit=limit)
        elif action == "wait":
            if not session_id:
                return json.dumps({
                    "status": "error",
                    "message": "session_id is required for 'wait' action."
                }, ensure_ascii=False)
            return _wait_for_process(session_id, timeout=timeout)
        elif action == "kill":
            if not session_id:
                return json.dumps({
                    "status": "error",
                    "message": "session_id is required for 'kill' action."
                }, ensure_ascii=False)
            return _kill_process(session_id)
        elif action == "write":
            if not session_id:
                return json.dumps({
                    "status": "error",
                    "message": "session_id is required for 'write' action."
                }, ensure_ascii=False)
            return _write_to_process(session_id, data, add_newline=False)
        elif action == "submit":
            if not session_id:
                return json.dumps({
                    "status": "error",
                    "message": "session_id is required for 'submit' action."
                }, ensure_ascii=False)
            return _write_to_process(session_id, data, add_newline=True)
        elif action == "close":
            if not session_id:
                return json.dumps({
                    "status": "error",
                    "message": "session_id is required for 'close' action."
                }, ensure_ascii=False)
            return _close_process(session_id)
        else:
            return json.dumps({
                "status": "error",
                "message": f"Unknown action '{action}'. Use: list, poll, log, wait, kill, write, submit, close"
            }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Process tool error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Process operation failed: {str(e)}"
        }, ensure_ascii=False)


def _list_processes() -> str:
    """列出所有活跃进程。"""
    with _registry_lock:
        processes = []
        for sid, info in _process_registry.items():
            proc = info.get("process")
            is_running = proc is not None and proc.poll() is None

            processes.append({
                "session_id": sid,
                "command": info.get("command", ""),
                "status": "running" if is_running else "stopped",
                "started_at": info.get("started_at"),
                "pid": proc.pid if proc else None,
            })

        return json.dumps({
            "status": "success",
            "action": "list",
            "processes": processes,
            "count": len(processes),
            "message": f"Showing {len(processes)} processes."
        }, ensure_ascii=False)


def _start_process(command: str, cwd: str = "") -> str:
    """启动后台进程。"""
    work_dir = Path(cwd) if cwd else Path.cwd()

    try:
        # 显式指定 UTF-8 编码，避免 Windows 默认使用 GBK 导致解码失败
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=work_dir,
        )

        session_id = _generate_process_id()

        with _registry_lock:
            _process_registry[session_id] = {
                "process": proc,
                "command": command,
                "started_at": time.time(),
                "output": [],
            }

        return json.dumps({
            "status": "success",
            "action": "start",
            "session_id": session_id,
            "pid": proc.pid,
            "command": command,
            "message": f"Process started with session_id: {session_id}"
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to start process: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Failed to start process: {str(e)}"
        }, ensure_ascii=False)


def _kill_process(session_id: str) -> str:
    """强制终止进程。"""
    with _registry_lock:
        if session_id not in _process_registry:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' not found."
            }, ensure_ascii=False)

        info = _process_registry[session_id]
        proc = info.get("process")

        if proc is None or proc.poll() is not None:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' is not running."
            }, ensure_ascii=False)

        try:
            proc.kill()
            return json.dumps({
                "status": "success",
                "action": "kill",
                "session_id": session_id,
                "message": f"Process '{session_id}' killed."
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to kill process: {str(e)}"
            }, ensure_ascii=False)


def _get_process_output(session_id: str, offset: int = None, limit: int = None) -> str:
    """获取进程输出，支持分页。

    Args:
        session_id: 进程会话 ID。
        offset: 起始行号（None 表示最后 limit 行）。
        limit: 最大返回行数（默认 200）。
    """
    with _registry_lock:
        if session_id not in _process_registry:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' not found."
            }, ensure_ascii=False)

        info = _process_registry[session_id]
        proc = info.get("process")

        if proc is None:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' has no output."
            }, ensure_ascii=False)

        # 读取新输出（非阻塞）
        output_lines = info.get("output", [])
        if proc.stdout:
            try:
                import select
                # 尝试读取可用输出
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    output_lines.append(line.rstrip())
            except Exception:
                pass

        info["output"] = output_lines
        total_lines = len(output_lines)

        # 分页逻辑
        if limit is None:
            limit = 200

        if offset is None:
            # 返回最后 limit 行
            start = max(0, total_lines - limit)
            end = total_lines
        else:
            start = max(0, offset)
            end = min(start + limit, total_lines)

        page_lines = output_lines[start:end]

        return json.dumps({
            "status": "success",
            "action": "log",
            "session_id": session_id,
            "output": "\n".join(page_lines),
            "total_lines": total_lines,
            "offset": start,
            "limit": limit,
            "has_more": end < total_lines,
            "is_running": proc.poll() is None,
            "message": f"Showing lines {start+1}-{end} of {total_lines}."
        }, ensure_ascii=False)


def _get_process_status(session_id: str, include_new_output: bool = False) -> str:
    """获取进程状态。

    Args:
        session_id: 进程会话 ID。
        include_new_output: 是否同时返回新输出（poll 模式）。
    """
    with _registry_lock:
        if session_id not in _process_registry:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' not found."
            }, ensure_ascii=False)

        info = _process_registry[session_id]
        proc = info.get("process")

        if proc is None:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' not found."
            }, ensure_ascii=False)

        is_running = proc.poll() is None
        exit_code = proc.poll()

        result = {
            "status": "success",
            "action": "poll" if include_new_output else "status",
            "session_id": session_id,
            "command": info.get("command", ""),
            "is_running": is_running,
            "exit_code": exit_code,
            "pid": proc.pid,
            "started_at": info.get("started_at"),
        }

        # poll 模式：同时返回新输出
        if include_new_output and proc and proc.stdout:
            output_lines = info.get("output", [])
            new_lines = []
            try:
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    output_lines.append(line.rstrip())
                    new_lines.append(line.rstrip())
            except Exception:
                pass
            info["output"] = output_lines
            result["new_output"] = new_lines
            result["total_lines"] = len(output_lines)

        result["message"] = f"Process is {'running' if is_running else 'stopped'}."
        return json.dumps(result, ensure_ascii=False)


def _wait_for_process(session_id: str, timeout: int = None) -> str:
    """等待进程完成。

    Args:
        session_id: 进程会话 ID。
        timeout: 最大等待秒数（None 表示无限等待）。
    """
    with _registry_lock:
        if session_id not in _process_registry:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' not found."
            }, ensure_ascii=False)

        info = _process_registry[session_id]
        proc = info.get("process")

        if proc is None:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' not found."
            }, ensure_ascii=False)

    # 在锁外等待，避免阻塞其他操作
    try:
        if timeout:
            proc.wait(timeout=timeout)
        else:
            proc.wait()
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True

    # 收集最终输出
    with _registry_lock:
        info = _process_registry.get(session_id, {})
        output_lines = info.get("output", [])
        if proc.stdout:
            try:
                remaining = proc.stdout.read()
                if remaining:
                    for line in remaining.splitlines():
                        output_lines.append(line)
            except Exception:
                pass
        info["output"] = output_lines

    is_running = proc.poll() is None
    exit_code = proc.poll()

    return json.dumps({
        "status": "success" if not timed_out else "timeout",
        "action": "wait",
        "session_id": session_id,
        "is_running": is_running,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "output": "\n".join(output_lines[-100:]),  # 最后 100 行
        "total_lines": len(output_lines),
        "message": f"Process {'completed' if not timed_out else 'timed out'} with exit code {exit_code}."
    }, ensure_ascii=False)


def _write_to_process(session_id: str, data: str, add_newline: bool = False) -> str:
    """向进程 stdin 写入数据。

    Args:
        session_id: 进程会话 ID。
        data: 要写入的数据。
        add_newline: 是否在末尾添加换行符（submit 模式）。
    """
    with _registry_lock:
        if session_id not in _process_registry:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' not found."
            }, ensure_ascii=False)

        info = _process_registry[session_id]
        proc = info.get("process")

        if proc is None or proc.poll() is not None:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' is not running."
            }, ensure_ascii=False)

        if proc.stdin is None:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' has no stdin."
            }, ensure_ascii=False)

    try:
        write_data = data + "\n" if add_newline else data
        proc.stdin.write(write_data)
        proc.stdin.flush()

        return json.dumps({
            "status": "success",
            "action": "submit" if add_newline else "write",
            "session_id": session_id,
            "bytes_written": len(write_data),
            "message": f"Wrote {len(write_data)} bytes to process stdin."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to write to process: {str(e)}"
        }, ensure_ascii=False)


def _close_process(session_id: str) -> str:
    """关闭进程 stdin（发送 EOF）。"""
    with _registry_lock:
        if session_id not in _process_registry:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' not found."
            }, ensure_ascii=False)

        info = _process_registry[session_id]
        proc = info.get("process")

        if proc is None or proc.poll() is not None:
            return json.dumps({
                "status": "error",
                "message": f"Process '{session_id}' is not running."
            }, ensure_ascii=False)

    try:
        if proc.stdin:
            proc.stdin.close()

        return json.dumps({
            "status": "success",
            "action": "close",
            "session_id": session_id,
            "message": f"Closed stdin for process '{session_id}'."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to close process stdin: {str(e)}"
        }, ensure_ascii=False)


def check_process_requirements() -> bool:
    """Process 工具没有外部要求，始终可用。"""
    return True


register_tool(
    name="process",
    toolset="terminal",
    schema={
        "name": "process",
        "description": (
            "Manage background processes started with terminal(background=true). "
            "Actions: 'list' (show all), 'poll' (check status + new output), 'log' (full output with pagination), "
            "'wait' (block until done or timeout), 'kill' (terminate), 'write' (send raw stdin data without newline), "
            "'submit' (send data + Enter, for answering prompts), 'close' (close stdin/send EOF)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "poll", "log", "wait", "kill", "write", "submit", "close"],
                    "description": "Action to perform on background processes"
                },
                "session_id": {
                    "type": "string",
                    "description": "Process session ID (from terminal background output). Required for all actions except 'list'."
                },
                "data": {
                    "type": "string",
                    "description": "Text to send to process stdin (for 'write' and 'submit' actions)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds to block for 'wait' action. Returns partial output on timeout.",
                    "minimum": 1
                },
                "offset": {
                    "type": "integer",
                    "description": "Line offset for 'log' action (default: last 200 lines)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max lines to return for 'log' action",
                    "minimum": 1
                },
            },
            "required": ["action"],
        },
    },
    handler=process,
    check_fn=check_process_requirements,
    description="后台进程管理",
    defer_loading=True,
)
