#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
魔搭 / 远程 MCP 部署：每个进程仅启用一种传输（stdio | http | sse），由环境变量唯一指定。

与 ModelScope MCP 实验场对齐时，远程侧通常使用 Streamable HTTP（FastMCP 中 transport=\"http\"），
端点形如 http(s)://host:port/mcp ；旧客户端可选用 sse。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Literal

# 与 FastMCP 文档一致：Streamable HTTP 使用 transport=\"http\"，非字面量 \"streamable-http\"
TransportName = Literal["stdio", "http", "sse"]

_ALLOWED = frozenset({"stdio", "http", "sse"})
_ALIASES = {
    "streamable-http": "http",
    "streamablehttp": "http",
}


@dataclass(frozen=True)
class WAFMCPConfig:
    """单一传输配置；禁止在同一进程中混用多种传输。"""

    transport: TransportName
    host: str
    port: int


def _parse_transport(raw: str | None) -> TransportName:
    if raw is None or not str(raw).strip():
        return "stdio"
    key = str(raw).strip().lower()
    if "," in key or " " in key:
        print(
            "错误: WAF_MCP_TRANSPORT 只能为单一取值（stdio / http / sse），不能用逗号或空格列举多种。",
            file=sys.stderr,
        )
        sys.exit(2)
    key = _ALIASES.get(key, key)
    if key not in _ALLOWED:
        print(
            f"错误: 未知 WAF_MCP_TRANSPORT={raw!r}，允许: stdio | http | sse（http 即魔搭 Streamable HTTP）",
            file=sys.stderr,
        )
        sys.exit(2)
    return key  # type: ignore[return-value]


def load_waf_mcp_config() -> WAFMCPConfig:
    transport = _parse_transport(os.environ.get("WAF_MCP_TRANSPORT"))
    host = os.environ.get("WAF_MCP_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port_s = os.environ.get("WAF_MCP_PORT", "8000").strip() or "8000"
    try:
        port = int(port_s)
    except ValueError:
        print(f"错误: WAF_MCP_PORT 必须为整数，当前为 {port_s!r}", file=sys.stderr)
        sys.exit(2)
    if not (1 <= port <= 65535):
        print(f"错误: WAF_MCP_PORT 越界: {port}", file=sys.stderr)
        sys.exit(2)
    return WAFMCPConfig(transport=transport, host=host, port=port)
