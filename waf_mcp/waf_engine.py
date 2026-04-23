#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WAF规则引擎 - 攻击检测引擎（医院WAF管理系统 v1.0.0）
"""

import re
import json
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

class WAFEngine:
    """WAF规则引擎"""
    
    def __init__(self, rules_file: str):
        self.rules_file = Path(rules_file)
        self.compile_failures: List[Dict] = []
        self.rules = self.load_rules()
        self.compiled_rules = self.compile_rules()
    
    def load_rules(self) -> List[Dict]:
        """加载WAF规则"""
        if not self.rules_file.exists():
            print(f"规则文件不存在: {self.rules_file}", file=sys.stderr)
            return []
        
        with open(self.rules_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    
    def compile_rules(self) -> List[Dict]:
        """编译规则（预编译正则表达式）"""
        compiled: List[Dict] = []
        failures: List[Dict[str, Any]] = []
        skipped_disabled = 0
        skipped_no_pattern = 0

        for rule in self.rules:
            if rule.get("enabled") is False:
                skipped_disabled += 1
                continue
            pattern = rule.get("pattern", "")
            if not pattern:
                skipped_no_pattern += 1
                continue

            try:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
                compiled.append({**rule, "compiled_pattern": compiled_pattern})
            except Exception as e:
                rid = rule.get("rule_id", "?")
                msg = str(e)
                print(f"规则编译失败 {rid}: {msg}", file=sys.stderr)
                failures.append({"rule_id": rid, "error": msg})

        self.compile_failures = failures
        print(
            f"✅ 编译了 {len(compiled)} 条WAF规则"
            f"（跳过禁用 {skipped_disabled}，无 pattern {skipped_no_pattern}，失败 {len(failures)}）",
            file=sys.stderr,
        )
        return compiled

    def reload(self) -> None:
        """重新从磁盘加载规则并编译。"""
        self.rules = self.load_rules()
        self.compiled_rules = self.compile_rules()
    
    def check_request(self, request_data: Dict) -> List[Dict]:
        """检查HTTP请求"""
        alerts = []
        
        # 检查URL
        url = request_data.get('url', '')
        # 检查请求体
        body = request_data.get('body', '')
        # 检查请求头
        headers = request_data.get('headers', {})
        # 检查Cookie
        cookies = request_data.get('cookies', '')
        
        for rule in self.compiled_rules:
            matched = False
            match_location = None
            
            # URL匹配
            if url and rule['compiled_pattern'].search(url):
                matched = True
                match_location = 'url'
            
            # Body匹配
            elif body and rule['compiled_pattern'].search(body):
                matched = True
                match_location = 'body'
            
            # Headers匹配
            elif headers:
                for header_name, header_value in headers.items():
                    if isinstance(header_value, str) and rule['compiled_pattern'].search(header_value):
                        matched = True
                        match_location = f'header:{header_name}'
                        break
            
            # Cookies匹配
            elif cookies and rule['compiled_pattern'].search(cookies):
                matched = True
                match_location = 'cookie'
            
            if matched:
                alerts.append({
                    'rule_id': rule.get('rule_id'),
                    'name': rule.get('name'),
                    'category': rule.get('category'),
                    'severity': rule.get('severity', 'medium'),
                    'description': rule.get('description'),
                    'action': rule.get('action', 'block'),
                    'match_location': match_location
                })
        
        return alerts
    
    def get_stats(self) -> Dict:
        """获取规则统计"""
        categories = {}
        severities = {}
        
        for rule in self.rules:
            if rule.get("enabled") is False:
                continue
            cat = rule.get("category", "other")
            sev = rule.get("severity", "medium")

            categories[cat] = categories.get(cat, 0) + 1
            severities[sev] = severities.get(sev, 0) + 1
        
        enabled_rules = [r for r in self.rules if r.get("enabled") is not False]
        return {
            "rules_file": str(self.rules_file),
            "total_rules": len(self.rules),
            "enabled_rules": len(enabled_rules),
            "compiled_rules": len(self.compiled_rules),
            "compile_failed": len(self.compile_failures),
            "compile_errors": self.compile_failures[:50],
            "categories": categories,
            "severities": severities,
        }
    
    def test_detection(self) -> List[Dict]:
        """测试WAF引擎检测能力"""
        test_cases = [
            {
                "name": "SQL注入测试",
                "request": {
                    "url": "http://example.com/login?id=1' OR '1'='1",
                    "method": "GET",
                    "headers": {"User-Agent": "Mozilla/5.0"},
                    "body": "",
                    "query_string": "id=1' OR '1'='1"
                },
                "expected": "sqli"
            },
            {
                "name": "XSS攻击测试",
                "request": {
                    "url": "http://example.com/search?q=<script>alert('xss')</script>",
                    "method": "GET",
                    "headers": {},
                    "body": "",
                    "query_string": "q=<script>alert('xss')</script>"
                },
                "expected": "xss"
            },
            {
                "name": "命令注入测试",
                "request": {
                    "url": "http://example.com/ping?host=127.0.0.1;cat /etc/passwd",
                    "method": "GET",
                    "headers": {},
                    "body": "",
                    "query_string": "host=127.0.0.1;cat /etc/passwd"
                },
                "expected": "cmdi"
            },
            {
                "name": "路径遍历测试",
                "request": {
                    "url": "http://example.com/file?path=../../../etc/passwd",
                    "method": "GET",
                    "headers": {},
                    "body": "",
                    "query_string": "path=../../../etc/passwd"
                },
                "expected": "lfi"
            }
        ]
        
        results = []
        for test in test_cases:
            alerts = self.check_request(test["request"])
            detected = len(alerts) > 0
            
            results.append({
                "test_name": test["name"],
                "expected": test["expected"],
                "detected": detected,
                "alert_count": len(alerts),
                "alerts": alerts if detected else []
            })
        
        return results
