"""循环提示系统。

提供内置维护提示和 loop.md 自定义提示加载。

查找顺序：
1. .claude/loop.md（项目级，优先）
2. ~/.nanohermes/loop.md（用户级）
3. 内置维护提示（回退）

设计理由：
- 与 CLAUDE.md 的文件位置约定一致
- 项目级优先允许团队共享循环策略
- 每次迭代前重新加载，支持运行时修改
- 25,000 字节截断防止过大文件影响性能
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.loop import MAX_LOOP_MD_SIZE

# 内置维护提示文本
MAINTENANCE_PROMPT = """维护模式。按以下优先级处理：

1. 如果当前会话中有未完成的工作（之前的回复提到要做但还没完成的事），继续完成它。
2. 如果当前分支有活跃的 PR：
   - 检查 CI 状态，如果失败则拉取失败日志并诊断
   - 处理新的审查评论
   - 解决合并冲突
3. 如果以上都没有待办事项，执行清理任务：
   - 修复已知的 bug
   - 简化复杂的代码
   - 改进测试覆盖

注意：
- 不要启动新的主动工作，只处理已有上下文中的任务
- 不可逆操作（push、delete 等）只有在之前对话中已授权的情况下才执行
- 不要递归创建新的循环任务

如果是动态间隔模式，请在响应末尾指定下一次等待时间，格式为：
__next_interval: <间隔>__
例如：__next_interval: 5m__ 或 __next_interval: 30m__
间隔单位：s（秒）、m（分钟）、h（小时）、d（天）"""


def get_maintenance_prompt(working_dir: Optional[Path] = None) -> str:
    """获取维护提示文本。

    查找顺序：
    1. working_dir/.claude/loop.md（项目级）
    2. ~/.nanohermes/loop.md（用户级）
    3. 内置维护提示（回退）

    Args:
        working_dir: 当前工作目录（用于查找项目级 loop.md）。

    Returns:
        维护提示文本（来自 loop.md 或内置）。
    """
    # 1. 项目级 loop.md
    if working_dir:
        project_loop_md = working_dir / ".claude" / "loop.md"
        content = _read_loop_md(project_loop_md)
        if content is not None:
            return content

    # 2. 用户级 loop.md
    user_loop_md = Path.home() / ".nanohermes" / "loop.md"
    content = _read_loop_md(user_loop_md)
    if content is not None:
        return content

    # 3. 内置维护提示
    return MAINTENANCE_PROMPT


def _read_loop_md(path: Path) -> Optional[str]:
    """读取 loop.md 文件。

    Args:
        path: 文件路径。

    Returns:
        文件内容（截断到 MAX_LOOP_MD_SIZE），如果文件不存在则返回 None。
    """
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return None

    # 截断到最大大小
    if len(content) > MAX_LOOP_MD_SIZE:
        content = content[:MAX_LOOP_MD_SIZE]

    return content.strip()
