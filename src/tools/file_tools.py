"""文件工具：读取文件、写入文件、搜索文件。

参考 Hermes Agent 的 file_tools.py 实现，简化版本包含：
- read_file: 读取文件内容（支持分页）
- write_file: 写入文件内容
- search_files: 搜索文件（按名称/扩展名）
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.tools.registry import register_tool


# ============================================================================
# read_file - 读取文件
# ============================================================================
def read_file(path: str, offset: int = 1, limit: int = 500, task_id: str = None) -> str:
    """读取文件内容，支持分页和行号。

    Args:
        path: 文件路径（绝对或相对路径）。
        offset: 起始行号（从 1 开始）。
        limit: 最大读取行数。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含内容、行号、总行数等。
    """
    try:
        file_path = Path(path)

        # 安全检查：不允许读取非文件
        if not file_path.exists():
            return json.dumps({"error": f"文件不存在: {path}"}, ensure_ascii=False)

        if not file_path.is_file():
            return json.dumps({"error": f"不是文件: {path}"}, ensure_ascii=False)

        # 安全检查：阻止读取二进制文件
        binary_exts = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.zip', '.tar', '.gz'}
        if file_path.suffix.lower() in binary_exts:
            return json.dumps({
                "error": f"无法读取二进制文件: {path} ({file_path.suffix})"
            }, ensure_ascii=False)

        # 读取文件
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        total_lines = len(all_lines)

        # 分页
        start = max(0, offset - 1)
        end = min(start + limit, total_lines)
        page_lines = all_lines[start:end]

        # 添加行号
        numbered_lines = []
        for i, line in enumerate(page_lines, start=start + 1):
            numbered_lines.append(f"{i:6d} | {line.rstrip()}")

        content = "\n".join(numbered_lines)

        result = {
            "path": str(file_path),
            "offset": offset,
            "limit": limit,
            "total_lines": total_lines,
            "lines_returned": len(page_lines),
            "content": content,
        }

        if end < total_lines:
            result["has_more"] = True
            result["next_offset"] = end + 1

        return json.dumps(result, ensure_ascii=False)

    except PermissionError:
        return json.dumps({"error": f"权限不足，无法读取: {path}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"读取文件失败: {type(e).__name__}: {e}"}, ensure_ascii=False)


# ============================================================================
# write_file - 写入文件
# ============================================================================
def write_file(path: str, content: str, task_id: str = None) -> str:
    """写入文件内容。如果文件不存在则创建，存在则覆盖。

    Args:
        path: 文件路径。
        content: 要写入的内容。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含写入结果。
    """
    try:
        file_path = Path(path)

        # 安全检查：阻止写入敏感路径
        sensitive_paths = [".env", ".git", "node_modules", "__pycache__"]
        for sp in sensitive_paths:
            if str(file_path).startswith(sp) or sp in str(file_path).split(os.sep):
                return json.dumps({
                    "error": f"拒绝写入敏感路径: {path}"
                }, ensure_ascii=False)

        # 确保父目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return json.dumps({
            "path": str(file_path),
            "bytes_written": len(content.encode("utf-8")),
            "status": "success",
        }, ensure_ascii=False)

    except PermissionError:
        return json.dumps({"error": f"权限不足，无法写入: {path}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"写入文件失败: {type(e).__name__}: {e}"}, ensure_ascii=False)


# ============================================================================
# search_files - 搜索文件
# ============================================================================
def search_files(
    path: str = ".",
    pattern: str = "*",
    recursive: bool = False,
    max_results: int = 50,
    task_id: str = None,
) -> str:
    """搜索文件。

    Args:
        path: 搜索起始目录。
        pattern: 文件名模式（支持通配符，如 "*.py"）。
        recursive: 是否递归搜索子目录。
        max_results: 最大返回结果数。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含匹配的文件列表。
    """
    try:
        search_path = Path(path)
        if not search_path.is_dir():
            return json.dumps({"error": f"目录不存在: {path}"}, ensure_ascii=False)

        results = []
        if recursive:
            for f in search_path.rglob(pattern):
                if f.is_file():
                    results.append(str(f))
                    if len(results) >= max_results:
                        break
        else:
            for f in search_path.glob(pattern):
                if f.is_file():
                    results.append(str(f))
                    if len(results) >= max_results:
                        break

        return json.dumps({
            "path": str(search_path),
            "pattern": pattern,
            "recursive": recursive,
            "total_found": len(results),
            "files": results,
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"搜索文件失败: {type(e).__name__}: {e}"}, ensure_ascii=False)


# ============================================================================
# 注册文件工具
# ============================================================================
def _register_file_tools() -> None:
    """注册文件工具到全局注册表。"""
    # read_file
    register_tool(
        name="read_file",
        toolset="file",
        schema={
            "name": "read_file",
            "description": "读取文件内容，支持分页和行号。适合查看代码、配置文件等文本文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径（绝对或相对路径）。",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "起始行号（从 1 开始），默认 1。",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "最大读取行数，默认 500。",
                    },
                },
                "required": ["path"],
            },
        },
        handler=read_file,
        description="读取文件内容",
    )

    # write_file
    register_tool(
        name="write_file",
        toolset="file",
        schema={
            "name": "write_file",
            "description": "写入文件内容。如果文件不存在则创建，存在则覆盖。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径。",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的内容。",
                    },
                },
                "required": ["path", "content"],
            },
        },
        handler=write_file,
        description="写入文件内容",
    )

    # search_files
    register_tool(
        name="search_files",
        toolset="file",
        schema={
            "name": "search_files",
            "description": "搜索匹配模式的文件。支持通配符和递归搜索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "搜索起始目录，默认当前目录。",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "文件名模式（支持通配符，如 '*.py'）。",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归搜索子目录，默认 false。",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数，默认 50。",
                    },
                },
                "required": ["pattern"],
            },
        },
        handler=search_files,
        description="搜索文件",
    )

    # patch
    register_tool(
        name="patch",
        toolset="file",
        schema={
            "name": "patch",
            "description": "文件查找替换编辑。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径。"},
                    "old_str": {"type": "string", "description": "要查找的字符串。"},
                    "new_str": {"type": "string", "description": "替换后的字符串。"},
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
        handler=patch,
        description="查找替换编辑",
    )


# ============================================================================
# patch - 查找替换编辑
# ============================================================================
def patch(path: str = "", old_str: str = "", new_str: str = "", task_id: str = None) -> str:
    """文件查找替换编辑。"""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return json.dumps({"error": f"File not found: {path}"}, ensure_ascii=False)

        content = file_path.read_text(encoding="utf-8")
        if old_str not in content:
            return json.dumps({"error": f"String not found: {old_str[:50]}..."}, ensure_ascii=False)

        new_content = content.replace(old_str, new_str, 1)
        file_path.write_text(new_content, encoding="utf-8")

        return json.dumps({
            "status": "success",
            "path": path,
            "message": "Patch applied successfully."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Patch failed: {type(e).__name__}: {e}"}, ensure_ascii=False)


# 模块导入时自动注册
_register_file_tools()
