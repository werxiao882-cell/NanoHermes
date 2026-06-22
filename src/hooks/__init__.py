"""Hooks 模块。

提供 EventBus 责任链拦截器的具体实现。

组件：
- dangerous_command_guard: 危险命令拦截器，复用 terminal.py 的 DANGEROUS_PATTERNS
- script_hook: ScriptHook 包装类，将外部脚本封装为拦截器
- config_loader: 从 settings 加载 hook 配置并自动注册
"""

from src.hooks.dangerous_command_guard import dangerous_command_guard
from src.hooks.script_hook import ScriptHook
from src.hooks.config_loader import load_hooks_from_config

__all__ = [
    "dangerous_command_guard",
    "ScriptHook",
    "load_hooks_from_config",
]
