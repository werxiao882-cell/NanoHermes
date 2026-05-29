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

from src.tools.registry import register_tool

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
        elif action == "start":
            if not command:
                return json.dumps({
                    "status": "error",
                    "message": "Command is required for 'start' action."
                }, ensure_ascii=False)
            return _start_process(command, cwd)
        elif action == "stop":
            if not process_id:
                return json.dumps({
                    "status": "error",
                    "message": "Process ID is required for 'stop' action."
                }, ensure_ascii=False)
            return _stop_process(process_id)
        elif action == "kill":
            if not process_id:
                return json.dumps({
                    "status": "error",
                    "message": "Process ID is required for 'kill' action."
                }, ensure_ascii=False)
            return _kill_process(process_id)
        elif action == "output":
            if not process_id:
                return json.dumps({
                    "status": "error",
                    "message": "Process ID is required for 'output' action."
                }, ensure_ascii=False)
            return _get_process_output(process_id)
        elif action == "status":
            if not process_id:
                return json.dumps({
                    "status": "error",
                    "message": "Process ID is required for 'status' action."
                }, ensure_ascii=False)
            return _get_process_status(process_id)
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
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
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
            "管理后台进程。支持启动、停止、终止和监控后台进程。\n\n"
            "操作：\n"
            "- list: 列出所有活跃进程\n"
            "- start: 启动后台进程（需要 command）\n"
            "- stop: 优雅停止进程\n"
            "- kill: 强制终止进程\n"
            "- output: 获取进程输出\n"
            "- status: 查看进程状态\n\n"
            "使用场景：长时间运行的任务、监控任务、后台服务。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "start", "stop", "kill", "output", "status"],
                    "description": "要执行的操作。",
                },
                "command": {
                    "type": "string",
                    "description": "要执行的命令（start 操作需要）。",
                },
                "process_id": {
                    "type": "string",
                    "description": "进程 ID（stop/kill/output/status 操作需要）。",
                },
                "cwd": {
                    "type": "string",
                    "description": "工作目录（start 操作可选）。",
                },
            },
            "required": ["action"],
        },
    },
    handler=process,
    check_fn=check_process_requirements,
    description="后台进程管理",
)
