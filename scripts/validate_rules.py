#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验规则 JSON：每条启用规则须含可被 Python re 编译的 pattern。失败则退出码 1。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "rules_file",
        type=Path,
        nargs="?",
        default=ROOT / "rules" / "waf_rules.mcp.json",
    )
    args = ap.parse_args()

    if not args.rules_file.is_file():
        print(f"文件不存在: {args.rules_file}", file=sys.stderr)
        return 1

    with open(args.rules_file, encoding="utf-8") as f:
        rules = json.load(f)
    if not isinstance(rules, list):
        print("规则文件必须是 JSON 数组", file=sys.stderr)
        return 1

    errors: list[str] = []
    for rule in rules:
        if rule.get("enabled") is False:
            continue
        rid = rule.get("rule_id", "?")
        pat = rule.get("pattern", "")
        if not pat:
            errors.append(f"{rid}: 缺少 pattern")
            continue
        try:
            re.compile(pat, re.IGNORECASE)
        except re.error as e:
            errors.append(f"{rid}: {e}")

    if errors:
        print(f"校验失败，共 {len(errors)} 条:", file=sys.stderr)
        for line in errors[:100]:
            print(f"  {line}", file=sys.stderr)
        if len(errors) > 100:
            print(f"  ... 另有 {len(errors) - 100} 条", file=sys.stderr)
        return 1

    print(f"✅ {args.rules_file}: {len(rules)} 条规则校验通过", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
