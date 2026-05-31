"""
MCP 服务器入口

支持通过 `python -m src.mcp.server` 启动 MCP 服务器。
"""

from .server import main

if __name__ == "__main__":
    main()
