"""Memory 工具：持久记忆。

基于 FileMemoryProvider 实现跨会话持久记忆。
支持两个目标：
- memory: Agent 的长期记忆（环境事实、项目约定等）
- user: 用户画像和偏好

操作：
- add: 添加新条目
- replace: 替换现有条目
- remove: 删除条目
- view: 查看记忆内容
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.tools.registry import register_tool

logger = logging.getLogger(__name__)

# 记忆文件存储路径
MEMORY_DIR = Path.home() / ".nanohermes" / "memory"
MEMORY_FILE = MEMORY_DIR / "MEMORY.md"
USER_FILE = MEMORY_DIR / "USER.md"


def _ensure_memory_dir():
    """确保记忆目录和文件存在。"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not MEMORY_FILE.exists():
        MEMORY_FILE.write_text("# Agent Memory\n\n", encoding="utf-8")
    if not USER_FILE.exists():
        USER_FILE.write_text("# User Profile\n\n", encoding="utf-8")


def _get_file_path(target: str) -> Path:
    """获取目标文件路径。"""
    if target == "user":
        return USER_FILE
    return MEMORY_FILE


def _read_file(path: Path) -> str:
    """读取文件内容。"""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _write_file(path: Path, content: str):
    """写入文件内容。"""
    path.write_text(content, encoding="utf-8")


def _add_entry(target: str, content: str) -> dict:
    """添加记忆条目。"""
    path = _get_file_path(target)
    _ensure_memory_dir()
    
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n## Entry\n\n{content}\n")
    
    return {
        "status": "success",
        "action": "add",
        "target": target,
        "message": f"Added entry to {target} memory."
    }


def _replace_entry(target: str, old_text: str, new_content: str) -> dict:
    """替换记忆条目。"""
    path = _get_file_path(target)
    content = _read_file(path)
    
    if old_text not in content:
        return {
            "status": "error",
            "message": f"Old text not found in {target} memory. Use exact text to identify the entry."
        }
    
    new_content = content.replace(old_text, new_content, 1)
    _write_file(path, new_content)
    
    return {
        "status": "success",
        "action": "replace",
        "target": target,
        "message": f"Replaced entry in {target} memory."
    }


def _remove_entry(target: str, old_text: str) -> dict:
    """删除记忆条目。"""
    path = _get_file_path(target)
    content = _read_file(path)
    
    if old_text not in content:
        return {
            "status": "error",
            "message": f"Old text not found in {target} memory. Use exact text to identify the entry."
        }
    
    new_content = content.replace(old_text, "", 1)
    _write_file(path, new_content)
    
    return {
        "status": "success",
        "action": "remove",
        "target": target,
        "message": f"Removed entry from {target} memory."
    }


def _view_memory(target: str = "") -> dict:
    """查看记忆内容。"""
    result = {}
    
    if not target or target == "memory":
        result["memory"] = _read_file(MEMORY_FILE)
    
    if not target or target == "user":
        result["user"] = _read_file(USER_FILE)
    
    return {
        "status": "success",
        "action": "view",
        "content": result,
        "message": "Current memory contents."
    }


def memory(
    action: str = "",
    target: str = "memory",
    content: str = "",
    old_text: str = "",
    key: str = "",
    task_id: str = None,
) -> str:
    """持久记忆工具。
    
    保存跨会话的持久信息。
    
    何时保存（主动执行，不要等待被要求）：
    - 用户纠正你或说"记住这个"/"别再那样做"
    - 用户分享偏好、习惯或个人信息
    - 发现环境信息（OS、已安装工具、项目结构）
    - 学习到特定用户的约定、API 怪癖或工作流
    
    优先级：用户偏好和纠正 > 环境事实 > 程序性知识
    """
    if target not in ("memory", "user"):
        return json.dumps({
            "status": "error",
            "message": f"Invalid target '{target}'. Use 'memory' or 'user'."
        }, ensure_ascii=False)
    
    try:
        if action == "add":
            if not content:
                return json.dumps({
                    "status": "error",
                    "message": "Content is required for 'add' action."
                }, ensure_ascii=False)
            result = _add_entry(target, content)
            
        elif action == "replace":
            if not old_text:
                return json.dumps({
                    "status": "error",
                    "message": "old_text is required for 'replace' action."
                }, ensure_ascii=False)
            if not content:
                return json.dumps({
                    "status": "error",
                    "message": "content is required for 'replace' action."
                }, ensure_ascii=False)
            result = _replace_entry(target, old_text, content)
            
        elif action == "remove":
            if not old_text:
                return json.dumps({
                    "status": "error",
                    "message": "old_text is required for 'remove' action."
                }, ensure_ascii=False)
            result = _remove_entry(target, old_text)
            
        elif action == "view":
            result = _view_memory(target)
            
        else:
            return json.dumps({
                "status": "error",
                "message": f"Unknown action '{action}'. Use: add, replace, remove, view"
            }, ensure_ascii=False)
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Memory tool error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Memory operation failed: {str(e)}"
        }, ensure_ascii=False)


def check_memory_requirements() -> bool:
    """Memory 工具没有外部要求，始终可用。"""
    return True


register_tool(
    name="memory",
    toolset="memory",
    schema={
        "name": "memory",
        "description": (
            "保存跨会话的持久记忆。记忆会注入到未来的对话中，所以保持简洁。\n\n"
            "何时保存（主动执行）：\n"
            "- 用户纠正你或说'记住这个'\n"
            "- 用户分享偏好、习惯或个人信息\n"
            "- 发现环境信息（OS、工具、项目结构）\n"
            "- 学习到特定用户的约定或工作流\n\n"
            "两个目标：\n"
            "- 'user': 用户画像 - 姓名、角色、偏好、沟通风格\n"
            "- 'memory': Agent 笔记 - 环境事实、项目约定、工具怪癖\n\n"
            "不要保存：任务进度、会话结果、临时状态（这些用 session_search 查找）"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "replace", "remove", "view"],
                    "description": "要执行的操作。",
                },
                "target": {
                    "type": "string",
                    "enum": ["memory", "user"],
                    "description": "记忆目标：'memory' 用于笔记，'user' 用于用户画像。",
                },
                "content": {
                    "type": "string",
                    "description": "记忆内容（add/replace 时需要）。",
                },
                "old_text": {
                    "type": "string",
                    "description": "要替换/删除的原文（replace/remove 时需要）。",
                },
            },
            "required": ["action"],
        },
    },
    handler=memory,
    check_fn=check_memory_requirements,
    description="持久记忆",
)
