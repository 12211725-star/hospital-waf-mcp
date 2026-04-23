#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 knowledge-base/waf_rules.json 抽取可在 Python re 下编译的规则，生成 rules/waf_rules.mcp.json。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent


def normalize_pattern(raw: str) -> Optional[str]:
    """将 ModSecurity 风格操作符转为 Python 正则，无法转换则返回 None。"""
    p = raw.strip()
    if not p:
        return None

    if p.startswith("!@rx ") or p.startswith("!@within "):
        return None

    if p.startswith("@rx "):
        return p[4:].strip()

    if p.startswith("@streq "):
        return re.escape(p[7:])

    # 不支持的运算符：交给 None，避免误用
    if re.match(r"^[@!]", p) and not p.startswith("'"):
        if p.startswith(
            (
                "@pm ",
                "@pmf ",
                "@contains ",
                "@within ",
                "@ipMatch ",
                "@lt ",
                "@gt ",
                "@eq ",
                "@validateByteRange ",
            )
        ):
            return None
        if p.startswith("@rx") is False and p[0] == "@":
            return None

    return p


def rule_compiles(rule: Dict[str, Any], pattern: str) -> bool:
    try:
        re.compile(pattern, re.IGNORECASE)
    except re.error:
        return False
    return True


def load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--source",
        type=Path,
        default=ROOT / "knowledge-base" / "waf_rules.json",
        help="原始规则 JSON（列表）",
    )
    ap.add_argument(
        "--supplement",
        type=Path,
        default=ROOT / "rules" / "hospital_supplement.json",
        help="医院场景增补规则（可选，不存在则忽略）",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=ROOT / "rules" / "waf_rules.mcp.json",
        help="输出 MCP 规则文件",
    )
    args = ap.parse_args()

    if not args.source.is_file():
        print(f"源文件不存在: {args.source}", file=sys.stderr)
        return 1

    raw_rules: List[Dict[str, Any]] = load_json(args.source)
    if not isinstance(raw_rules, list):
        print("源文件必须是规则数组", file=sys.stderr)
        return 1

    out: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    for rule in raw_rules:
        rid = rule.get("rule_id")
        if not rid or rid in seen_ids:
            continue
        pat_raw = rule.get("pattern") or ""
        normalized = normalize_pattern(pat_raw) if isinstance(pat_raw, str) else None
        if not normalized:
            continue
        if "%{" in normalized:
            continue
        if not rule_compiles(rule, normalized):
            continue

        entry = {k: v for k, v in rule.items() if k != "compiled_pattern"}
        entry["pattern"] = normalized
        if "enabled" not in entry:
            entry["enabled"] = True
        out.append(entry)
        seen_ids.add(str(rid))

    if args.supplement.is_file():
        extra: List[Dict[str, Any]] = load_json(args.supplement)
        if isinstance(extra, list):
            for rule in extra:
                rid = rule.get("rule_id")
                pat = rule.get("pattern")
                if not rid or rid in seen_ids or not pat:
                    continue
                if not rule_compiles(rule, str(pat)):
                    print(f"增补规则编译失败，已跳过: {rid}", file=sys.stderr)
                    continue
                entry = {k: v for k, v in rule.items() if k != "compiled_pattern"}
                if "enabled" not in entry:
                    entry["enabled"] = True
                out.append(entry)
                seen_ids.add(str(rid))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(
        f"写入 {args.output}，共 {len(out)} 条可编译规则（源 {len(raw_rules)} 条）",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
