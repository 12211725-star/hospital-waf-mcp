#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""医院 WAF 功能测试：规则校验、引擎自检、FastAPI 关键接口。无需 pytest。

用法：在项目根目录执行  python3 scripts/run_functional_tests.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    def ok(name: str) -> None:
        print(f"  PASS  {name}")

    def fail(name: str, msg: str) -> int:
        print(f"  FAIL  {name}: {msg}", file=sys.stderr)
        return 1

    print("[1] scripts/validate_rules.py")
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_rules.py")],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return fail("validate_rules", r.stderr or r.stdout)
    ok("validate_rules.py exit 0")

    print("[2] WAFEngine")
    sys.path.insert(0, str(ROOT))
    from waf_engine import WAFEngine

    eng = WAFEngine(str(ROOT / "rules" / "waf_rules.mcp.json"))
    st = eng.get_stats()
    if st.get("compile_failed", -1) != 0:
        return fail("compile_failed", str(st.get("compile_errors")))
    if st.get("compiled_rules", 0) < 1:
        return fail("compiled_rules", str(st))
    ok(f"stats compiled={st['compiled_rules']} failed={st['compile_failed']}")

    for row in eng.test_detection():
        if not row.get("detected"):
            return fail("test_detection", json.dumps(row, ensure_ascii=False))
    ok("test_detection 4/4 detected")

    sqli = eng.check_request(
        {
            "url": "http://evil.test/q?id=1' OR '1'='1",
            "body": "",
            "headers": {},
            "cookies": "",
        }
    )
    if not sqli:
        return fail("sqli sample", "no alerts")
    ok(f"sqli sample alerts={len(sqli)}")

    print("[3] FastAPI routes")
    from fastapi.testclient import TestClient

    import app as waf_app

    client = TestClient(waf_app.app)

    h = client.get("/health")
    if h.status_code != 200 or h.json().get("status") != "healthy":
        return fail("/health", f"{h.status_code} {h.text[:200]}")
    ok("/health")

    ws = client.get("/api/waf-stats")
    if ws.status_code != 200 or not ws.json().get("success"):
        return fail("/api/waf-stats", ws.text[:300])
    d = ws.json().get("data", {})
    if d.get("compile_failed") != 0:
        return fail("waf-stats compile_failed", str(d))
    ok("/api/waf-stats")

    tw = client.post("/api/test-waf")
    if tw.status_code != 200 or not tw.json().get("success"):
        return fail("/api/test-waf", tw.text[:300])
    for item in tw.json().get("data", []):
        if not item.get("detected"):
            return fail("/api/test-waf item", json.dumps(item, ensure_ascii=False))
    ok("/api/test-waf")

    cr = client.post(
        "/api/check-request",
        json={
            "url": "http://evil.test/q?id=1' OR '1'='1",
            "method": "GET",
            "headers": {},
            "body": "",
            "cookies": "",
        },
    )
    if cr.status_code != 200:
        return fail("/api/check-request status", str(cr.status_code))
    cj = cr.json()
    if not cj.get("success") or cj.get("alert_count", 0) < 1:
        return fail("/api/check-request body", str(cj)[:400])
    ok("/api/check-request")

    lo = client.post(
        "/api/login", json={"username": "admin", "password": "wrong", "captcha": ""}
    )
    if lo.status_code != 200:
        return fail("/api/login status", str(lo.status_code))
    if lo.json().get("success") is not False:
        return fail("/api/login should fail", str(lo.json()))
    ok("/api/login wrong password")

    print("[4] waf_mcp (optional)")
    try:
        import fastmcp  # noqa: F401
    except ImportError:
        print("  SKIP  fastmcp not installed (pip install -r requirements-mcp.txt)")
    else:
        from waf_mcp.server import mcp as _mcp  # noqa: WPS433

        _ = _mcp
        ok("waf_mcp.server import")

    print("\n全部功能测试通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
