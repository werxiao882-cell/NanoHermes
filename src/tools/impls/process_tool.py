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
    command: str = "",
    process_id: str = "",
    cwd: str = "",
    task_id: str = None,
    **kwargs,
) -> str:
    """管理后台进程。
    
    支持的操作：
    - list: 列出所有活跃进程
    - start: 启动后台进程（需要 command）
    - stop: 停止进程（需要 process_id）
    - kill: 强制终止进程（需要 process_id）
    - output: 获取进程输出（需要 process_id）
    - status: 查看进程状态（需要 process_id）
    """
    if not action:
        return json.dumps({
            "status": "error",
            "message": "Action is required. Use: list, start, stop, kill, output, status"
        }, ensure_ascii=False)
    
    try:
        if action == "list":
            return _list_processes()
        elif action == "start" or action == "poll":
            if not command:
                return json.dumps({
                    "status": "error",
                    "message": "Command is required for 'start' action."
                }, ensure_ascii=False)
            return _start_process(command, cwd)
        elif action == "stop" or action == "kill":
            if not process_id:
                return json.dumps({
                    "status": "error",
                    "message": "Process ID is required for 'kill' action."
                }, ensure_ascii=False)
            return _kill_process(process_id)
        elif action == "output" or action == "log":
            if not process_id:
                return json.dumps({
                    "status": "error",
                    "message": "Process ID is required for 'log' action."
                }, ensure_ascii=False)
            return _get_process_output(process_id)
        elif action == "status" or action == "wait":
            if not process_id:
                return json.dumps({
                    "status": "error",
                    "message": "Process ID is required for 'status' action."
                }, ensure_ascii=False)
            return _get_process_status(process_id)
        elif action == "write" or action == "submit":
            if not process_id or not command:
                return json.dumps({
                    "status": "error",
                    "message": "Process ID and data are required for 'write' action."
                }, ensure_ascii=False)
            return _write_to_process(process_id, command, action == "submit")
        elif action == "close":
            if not process_id:
                return json.dumps({
                    "status": "error",
                    "message": "Process ID is required for 'close' action."
                }, ensure_ascii=False)
            return _close_process(process_id)
        else:
            return json.dumps({
                "status": "error",
                "message": f"Unknown action '{action}'. Use: list, start, stop, kill, output, status"
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
        for pid, info in _process_registry.items():
            proc = info.get("process")
            is_running = proc is not None and proc.poll() is None
            
            processes.append({
                "process_id": pid,
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
        
        process_id = _generate_process_id()
        
        with _registry_lock:
            _process_registry[process_id] = {
                "process": proc,
                "command": command,
                "started_at": time.time(),
                "output": [],
            }
        
        return json.dumps({
            "status": "success",
            "action": "start",
            "process_id": process_id,
            "pid": proc.pid,
            "command": command,
            "message": f"Process started with ID {process_id}."
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Failed to start process: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Failed to start process: {str(e)}"
        }, ensure_ascii=False)


def _stop_process(process_id: str) -> str:
    """停止进程（优雅终止）。"""
    with _registry_lock:
        if process_id not in _process_registry:
            return json.dumps({
                "status": "error",
                "message": f"Process {process_id} not found."
            }, ensure_ascii=False)
        
        info = _process_registry[process_id]
        proc = info.get("process")
        
        if proc is None or proc.poll() is not None:
            return json.dumps({
                "status": "error",
                "message": f"Process {process_id} is not running."
            }, ensure_ascii=False)
        
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            
            return json.dumps({
                "status": "success",
                "action": "stop",
                "process_id": process_id,
                "message": f"Process {process_id} stopped."
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to stop process: {str(e)}"
            }, ensure_ascii=False)


def _kill_process(process_id: str) -> str:
    """强制终止进程。"""
    with _registry_lock:
        if process_id not in _process_registry:
            return json.dumps({
                "status": "error",
                "message": f"Process {process_id} not found."
            }, ensure_ascii=False)
        
        info = _process_registry[process_id]
        proc = info.get("process")
        
        if proc is None or proc.poll() is not None:
            return json.dumps({
                "status": "error",
                "message": f"Process {process_id} is not running."
            }, ensure_ascii=False)
        
        try:
            proc.kill()
            return json.dumps({
                "status": "success",
                "action": "kill",
                "process_id": process_id,
                "message": f"Process {process_id} killed."
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to kill process: {str(e)}"
            }, ensure_ascii=False)


def _get_process_output(process_id: str) -> str:
    """获取进程输出。"""
    with _registry_lock:
        if process_id not in _process_registry:
            return json.dumps({
                "status": "error",
                "message": f"Process {process_id} not found."
            }, ensure_ascii=False)
        
        info = _process_registry[process_id]
        proc = info.get("process")
        
        if proc is None:
            return json.dumps({
                "status": "error",
                "message": f"Process {process_id} has no output."
            }, ensure_ascii=False)
        
        # 读取新输出
        output_lines = info.get("output", [])
        if proc.stdout:
            try:
                line = proc.stdout.readline()
                while line:
                    output_lines.append(line.rstrip())
                    line = proc.stdout.readline()
            except Exception:
                pass
        
        info["output"] = output_lines
        
        return json.dumps({
            "status": "success",
            "action": "output",
            "process_id": process_id,
            "output": output_lines[-100:],  # 最近 100 行
            "is_running": proc.poll() is None,
            "message": f"Retrieved {len(output_lines)} lines of output."
        }, ensure_ascii=False)


def _get_process_status(process_id: str) -> str:
    """获取进程状态。"""
    with _registry_lock:
        if process_id not in _process_registry:
            return json.dumps({
                "status": "error",
                "message": f"Process {process_id} not found."
            }, ensure_ascii=False)
        
        info = _process_registry[process_id]
        proc = info.get("process")
        
        if proc is None:
            return json.dumps({
                "status": "error",
                "message": f"Process {process_id} not found."
            }, ensure_ascii=False)
        
        is_running = proc.poll() is None
        exit_code = proc.poll()
        
        return json.dumps({
            "status": "success",
            "action": "status",
            "process_id": process_id,
            "command": info.get("command", ""),
            "is_running": is_running,
            "exit_code": exit_code,
            "pid": proc.pid,
            "started_at": info.get("started_at"),
            "message": f"Process is {'running' if is_running else 'stopped'}."
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
