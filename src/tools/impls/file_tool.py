"""文件工具：读取文件、写入文件、搜索文件、补丁编辑。

参考 Hermes Agent 的 file_tools.py 实现，简化版本包含：
- read_file: 读取文件内容（支持分页）
- write_file: 写入文件内容
- search_files: 搜索文件（按名称/扩展名/内容）
- patch: 查找替换编辑（支持模糊匹配）

设计决策：
- 所有工具返回 JSON 字符串，便于 LLM 解析
- 安全检查防止误操作敏感文件
- search_files 使用逐行读取，支持大文件
- patch 支持模糊匹配（空白归一化），提高成功率
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from src.tools.core.registry import register_tool


# ============================================================================
# 常量定义
# ============================================================================

# 二进制文件扩展名（不应作为文本读取）
BINARY_EXTENSIONS = {
    # 编译文件
    '.pyc', '.pyo', '.so', '.dll', '.exe', '.o', '.obj', '.class',
    # 图片
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.bmp', '.webp', '.svg',
    # 压缩包
    '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
    # 文档
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    # 数据库
    '.sqlite', '.db', '.mdb',
    # 音视频
    '.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv',
    # 字体
    '.ttf', '.otf', '.woff', '.woff2',
}

# 敏感路径模式（防止误写）
SENSITIVE_PATH_PATTERNS = [
    '.env',           # 环境变量
    '.git',           # Git 仓库
    'node_modules',   # Node 依赖
    '__pycache__',    # Python 缓存
    '.venv',          # 虚拟环境
    'venv',           # 虚拟环境
    '.ssh',           # SSH 密钥
    '.aws',           # AWS 凭证
]

# 文件读取最大行数限制
MAX_READ_LINES = 10000

# 搜索最大结果数
MAX_SEARCH_RESULTS = 100


# ============================================================================
# 辅助函数
# ============================================================================

def _is_binary_file(path: Path) -> bool:
    """判断文件是否为二进制文件。

    检查策略：
    1. 扩展名匹配（快速）
    2. 读取文件头部检测 null bytes（准确）

    为什么要双重检查？
    - 扩展名不可靠（如 .txt 文件可能包含二进制内容）
    - 读取整个文件太慢，只检查前 8KB
    """
    # 快速检查：扩展名
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    # 精确检查：读取前 8KB 检测 null bytes
    try:
        with open(path, 'rb') as f:
            chunk = f.read(8192)
            return b'\x00' in chunk
    except (IOError, OSError):
        return False


def _is_sensitive_path(path: Path) -> bool:
    """检查路径是否为敏感路径。

    检查策略：
    1. 检查路径各部分是否包含敏感目录名
    2. 检查文件名是否为敏感文件

    为什么要检查所有部分？
    - 防止 `/project/.env/backup.txt` 这样的嵌套路径
    - 防止 `.git/config` 这样的子路径
    """
    path_str = str(path)
    path_parts = path.parts

    for pattern in SENSITIVE_PATH_PATTERNS:
        # 检查文件名
        if path.name == pattern or path.name.startswith(pattern + '.'):
            return True
        # 检查路径各部分
        if pattern in path_parts:
            return True
        # 检查完整路径（处理绝对路径）
        if f'{os.sep}{pattern}' in path_str or path_str.endswith(f'{os.sep}{pattern}'):
            return True

    return False


def _normalize_whitespace(text: str) -> str:
    """归一化空白字符，用于模糊匹配。

    转换规则：
    - 所有空白字符（空格、tab、换行）替换为单个空格
    - 去除首尾空白

    为什么要归一化？
    - 不同编辑器可能有不同的缩进设置（2空格 vs 4空格 vs tab）
    - 复制粘贴时可能引入额外空白
    - 归一化后匹配更宽松，提高成功率
    """
    return re.sub(r'\s+', ' ', text).strip()


# ============================================================================
# read_file - 读取文件
# ============================================================================

def read_file(path: str, offset: int = 1, limit: int = 500, task_id: str = None, **kwargs) -> str:
    """读取文件内容，支持分页和行号。

    Args:
        path: 文件路径（绝对或相对路径）。
        offset: 起始行号（从 1 开始）。
        limit: 最大读取行数（最大 2000）。
        task_id: 任务 ID（保留参数）。

    Returns:
        JSON 字符串，包含内容、行号、总行数等。

    安全限制：
    - 拒绝读取二进制文件（通过扩展名和内容检测）
    - 限制最大读取行数，防止 OOM
    """
    try:
        file_path = Path(path).expanduser().resolve()

        # 安全检查：文件存在性
        if not file_path.exists():
            # 尝试查找相似文件
            parent = file_path.parent
            if parent.exists():
                similar = [f.name for f in parent.iterdir() if f.is_file()][:10]
                return json.dumps({
                    "error": f"文件不存在: {path}",
                    "similar_files": similar,
                    "hint": "请检查路径是否正确"
                }, ensure_ascii=False)
            return json.dumps({"error": f"文件不存在: {path}"}, ensure_ascii=False)

        if not file_path.is_file():
            return json.dumps({"error": f"不是文件: {path}"}, ensure_ascii=False)

        # 安全检查：二进制文件
        if _is_binary_file(file_path):
            return json.dumps({
                "error": f"无法读取二进制文件: {path}",
                "hint": "请使用专门的工具处理二进制文件"
            }, ensure_ascii=False)

        # 读取文件（逐行，支持大文件）
        all_lines = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= MAX_READ_LINES:
                    break
                all_lines.append(line)

        total_lines = len(all_lines)
        truncated = total_lines >= MAX_READ_LINES

        # 限制单次读取行数
        limit = min(limit, 2000)

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

        if truncated:
            result["warning"] = f"文件超过 {MAX_READ_LINES} 行，已截断"

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
        task_id: 任务 ID（保留参数）。

    Returns:
        JSON 字符串，包含写入结果。

    安全检查：
    - 阻止写入敏感路径（.env, .git, node_modules 等）
    - 自动创建父目录
    """
    try:
        file_path = Path(path).expanduser().resolve()

        # 安全检查：敏感路径
        if _is_sensitive_path(file_path):
            return json.dumps({
                "error": f"拒绝写入敏感路径: {path}",
                "hint": "如需修改敏感文件，请使用专门的工具或手动操作"
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
    recursive: bool = True,
    task_id: str = None,
    **kwargs,
) -> str:
    """搜索文件内容或按名称查找文件。

    Args:
        pattern: 搜索模式。content 模式为正则表达式，files 模式为 glob 模式。
        target: "content" 搜索文件内容，"files" 按名称查找文件。
        path: 搜索目录。
        file_glob: 文件名过滤模式（仅 content 模式）。
        limit: 最大结果数。
        offset: 跳过前 N 个结果。
        output_mode: "content" 显示匹配行，"files_only" 仅显示文件名，"count" 显示计数。
        context: 匹配行前后显示的上下文行数。
        recursive: 是否递归搜索子目录。
        task_id: 任务 ID（保留参数）。

    Returns:
        JSON 字符串，包含搜索结果。

    性能优化：
    - 逐行读取，支持大文件
    - 跳过二进制文件
    - 结果数限制防止 OOM
    """
    try:
        search_path = Path(path).expanduser().resolve()
        if not search_path.exists():
            return json.dumps({"error": f"路径不存在: {path}"}, ensure_ascii=False)

        if not search_path.is_dir():
            return json.dumps({"error": f"不是目录: {path}"}, ensure_ascii=False)

        # 限制结果数
        limit = min(limit, MAX_SEARCH_RESULTS)

        # 文件搜索模式
        if target == "files":
            return _search_files_by_name(search_path, pattern, recursive, limit, offset)

        # 内容搜索模式
        return _search_files_by_content(
            search_path, pattern, file_glob, recursive,
            limit, offset, output_mode, context
        )

    except Exception as e:
        return json.dumps({"error": f"搜索失败: {type(e).__name__}: {e}"}, ensure_ascii=False)


def _search_files_by_name(
    search_path: Path,
    pattern: str,
    recursive: bool,
    limit: int,
    offset: int,
) -> str:
    """按文件名搜索（glob 模式）。"""
    results = []
    skipped = 0

    # 选择搜索方法
    glob_method = search_path.rglob if recursive else search_path.glob

    for f in glob_method(pattern):
        if f.is_file():
            if skipped < offset:
                skipped += 1
                continue
            results.append(str(f))
            if len(results) >= limit:
                break

    return json.dumps({
        "path": str(search_path),
        "pattern": pattern,
        "total_found": len(results) + skipped,
        "offset": offset,
        "files": results,
    }, ensure_ascii=False)


def _search_files_by_content(
    search_path: Path,
    pattern: str,
    file_glob: str | None,
    recursive: bool,
    limit: int,
    offset: int,
    output_mode: str,
    context_lines: int,
) -> str:
    """按内容搜索（正则模式，逐行读取）。"""
    # 编译正则表达式
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return json.dumps({
            "error": f"无效的正则表达式: {pattern}",
            "details": str(e)
        }, ensure_ascii=False)

    results = []
    files_searched = 0
    skipped = 0

    # 选择文件遍历方法
    glob_pattern = file_glob if file_glob else "*"
    glob_method = search_path.rglob if recursive else search_path.glob

    for file_path in glob_method(glob_pattern):
        if not file_path.is_file():
            continue

        # 跳过二进制文件
        if _is_binary_file(file_path):
            continue

        files_searched += 1

        # 逐行读取并搜索
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = []
                for line_num, line in enumerate(f, 1):
                    lines.append(line)

                    # 检查匹配
                    if regex.search(line):
                        # 处理 offset
                        if skipped < offset:
                            skipped += 1
                            continue

                        # 构建结果
                        match_result = _build_match_result(
                            file_path, line_num, line, lines, context_lines
                        )

                        if output_mode == "files_only":
                            # 只添加文件名（去重）
                            file_str = str(file_path)
                            if file_str not in results:
                                results.append(file_str)
                        elif output_mode == "count":
                            # 计数模式
                            results.append(match_result)
                        else:
                            # 完整内容模式
                            results.append(match_result)

                        if len(results) >= limit:
                            break

                if len(results) >= limit:
                    break

        except (IOError, OSError):
            # 跳过无法读取的文件
            continue

    # 构建响应
    response = {
        "path": str(search_path),
        "pattern": pattern,
        "files_searched": files_searched,
        "offset": offset,
    }

    if output_mode == "count":
        # 按文件分组计数
        file_counts = {}
        for r in results:
            file_counts[r["file"]] = file_counts.get(r["file"], 0) + 1
        response["counts"] = file_counts
        response["total_matches"] = len(results)
    elif output_mode == "files_only":
        response["total_found"] = len(results)
        response["files"] = results
    else:
        response["total_found"] = len(results)
        response["matches"] = results

    return json.dumps(response, ensure_ascii=False)


def _build_match_result(
    file_path: Path,
    line_num: int,
    matched_line: str,
    all_lines: list[str],
    context_lines: int,
) -> dict:
    """构建匹配结果，包含上下文行。"""
    result = {
        "file": str(file_path),
        "line": line_num,
        "content": matched_line.rstrip(),
    }

    # 添加上下文
    if context_lines > 0:
        start = max(0, line_num - 1 - context_lines)
        end = min(len(all_lines), line_num + context_lines)

        before = []
        for i in range(start, line_num - 1):
            before.append(f"{i + 1}: {all_lines[i].rstrip()}")

        after = []
        for i in range(line_num, end):
            after.append(f"{i + 1}: {all_lines[i].rstrip()}")

        if before:
            result["before"] = before
        if after:
            result["after"] = after

    return result


# ============================================================================
# patch - 查找替换编辑
# ============================================================================

def patch(
    mode: str = "replace",
    path: str = "",
    old_string: str = "",
    new_string: str = "",
    replace_all: bool = False,
    fuzzy: bool = True,
    patch_content: str = "",
    task_id: str = None,
    **kwargs,
) -> str:
    """文件查找替换编辑。

    Args:
        mode: "replace" 查找替换模式，"patch" V4A 补丁模式（未实现）。
        path: 文件路径（replace 模式必需）。
        old_string: 要查找的字符串（replace 模式必需）。
        new_string: 替换为的字符串。
        replace_all: 是否替换所有匹配项。
        fuzzy: 是否启用模糊匹配（空白归一化）。
        patch_content: V4A 补丁内容（patch 模式）。
        task_id: 任务 ID（保留参数）。

    Returns:
        JSON 字符串，包含操作结果。

    模糊匹配策略：
    1. 首先尝试精确匹配
    2. 失败后尝试空白归一化匹配
    3. 归一化：所有空白字符（空格、tab、换行）替换为单个空格

    为什么要模糊匹配？
    - 不同编辑器缩进设置不同（2空格 vs 4空格 vs tab）
    - 复制粘贴可能引入额外空白
    - 提高匹配成功率，减少重试
    """
    try:
        # Patch 模式（未实现）
        if mode == "patch":
            return json.dumps({
                "status": "error",
                "message": "V4A patch mode not yet implemented. Use mode='replace' instead.",
                "hint": "请使用 mode='replace' 进行查找替换"
            }, ensure_ascii=False)

        # 参数验证
        if not path:
            return json.dumps({"error": "缺少必需参数: path"}, ensure_ascii=False)
        if not old_string:
            return json.dumps({"error": "缺少必需参数: old_string"}, ensure_ascii=False)

        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            return json.dumps({"error": f"文件不存在: {path}"}, ensure_ascii=False)

        if not file_path.is_file():
            return json.dumps({"error": f"不是文件: {path}"}, ensure_ascii=False)

        # 读取文件内容
        content = file_path.read_text(encoding="utf-8")

        # 尝试匹配
        match_result = _find_match(content, old_string, fuzzy)

        if match_result is None:
            return json.dumps({
                "error": f"未找到匹配: {old_string[:100]}...",
                "hint": "请检查字符串是否正确，或尝试 fuzzy=true"
            }, ensure_ascii=False)

        match_count = match_result["count"]

        # 检查唯一性
        if match_count > 1 and not replace_all:
            return json.dumps({
                "error": f"找到 {match_count} 处匹配，需要唯一匹配",
                "hint": "请提供更多上下文确保唯一性，或使用 replace_all=true"
            }, ensure_ascii=False)

        # 执行替换
        if match_result["type"] == "exact":
            # 精确匹配
            new_content = content.replace(old_string, new_string, -1 if replace_all else 1)
        else:
            # 模糊匹配：使用正则替换
            new_content = match_result["regex"].sub(
                new_string,
                content,
                count=0 if replace_all else 1
            )

        # 写回文件
        file_path.write_text(new_content, encoding="utf-8")

        return json.dumps({
            "status": "success",
            "path": str(file_path),
            "matches_replaced": match_count if replace_all else 1,
            "match_type": match_result["type"],
        }, ensure_ascii=False)

    except PermissionError:
        return json.dumps({"error": f"权限不足: {path}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"补丁失败: {type(e).__name__}: {e}"}, ensure_ascii=False)


def _find_match(content: str, old_string: str, fuzzy: bool) -> dict | None:
    """查找匹配，支持精确和模糊匹配。

    Returns:
        匹配结果字典或 None。
        {
            "type": "exact" | "fuzzy",
            "count": int,
            "regex": re.Pattern (仅模糊匹配)
        }
    """
    # 1. 精确匹配
    count = content.count(old_string)
    if count > 0:
        return {"type": "exact", "count": count}

    # 2. 模糊匹配（如果启用）
    if fuzzy:
        # 归一化空白后匹配
        normalized_old = _normalize_whitespace(old_string)

        # 构建正则：将空白替换为 \s+
        # 转义特殊字符，但保留空白处理
        escaped = re.escape(normalized_old)
        # 将转义的空格替换为 \s+
        pattern_str = escaped.replace(r'\ ', r'\s+')

        try:
            regex = re.compile(pattern_str, re.MULTILINE)
            matches = list(regex.finditer(content))
            if matches:
                return {"type": "fuzzy", "count": len(matches), "regex": regex}
        except re.error:
            pass

    return None


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
                "Read a text file with line numbers and pagination. "
                "Output format: 'LINE_NUM | CONTENT'. "
                "Use offset and limit for large files (max 2000 lines per request). "
                "Cannot read binary files (images, PDFs, archives, etc.). "
                "For images, use vision_analyze tool instead."
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
                "Write content to a file, creating or overwriting it. "
                "Parent directories are created automatically. "
                "WARNING: This completely replaces the file content. "
                "Use 'patch' tool for targeted edits instead. "
                "Cannot write to sensitive paths (.env, .git, node_modules, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write (will be created if it doesn't exist)",
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
                "Search file contents or find files by name pattern.\n\n"
                "Content search (target='content'): Regex search inside files. "
                "Supports context lines before/after matches.\n\n"
                "File search (target='files'): Find files by glob pattern (e.g., '*.py', '*config*').\n\n"
                "Binary files are automatically skipped."
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
                        "description": "'content' searches inside files, 'files' searches by filename",
                        "default": "content"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (default: current directory)",
                        "default": ".",
                    },
                    "file_glob": {
                        "type": "string",
                        "description": "Filter files by pattern (e.g., '*.py' to only search Python files)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 50, max: 100)",
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
                        "description": "Output format: 'content' shows matching lines, 'files_only' lists file paths, 'count' shows match counts",
                        "default": "content"
                    },
                    "context": {
                        "type": "integer",
                        "description": "Number of context lines before and after each match (default: 0)",
                        "default": 0,
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Search subdirectories recursively (default: true)",
                        "default": True
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
                "Find and replace text in files. "
                "Supports fuzzy matching (whitespace normalization) for robustness.\n\n"
                "REPLACE MODE (default): Find old_string and replace with new_string. "
                "old_string must be unique unless replace_all=true.\n\n"
                "Fuzzy matching: When exact match fails, normalizes whitespace "
                "(converts tabs/multiple spaces to single space) and retries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["replace", "patch"],
                        "description": "Edit mode. 'replace' (default): find and replace. 'patch': V4A format (not implemented).",
                        "default": "replace"
                    },
                    "path": {
                        "type": "string",
                        "description": "File path to edit (required for replace mode)",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Text to find (required for replace mode). Must be unique unless replace_all=true.",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement text. Use empty string to delete.",
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace all occurrences instead of requiring unique match (default: false)",
                        "default": False
                    },
                    "fuzzy": {
                        "type": "boolean",
                        "description": "Enable fuzzy matching with whitespace normalization (default: true)",
                        "default": True
                    },
                },
                "required": ["path", "old_string"],
            },
        },
        handler=patch,
        description="查找替换编辑",
    )


# 模块导入时自动注册
_register_file_tools()
