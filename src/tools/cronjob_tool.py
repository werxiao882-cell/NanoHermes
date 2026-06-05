"""Cronjob 工具：管理定时任务。

基于 JSON 文件存储定时任务配置。
支持的操作：
- list: 列出所有任务
- add: 添加新任务
- edit: 编辑任务
- pause: 暂停任务
- resume: 恢复任务
- run: 立即运行任务
- remove: 删除任务

支持多种调度格式：
- 持续时间： "30m", "2h", "1d"
- 周期性： "every 2h", "every monday 9am"
- Cron 表达式： "0 9 * * *"
- ISO 时间戳（一次性）： "2026-06-01T09:00:00Z"
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from src.tools.registry import register_tool

logger = logging.getLogger(__name__)

# 定时任务存储路径
CRON_DIR = Path.home() / ".nanohermes" / "cron"
CRON_FILE = CRON_DIR / "jobs.json"
_cron_lock = threading.Lock()


def _ensure_cron_dir():
    """确保定时任务目录和文件存在。"""
    CRON_DIR.mkdir(parents=True, exist_ok=True)
    if not CRON_FILE.exists():
        CRON_FILE.write_text("{}", encoding="utf-8")


def _load_jobs() -> dict:
    """加载所有定时任务。"""
    _ensure_cron_dir()
    try:
        content = CRON_FILE.read_text(encoding="utf-8")
        return json.loads(content)
    except Exception:
        return {}


def _save_jobs(jobs: dict):
    """保存所有定时任务。"""
    _ensure_cron_dir()
    CRON_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")


def _generate_job_id() -> str:
    """生成唯一的任务 ID。"""
    import uuid
    return str(uuid.uuid4())[:8]


def _parse_schedule(schedule: str) -> dict:
    """解析调度表达式。
    
    支持格式：
    - 持续时间： "30m", "2h", "1d"
    - 周期性： "every 2h", "every monday 9am"
    - Cron 表达式： "0 9 * * *"
    - ISO 时间戳（一次性）： "2026-06-01T09:00:00Z"
    """
    schedule = schedule.strip().lower()
    
    # ISO 时间戳（一次性）
    if "T" in schedule:
        try:
            dt = datetime.fromisoformat(schedule.replace("Z", "+00:00"))
            return {
                "type": "once",
                "run_at": dt.isoformat(),
                "raw": schedule,
            }
        except Exception:
            pass
    
    # 持续时间
    import re
    duration_match = re.match(r"^(\d+)([mhd])$", schedule)
    if duration_match:
        value = int(duration_match.group(1))
        unit = duration_match.group(2)
        return {
            "type": "interval",
            "value": value,
            "unit": unit,
            "raw": schedule,
        }
    
    # 周期性
    if schedule.startswith("every"):
        return {
            "type": "recurring",
            "raw": schedule,
        }
    
    # Cron 表达式（5 字段）
    parts = schedule.split()
    if len(parts) == 5:
        return {
            "type": "cron",
            "minute": parts[0],
            "hour": parts[1],
            "day_of_month": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
            "raw": schedule,
        }
    
    return {
        "type": "unknown",
        "raw": schedule,
    }


def cronjob(
    action: str = "",
    job_id: str = "",
    schedule: str = "",
    prompt: str = "",
    name: str = "",
    task_id: str = None,
    **kwargs,
) -> str:
    """管理定时任务。
    
    支持的操作：
    - list: 列出所有任务
    - add: 添加新任务（需要 schedule 和 prompt）
    - edit: 编辑任务（需要 job_id）
    - pause: 暂停任务（需要 job_id）
    - resume: 恢复任务（需要 job_id）
    - run: 立即运行任务（需要 job_id）
    - remove: 删除任务（需要 job_id）
    """
    if not action:
        return json.dumps({
            "status": "error",
            "message": "Action is required. Use: list, add, edit, pause, resume, run, remove"
        }, ensure_ascii=False)
    
    try:
        if action == "list":
            return _list_jobs()
        elif action == "add" or action == "create":
            if not schedule or not prompt:
                return json.dumps({
                    "status": "error",
                    "message": "Schedule and prompt are required for 'add' action."
                }, ensure_ascii=False)
            return _add_job(schedule, prompt, name)
        elif action == "edit" or action == "update":
            if not job_id:
                return json.dumps({
                    "status": "error",
                    "message": "Job ID is required for 'edit' action."
                }, ensure_ascii=False)
            return _edit_job(job_id, schedule, prompt, name)
        elif action == "pause":
            if not job_id:
                return json.dumps({
                    "status": "error",
                    "message": "Job ID is required for 'pause' action."
                }, ensure_ascii=False)
            return _pause_job(job_id)
        elif action == "resume":
            if not job_id:
                return json.dumps({
                    "status": "error",
                    "message": "Job ID is required for 'resume' action."
                }, ensure_ascii=False)
            return _resume_job(job_id)
        elif action == "run":
            if not job_id:
                return json.dumps({
                    "status": "error",
                    "message": "Job ID is required for 'run' action."
                }, ensure_ascii=False)
            return _run_job(job_id)
        elif action == "remove":
            if not job_id:
                return json.dumps({
                    "status": "error",
                    "message": "Job ID is required for 'remove' action."
                }, ensure_ascii=False)
            return _remove_job(job_id)
        else:
            return json.dumps({
                "status": "error",
                "message": f"Unknown action '{action}'. Use: list, add, edit, pause, resume, run, remove"
            }, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"Cronjob tool error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Cronjob operation failed: {str(e)}"
        }, ensure_ascii=False)


def _list_jobs() -> str:
    """列出所有定时任务。"""
    with _cron_lock:
        jobs = _load_jobs()
        
        job_list = []
        for jid, job in jobs.items():
            job_list.append({
                "job_id": jid,
                "name": job.get("name", ""),
                "schedule": job.get("schedule", ""),
                "prompt": job.get("prompt", "")[:100],
                "status": job.get("status", "active"),
                "created_at": job.get("created_at"),
                "last_run": job.get("last_run"),
            })
        
        return json.dumps({
            "status": "success",
            "action": "list",
            "jobs": job_list,
            "count": len(job_list),
            "message": f"Showing {len(job_list)} cron jobs."
        }, ensure_ascii=False)


def _add_job(schedule: str, prompt: str, name: str = "") -> str:
    """添加新定时任务。"""
    with _cron_lock:
        jobs = _load_jobs()
        
        job_id = _generate_job_id()
        parsed_schedule = _parse_schedule(schedule)
        
        jobs[job_id] = {
            "job_id": job_id,
            "name": name or f"Job {job_id}",
            "schedule": schedule,
            "parsed_schedule": parsed_schedule,
            "prompt": prompt,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "last_run": None,
        }
        
        _save_jobs(jobs)
        
        return json.dumps({
            "status": "success",
            "action": "add",
            "job_id": job_id,
            "schedule": parsed_schedule,
            "message": f"Cron job '{job_id}' added with schedule: {schedule}"
        }, ensure_ascii=False)


def _edit_job(job_id: str, schedule: str = "", prompt: str = "", name: str = "") -> str:
    """编辑定时任务。"""
    with _cron_lock:
        jobs = _load_jobs()
        
        if job_id not in jobs:
            return json.dumps({
                "status": "error",
                "message": f"Job {job_id} not found."
            }, ensure_ascii=False)
        
        job = jobs[job_id]
        
        if schedule:
            job["schedule"] = schedule
            job["parsed_schedule"] = _parse_schedule(schedule)
        
        if prompt:
            job["prompt"] = prompt
        
        if name:
            job["name"] = name
        
        _save_jobs(jobs)
        
        return json.dumps({
            "status": "success",
            "action": "edit",
            "job_id": job_id,
            "message": f"Job {job_id} updated."
        }, ensure_ascii=False)


def _pause_job(job_id: str) -> str:
    """暂停定时任务。"""
    with _cron_lock:
        jobs = _load_jobs()
        
        if job_id not in jobs:
            return json.dumps({
                "status": "error",
                "message": f"Job {job_id} not found."
            }, ensure_ascii=False)
        
        jobs[job_id]["status"] = "paused"
        _save_jobs(jobs)
        
        return json.dumps({
            "status": "success",
            "action": "pause",
            "job_id": job_id,
            "message": f"Job {job_id} paused."
        }, ensure_ascii=False)


def _resume_job(job_id: str) -> str:
    """恢复定时任务。"""
    with _cron_lock:
        jobs = _load_jobs()
        
        if job_id not in jobs:
            return json.dumps({
                "status": "error",
                "message": f"Job {job_id} not found."
            }, ensure_ascii=False)
        
        jobs[job_id]["status"] = "active"
        _save_jobs(jobs)
        
        return json.dumps({
            "status": "success",
            "action": "resume",
            "job_id": job_id,
            "message": f"Job {job_id} resumed."
        }, ensure_ascii=False)


def _run_job(job_id: str) -> str:
    """立即运行定时任务。"""
    with _cron_lock:
        jobs = _load_jobs()
        
        if job_id not in jobs:
            return json.dumps({
                "status": "error",
                "message": f"Job {job_id} not found."
            }, ensure_ascii=False)
        
        job = jobs[job_id]
        
        # 标记为已运行
        jobs[job_id]["last_run"] = datetime.now().isoformat()
        _save_jobs(jobs)
        
        return json.dumps({
            "status": "success",
            "action": "run",
            "job_id": job_id,
            "prompt": job.get("prompt", "")[:200],
            "message": f"Job {job_id} marked as run. In a full implementation, this would trigger execution."
        }, ensure_ascii=False)


def _remove_job(job_id: str) -> str:
    """删除定时任务。"""
    with _cron_lock:
        jobs = _load_jobs()
        
        if job_id not in jobs:
            return json.dumps({
                "status": "error",
                "message": f"Job {job_id} not found."
            }, ensure_ascii=False)
        
        del jobs[job_id]
        _save_jobs(jobs)
        
        return json.dumps({
            "status": "success",
            "action": "remove",
            "job_id": job_id,
            "message": f"Job {job_id} removed."
        }, ensure_ascii=False)


def check_cronjob_requirements() -> bool:
    """Cronjob 工具没有外部要求，始终可用。"""
    return True


register_tool(
    name="cronjob",
    toolset="cronjob",
    schema={
        "name": "cronjob",
        "description": (
            "Manage scheduled cron jobs with a single compressed tool.\n\n"
            "Use action='create' to schedule a new job from a prompt or one or more skills.\n"
            "Use action='list' to inspect jobs.\n"
            "Use action='update', 'pause', 'resume', 'remove', or 'run' to manage an existing job.\n\n"
            "To stop a job the user no longer wants: first action='list' to find the job_id, then action='remove' with that job_id. Never guess job IDs — always list first.\n\n"
            "Jobs run in a fresh session with no current-chat context, so prompts must be self-contained.\n"
            "If skills are provided on create, the future cron run loads those skills in order, then follows the prompt as the task instruction.\n"
            "On update, passing skills=[] clears attached skills.\n\n"
            "NOTE: The agent's final response is auto-delivered to the target. Put the primary\n"
            "user-facing content in the final response. Cron jobs run autonomously with no user\n"
            "present — they cannot ask questions or request clarification.\n\n"
            "Important safety rule: cron-run sessions should not recursively schedule more cron jobs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "One of: create, list, update, pause, resume, remove, run"
                },
                "job_id": {
                    "type": "string",
                    "description": "Required for update/pause/resume/remove/run"
                },
                "prompt": {
                    "type": "string",
                    "description": "For create: the full self-contained prompt. If skills are also provided, this becomes the task instruction paired with those skills."
                },
                "schedule": {
                    "type": "string",
                    "description": "For create/update: '30m', 'every 2h', '0 9 * * *', or ISO timestamp"
                },
                "name": {
                    "type": "string",
                    "description": "Optional human-friendly name"
                },
            },
            "required": ["action"],
        },
    },
    handler=cronjob,
    check_fn=check_cronjob_requirements,
    description="管理定时任务",
)
