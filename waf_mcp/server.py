#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""医院 WAF FastMCP 服务定义（工具与 HTTP 健康检查）。传输方式由 waf_mcp.config 在入口选择其一。"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.version_info < (3, 10):
    print("hospital-waf MCP 需要 Python 3.10 及以上。", file=sys.stderr)
    sys.exit(1)

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from starlette.requests import Request
from starlette.responses import JSONResponse

from fastmcp import FastMCP

from version import __version__
from waf_engine import WAFEngine

_DEFAULT_MCP_RULES = _ROOT / "rules" / "waf_rules.mcp.json"


def _rules_path() -> Path:
    env = os.environ.get("WAF_RULES_FILE")
    if env:
        return Path(env).expanduser().resolve()
    return _DEFAULT_MCP_RULES.resolve()


_engine: Optional[WAFEngine] = None


def _get_engine() -> WAFEngine:
    global _engine
    if _engine is None:
        _engine = WAFEngine(str(_rules_path()))
    return _engine


def _reload_engine() -> WAFEngine:
    global _engine
    _engine = WAFEngine(str(_rules_path()))
    return _engine


mcp = FastMCP(name="hospital-waf")


@mcp.custom_route("/health", methods=["GET"])
async def mcp_health(_request: Request) -> JSONResponse:
    """供负载均衡 / 魔搭托管探活（仅在网络传输模式下由同一进程暴露）。"""
    eng = _get_engine()
    st = eng.get_stats()
    return JSONResponse(
        {
            "status": "ok",
            "service": "hospital-waf-mcp",
            "version": __version__,
            "rules_file": st.get("rules_file"),
            "compiled_rules": st.get("compiled_rules"),
            "compile_failed": st.get("compile_failed"),
        }
    )


@mcp.tool
def waf_check_request(
    url: str = "",
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: str = "",
    cookies: str = "",
) -> List[Dict[str, Any]]:
    """对 HTTP 请求做 WAF 规则检测，返回命中的告警列表（无命中则为空列表）。url 建议包含完整查询串。"""
    request_data: Dict[str, Any] = {
        "url": url,
        "method": method,
        "headers": headers or {},
        "body": body,
        "cookies": cookies,
    }
    return _get_engine().check_request(request_data)


@mcp.tool
def waf_rule_stats() -> Dict[str, Any]:
    """返回当前已加载规则的统计：含 rules_file、compiled_rules、compile_failed、compile_errors（截断）及分类计数。"""
    return _get_engine().get_stats()


@mcp.tool
def waf_reload_rules() -> Dict[str, Any]:
    """重新从磁盘加载 WAF_RULES_FILE（或默认 rules/waf_rules.mcp.json）并编译。用于修改规则文件后无需重启 MCP。"""
    eng = _reload_engine()
    stats = eng.get_stats()
    return {"success": True, "message": "规则已重新加载", "stats": stats}


@mcp.tool
def waf_run_self_tests() -> List[Dict[str, Any]]:
    """运行内置 SQLi/XSS/命令注入/路径遍历样例，用于快速验证引擎是否检出攻击。"""
    return _get_engine().test_detection()
