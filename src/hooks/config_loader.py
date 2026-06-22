"""Hook 配置加载器。

从 settings（nanohermes.json）加载 hook 配置，自动注册到 EventBus。

配置格式：
{
  "hooks": {
    "model_request": [
      {"type": "script", "path": "./scripts/validate.sh", "timeout": 30}
    ],
    "tool_start": [
      {"type": "python", "module": "my_hooks", "function": "check_tool", "priority": 5}
    ]
  }
}

EventType 映射：
  model_request -> EventType.MODEL_REQUEST
  tool_start    -> EventType.TOOL_START
  ...（下划线转大写）
"""

import importlib
import logging
from typing import Any

from src.conversation.events import EventBus, EventType
from src.hooks.script_hook import ScriptHook

logger = logging.getLogger(__name__)

# EventType 名称映射（小写下划线 -> Enum 成员名）
_EVENT_TYPE_MAP: dict[str, EventType] = {
    e.value: e for e in EventType
}


def load_hooks_from_config(config: dict[str, Any], event_bus: EventBus) -> None:
    """从 settings 加载 hook 配置并注册到 EventBus。

    设计理由：
    - 支持 script 和 python 两种 handler 类型
    - script 类型创建 ScriptHook 包装类
    - python 类型动态导入模块函数
    - 配置加载失败不影响主流程（故障隔离）

    Args:
        config: settings 配置字典（包含 hooks 字段）。
        event_bus: EventBus 实例。
    """
    hooks_config = config.get("hooks", {})
    if not hooks_config:
        return

    for event_name, handlers in hooks_config.items():
        event_type = _EVENT_TYPE_MAP.get(event_name)
        if not event_type:
            logger.warning(f"未知的事件类型: {event_name}")
            continue

        if not isinstance(handlers, list):
            logger.warning(f"hooks.{event_name} 应为列表: {handlers}")
            continue

        for handler_cfg in handlers:
            try:
                handler = _create_handler(handler_cfg)
                if handler:
                    priority = handler_cfg.get("priority", 0)
                    event_bus.intercept(event_type, handler, priority=priority)
                    logger.debug(f"注册 hook: {event_name} (priority={priority})")
            except Exception as e:
                logger.warning(f"加载 hook 配置失败: {event_name} - {handler_cfg} - {e}")


def _create_handler(handler_cfg: dict[str, Any]):
    """根据配置创建 handler 函数。

    Args:
        handler_cfg: handler 配置字典。

    Returns:
        handler 函数，或 None（如果配置无效）。
    """
    handler_type = handler_cfg.get("type", "")

    if handler_type == "script":
        path = handler_cfg.get("path", "")
        if not path:
            logger.warning("ScriptHook 配置缺少 path")
            return None
        timeout = handler_cfg.get("timeout", 30)
        return ScriptHook(path, timeout=timeout)

    elif handler_type == "python":
        module_name = handler_cfg.get("module", "")
        function_name = handler_cfg.get("function", "")
        if not module_name or not function_name:
            logger.warning("Python hook 配置缺少 module 或 function")
            return None

        try:
            module = importlib.import_module(module_name)
            return getattr(module, function_name)
        except (ImportError, AttributeError) as e:
            logger.warning(f"导入 Python hook 失败: {module_name}.{function_name} - {e}")
            return None

    else:
        logger.warning(f"未知的 hook 类型: {handler_type}")
        return None
