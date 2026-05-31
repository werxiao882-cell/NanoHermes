"""
传输模式配置和路由

支持 3 种 MCP 官方传输模式：
- Stdio（本地必选）
- Streamable HTTP（网络推荐）
- HTTP+SSE（旧版兼容）
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class TransportMode(str, Enum):
    """MCP 传输模式枚举"""
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable-http"
    SSE = "sse"


@dataclass
class TransportConfig:
    """传输配置"""
    mode: TransportMode
    host: str = "0.0.0.0"
    port: int = 8000
    path: str = "/mcp"

    @classmethod
    def from_args(cls, transport: str = "stdio", host: str = "0.0.0.0", port: int = 8000, path: str = "/mcp") -> "TransportConfig":
        """从命令行参数创建配置"""
        mode = TransportMode(transport)
        return cls(mode=mode, host=host, port=port, path=path)

    def get_server_url(self) -> str:
        """获取服务器 URL（HTTP 模式）"""
        if self.mode == TransportMode.STDIO:
            raise ValueError("Stdio 模式不支持 URL")
        return f"http://{self.host}:{self.port}{self.path}"
