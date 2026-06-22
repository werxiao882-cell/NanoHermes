"""ScriptHook - 外部脚本拦截器包装类。

将外部脚本封装为 EventBus 拦截器，通过 subprocess 执行。
stdin 传入 JSON 上下文，stdout 接收 ChainResult。

使用方式：
    hook = ScriptHook("./scripts/validate.sh", timeout=30)
    loop.events.intercept(EventType.MODEL_REQUEST, hook, priority=5)

脚本输出格式（JSON）：
    {"block": true, "message": "拒绝原因"}  # 阻断
    {"block": false}                        # 放行
    {}                                     # 放行（默认）
"""

import json
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class ScriptHook:
    """外部脚本拦截器包装类。

    通过 subprocess 执行外部脚本，stdin 传入 JSON 上下文，
    stdout 接收阻断信号。故障隔离：脚本失败不影响主流程。

    Attributes:
        script_path: 脚本路径。
        timeout: 执行超时（秒），默认 30。
    """

    def __init__(self, script_path: str, timeout: int = 30):
        """初始化 ScriptHook。

        Args:
            script_path: 脚本路径。
            timeout: 执行超时（秒），默认 30。
        """
        self.script_path = script_path
        self.timeout = timeout

    def __call__(self, data: dict[str, Any], next_fn) -> None:
        """执行脚本，根据输出决定是否放行。

        设计理由：
        - stdin 传入 JSON 上下文，脚本可读取完整事件数据
        - stdout 解析 ChainResult，支持 block + message
        - 超时/失败/非法输出均放行（故障隔离）
        - 脚本返回非零退出码视为失败，放行

        Args:
            data: 事件数据。
            next_fn: 责任链下一个拦截器的调用函数。
        """
        try:
            proc = subprocess.run(
                [self.script_path],
                input=json.dumps(data, ensure_ascii=False),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            # 非零退出码视为失败，放行
            if proc.returncode != 0:
                logger.debug(f"ScriptHook 脚本返回非零退出码: {self.script_path}")
                next_fn()
                return

            # 解析 stdout
            output = proc.stdout.strip()
            if not output:
                # 空输出视为放行
                next_fn()
                return

            result = json.loads(output)
            if result.get("block"):
                # 阻断：不调用 next_fn
                logger.warning(f"ScriptHook 阻断: {self.script_path} - {result.get('message', '')}")
                return

            next_fn()

        except subprocess.TimeoutExpired:
            logger.warning(f"ScriptHook 执行超时 ({self.timeout}s): {self.script_path}")
            next_fn()

        except json.JSONDecodeError:
            logger.warning(f"ScriptHook stdout 非法 JSON: {self.script_path}")
            next_fn()

        except FileNotFoundError:
            logger.error(f"ScriptHook 脚本不存在: {self.script_path}")
            next_fn()

        except Exception as e:
            logger.warning(f"ScriptHook 执行失败: {self.script_path} - {e}")
            next_fn()
