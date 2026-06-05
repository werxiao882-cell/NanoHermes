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
def read_file(path: str, offset: int = 1, limit: int = 500, task_id: str = None, **kwargs) -> str:
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
def write_file(path: str, content: str, task_id: str = None, **kwargs) -> str:
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
    pattern: str = "*",
    target: str = "content",
    path: str = ".",
    file_glob: str = None,
    limit: int = 50,
    offset: int = 0,
    output_mode: str = "content",
    context: int = 0,
    recursive: bool = False,
    max_results: int = 50,
    task_id: str = None,
    **kwargs,
) -> str:
    """搜索文件。"""
    try:
        search_path = Path(path)
        if not search_path.is_dir():
            return json.dumps({"error": f"目录不存在: {path}"}, ensure_ascii=False)

        # File search mode
        if target == "files":
            results = []
            if recursive:
                for f in search_path.rglob(pattern):
                    if f.is_file():
                        results.append(str(f))
                        if len(results) >= limit:
                            break
            else:
                for f in search_path.glob(pattern):
                    if f.is_file():
                        results.append(str(f))
                        if len(results) >= limit:
                            break

            return json.dumps({
                "path": str(search_path),
                "pattern": pattern,
                "total_found": len(results),
                "files": results,
            }, ensure_ascii=False)
        
        # Content search mode (simple implementation)
        results = []
        for f in search_path.rglob(file_glob or "*"):
            if f.is_file():
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    import re
                    matches = list(re.finditer(pattern, content, re.IGNORECASE))
                    for m in matches:
                        start = max(0, m.start() - 50)
                        end = min(len(content), m.end() + 50)
                        line_num = content[:m.start()].count("\n") + 1
                        results.append({
                            "file": str(f),
                            "line": line_num,
                            "match": content[start:end],
                        })
                        if len(results) >= limit:
                            break
                except Exception:
                    pass
            if len(results) >= limit:
                break

        return json.dumps({
            "path": str(search_path),
            "pattern": pattern,
            "total_found": len(results),
            "matches": results,
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
            "description": (
                "Read a text file with line numbers and pagination. Use this instead of cat/head/tail in terminal. "
                "Output format: 'LINE_NUM|CONTENT'. Suggests similar filenames if not found. "
                "Use offset and limit for large files. Reads exceeding ~100K characters are rejected; "
                "use offset and limit to read specific sections of large files. "
                "NOTE: Cannot read images or binary files — use vision_analyze for images."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read (absolute, relative, or ~/path)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start reading from (1-indexed, default: 1)",
                        "default": 1,
                        "minimum": 1,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read (default: 500, max: 2000)",
                        "default": 500,
                        "maximum": 2000,
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
            "description": (
                "Write content to a file, completely replacing existing content. "
                "Use this instead of echo/cat heredoc in terminal. "
                "Creates parent directories automatically. "
                "OVERWRITES the entire file — use 'patch' for targeted edits. "
                "Auto-runs syntax checks on .py/.json/.yaml/.toml and other linted languages; "
                "only NEW errors introduced by this write are surfaced (pre-existing errors are filtered out)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write (will be created if it doesn't exist, overwritten if it does)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete content to write to the file",
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
            "description": (
                "Search file contents or find files by name. Use this instead of grep/rg/find/ls in terminal. "
                "Ripgrep-backed, faster than shell equivalents.\n\n"
                "Content search (target='content'): Regex search inside files. "
                "Output modes: full matches with line numbers, file paths only, or match counts.\n\n"
                "File search (target='files'): Find files by glob pattern (e.g., '*.py', '*config*'). "
                "Also use this instead of ls — results sorted by modification time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern for content search, or glob pattern (e.g., '*.py') for file search"
                    },
                    "target": {
                        "type": "string",
                        "enum": ["content", "files"],
                        "description": "'content' searches inside file contents, 'files' searches for files by name",
                        "default": "content"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in (default: current working directory)",
                        "default": ".",
                    },
                    "file_glob": {
                        "type": "string",
                        "description": "Filter files by pattern in grep mode (e.g., '*.py' to only search Python files)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 50)",
                        "default": 50,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Skip first N results for pagination (default: 0)",
                        "default": 0,
                    },
                    "output_mode": {
                        "type": "string",
                        "enum": ["content", "files_only", "count"],
                        "description": "Output format for grep mode: 'content' shows matching lines with line numbers, 'files_only' lists file paths, 'count' shows match counts per file",
                        "default": "content"
                    },
                    "context": {
                        "type": "integer",
                        "description": "Number of context lines before and after each match (grep mode only)",
                        "default": 0,
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
            "description": (
                "Targeted find-and-replace edits in files. Use this instead of sed/awk in terminal. "
                "Uses fuzzy matching (9 strategies) so minor whitespace/indentation differences won't break it. "
                "Returns a unified diff. Auto-runs syntax checks after editing.\n\n"
                "REPLACE MODE (mode='replace', default): find a unique string and replace it. "
                "REQUIRED PARAMETERS: mode, path, old_string, new_string.\n"
                "PATCH MODE (mode='patch'): apply V4A multi-file patches for bulk changes. "
                "REQUIRED PARAMETERS: mode, patch."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["replace", "patch"],
                        "description": "Edit mode. 'replace' (default): requires path + old_string + new_string. 'patch': requires patch content only.",
                        "default": "replace"
                    },
                    "path": {
                        "type": "string",
                        "description": "REQUIRED when mode='replace'. File path to edit."
                    },
                    "old_string": {
                        "type": "string",
                        "description": "REQUIRED when mode='replace'. Exact text to find and replace. Must be unique in the file unless replace_all=true. Include surrounding context lines to ensure uniqueness."
                    },
                    "new_string": {
                        "type": "string",
                        "description": "REQUIRED when mode='replace'. Replacement text. Pass empty string '' to delete the matched text."
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace all occurrences instead of requiring a unique match (default: false)",
                        "default": False
                    },
                    "patch": {
                        "type": "string",
                        "description": "REQUIRED when mode='patch'. V4A format patch content."
                    },
                },
                "required": ["mode"],
            },
        },
        handler=patch,
        description="查找替换编辑",
    )


# ============================================================================
# patch - 查找替换编辑
# ============================================================================
def patch(
    mode: str = "replace",
    path: str = "",
    old_string: str = "",
    new_string: str = "",
    replace_all: bool = False,
    patch: str = "",
    task_id: str = None,
    **kwargs,
) -> str:
    """文件查找替换编辑。"""
    try:
        # For backward compatibility
        if mode == "patch" and patch:
            return json.dumps({
                "status": "error",
                "message": "V4A patch mode not yet implemented. Use mode='replace' instead."
            }, ensure_ascii=False)
        
        file_path = Path(path)
        if not file_path.exists():
            return json.dumps({"error": f"File not found: {path}"}, ensure_ascii=False)

        content = file_path.read_text(encoding="utf-8")
        if old_string not in content:
            return json.dumps({"error": f"String not found: {old_string[:50]}..."}, ensure_ascii=False)

        count = content.count(old_string)
        if count > 1 and not replace_all:
            return json.dumps({
                "error": f"String found {count} times. Use replace_all=true or provide more context.",
            }, ensure_ascii=False)

        new_content = content.replace(old_string, new_string, 1 if not replace_all else -1)
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
