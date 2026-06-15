"""后台任务调度模块。

提供统一的后台任务调度框架，管理记忆刷写、技能审查等后台任务。

公共 API：
- BackgroundTaskScheduler: 后台任务调度器
- run_background_review(): 同步执行后台审查（供调度器 handler 调用）
- spawn_background_review(): 在后台线程中启动审查（独立使用）
- fork_agent(): 创建简化的子代理，支持工具调用循环
- register_memory_flush_task(): 注册记忆刷写任务
- register_skill_review_task(): 注册技能审查任务
"""

from src.background.scheduler import BackgroundTaskScheduler
from src.background.review import (
    run_background_review,
    spawn_background_review,
    fork_agent,
    build_review_prompt,
    format_conversation,
    REVIEW_TOOL_WHITELIST,
    MEMORY_REVIEW_PROMPT,
    SKILL_REVIEW_PROMPT,
)
from src.background.memory_flush import (
    memory_flush_handler,
    memory_flush_trigger,
    register_memory_flush_task,
    MEMORY_FLUSH_MIN_MESSAGES,
)
from src.background.skill_review import (
    skill_review_handler,
    skill_review_trigger,
    register_skill_review_task,
    reset_last_review_time,
    SKILL_REVIEW_MIN_TURNS,
    SKILL_REVIEW_MIN_INTERVAL_SECONDS,
)

__all__ = [
    # 调度器
    "BackgroundTaskScheduler",
    # 审查核心
    "run_background_review",
    "spawn_background_review",
    "fork_agent",
    "build_review_prompt",
    "format_conversation",
    "REVIEW_TOOL_WHITELIST",
    "MEMORY_REVIEW_PROMPT",
    "SKILL_REVIEW_PROMPT",
    # 记忆刷写
    "memory_flush_handler",
    "memory_flush_trigger",
    "register_memory_flush_task",
    "MEMORY_FLUSH_MIN_MESSAGES",
    # 技能审查
    "skill_review_handler",
    "skill_review_trigger",
    "register_skill_review_task",
    "reset_last_review_time",
    "SKILL_REVIEW_MIN_TURNS",
    "SKILL_REVIEW_MIN_INTERVAL_SECONDS",
]
