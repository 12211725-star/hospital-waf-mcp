#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院 WAF MCP 入口：每个进程仅使用一种传输（stdio / http / sse），由 WAF_MCP_TRANSPORT 指定。

- stdio：本地 IDE（如 Cursor）子进程方式，默认。
- http：魔搭 / 远程场景推荐的 Streamable HTTP（FastMCP transport=\"http\"），MCP 端点 http(s)://host:port/mcp
- sse：兼容旧版仅支持 SSE 的客户端（不推荐新集成）
"""

from __future__ import annotations

import sys

from waf_mcp.config import load_waf_mcp_config
from waf_mcp.server import mcp


def main() -> None:
    cfg = load_waf_mcp_config()

    if cfg.transport == "stdio":
        mcp.run()
        return

    # 网络传输：单一端口、单一协议，与魔搭「自定义 MCP」二选一（http 或 sse）一致
    mcp.run(transport=cfg.transport, host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
