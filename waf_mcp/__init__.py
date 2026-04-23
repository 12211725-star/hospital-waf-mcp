# Hospital WAF MCP（FastMCP）。传输：见 WAF_MCP_TRANSPORT（stdio | http | sse）。
# 运行：python -m waf_mcp
from version import __version__

from waf_mcp.server import mcp

__all__ = ["mcp", "__version__"]
