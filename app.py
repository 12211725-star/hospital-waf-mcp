#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院WAF管理系统 v1.0.0 - 主程序（等保2.0二级合规版）
功能：Web应用防火墙规则管理、攻击日志、黑白名单、实时监控
"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import json
import uuid
import re
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import random
import string
import io
from PIL import Image, ImageDraw, ImageFont

# BASE_DIR 定义
BASE_DIR = Path(__file__).resolve().parent

from version import __version__

# 导入WAF引擎
from waf_engine import WAFEngine

# MCP 兼容规则（方案 A）：rules/waf_rules.mcp.json，可用环境变量 WAF_RULES_FILE 覆盖
_waf_rules_env = os.environ.get("WAF_RULES_FILE")
WAF_ENGINE_RULES_FILE = (
    Path(_waf_rules_env).expanduser().resolve()
    if _waf_rules_env
    else (BASE_DIR / "rules" / "waf_rules.mcp.json").resolve()
)

# 知识库管理API
import sys
sys.path.insert(0, str(BASE_DIR))
try:
    from knowledge_base_routes import create_kb_router
    KB_ROUTER_AVAILABLE = True
except ImportError:
    KB_ROUTER_AVAILABLE = False

app = FastAPI(
    title=f"医院WAF管理系统 v{__version__} - 等保合规版",
    version=__version__,
)
# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



waf_engine = WAFEngine(str(WAF_ENGINE_RULES_FILE))

# 注册知识库管理路由
if KB_ROUTER_AVAILABLE:
    try:
        kb_router = create_kb_router(str(BASE_DIR), "WAF管理系统")
        app.include_router(kb_router)
    except Exception as e:
        print(f"知识库路由注册失败: {e}")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

# 数据存储
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
ATTACK_LOGS_FILE = DATA_DIR / "attack_logs.json"
WAF_RULES_FILE = DATA_DIR / "waf_rules.json"
IP_BLACKLIST_FILE = DATA_DIR / "ip_blacklist.json"
IP_WHITELIST_FILE = DATA_DIR / "ip_whitelist.json"
USERS_FILE = DATA_DIR / "users.json"
AUDIT_LOGS_FILE = DATA_DIR / "audit_logs.json"
LOGIN_LOGS_FILE = DATA_DIR / "login_logs.json"


class LoginRequest(BaseModel):
    username: str
    password: str
    captcha: Optional[str] = ""


class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str
    real_name: str


class AddIPRequest(BaseModel):
    ip: str
    reason: str
    expire_days: Optional[int] = 30


class RuleUpdateRequest(BaseModel):
    rule_id: str
    enabled: bool


# ==================== 数据管理 ====================

def load_json(file_path):
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_users():
    users = load_json(USERS_FILE)
    if not users:
        users = [{
            "user_id": "admin",
            "username": "admin",
            "password": hash_password("Admin@123"),
            "role": "admin",
            "real_name": "系统管理员",
            "must_change_password": True,
            "last_password_change": datetime.now().isoformat(),
            "login_failed_count": 0,
            "locked_until": None,
            "created_at": datetime.now().isoformat()
        }]
        save_json(USERS_FILE, users)
    return users


def save_users(users):
    save_json(USERS_FILE, users)


def load_attack_logs():
    logs = load_json(ATTACK_LOGS_FILE)
    if not logs:
        # 生成模拟攻击日志
        logs = generate_mock_attack_logs()
        save_json(ATTACK_LOGS_FILE, logs)
    return logs


def load_waf_rules():
    rules = load_json(WAF_RULES_FILE)
    if not rules:
        rules = generate_default_rules()
        save_json(WAF_RULES_FILE, rules)
    return rules


def load_ip_blacklist():
    return load_json(IP_BLACKLIST_FILE)


def load_ip_whitelist():
    return load_json(IP_WHITELIST_FILE)


def save_audit_log(log_entry):
    logs = load_json(AUDIT_LOGS_FILE)
    logs.append(log_entry)
    if len(logs) > 10000:
        logs = logs[-10000:]
    save_json(AUDIT_LOGS_FILE, logs)


def save_login_log(log_entry):
    logs = load_json(LOGIN_LOGS_FILE)
    logs.append(log_entry)
    if len(logs) > 10000:
        logs = logs[-10000:]
    save_json(LOGIN_LOGS_FILE, logs)


# ==================== 安全功能 ====================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def check_password_complexity(password: str) -> tuple:
    if len(password) < 8:
        return False, "密码长度至少8位"
    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含大写字母"
    if not re.search(r'[a-z]', password):
        return False, "密码必须包含小写字母"
    if not re.search(r'[0-9]', password):
        return False, "密码必须包含数字"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码必须包含特殊字符"
    return True, "密码强度符合要求"


def check_user_locked(user: dict) -> tuple:
    if user.get('locked_until'):
        locked_until = datetime.fromisoformat(user['locked_until'])
        if datetime.now() < locked_until:
            remaining = int((locked_until - datetime.now()).total_seconds() / 60)
            return True, f"账号已锁定，请{remaining}分钟后再试"
        else:
            user['locked_until'] = None
            user['login_failed_count'] = 0
            return False, ""
    return False, ""


def record_login_failed(user: dict):
    user['login_failed_count'] = user.get('login_failed_count', 0) + 1
    if user['login_failed_count'] >= 5:
        user['locked_until'] = (datetime.now() + timedelta(minutes=30)).isoformat()
        user['login_failed_count'] = 0


def check_password_expired(user: dict) -> bool:
    last_change = datetime.fromisoformat(user.get('last_password_change', datetime.now().isoformat()))
    return (datetime.now() - last_change).days > 90


# ==================== 模拟数据生成 ====================

def generate_mock_attack_logs():
    """生成模拟攻击日志"""
    attack_types = [
        ("SQL注入", "sqli", "SELECT * FROM users WHERE id=1' OR '1'='1"),
        ("XSS攻击", "xss", "<script>alert('XSS')</script>"),
        ("命令注入", "cmdi", "; cat /etc/passwd"),
        ("路径遍历", "lfi", "../../../etc/passwd"),
        ("CSRF攻击", "csrf", "POST /admin/delete?id=1"),
        ("文件上传", "upload", "恶意文件上传尝试"),
        ("暴力破解", "brute", "连续登录失败"),
        ("目录扫描", "scan", "敏感目录扫描"),
    ]

    logs = []
    now = datetime.now()

    # 生成最近7天的攻击日志
    for i in range(200):
        attack_type, attack_id, payload = random.choice(attack_types)
        hours_ago = random.randint(0, 168)  # 最近7天
        attack_time = now - timedelta(hours=hours_ago)

        log = {
            "log_id": str(uuid.uuid4()),
            "attack_time": attack_time.isoformat(),
            "attack_type": attack_type,
            "attack_id": attack_id,
            "source_ip": f"192.168.{random.randint(1,254)}.{random.randint(1,254)}",
            "target_url": f"/api/{random.choice(['login', 'search', 'upload', 'admin'])}",
            "payload": payload,
            "severity": random.choice(["high", "medium", "low"]),
            "action": random.choice(["blocked", "blocked", "blocked", "alert"]),
            "rule_id": f"rule-{attack_id}-001"
        }
        logs.append(log)

    return sorted(logs, key=lambda x: x['attack_time'], reverse=True)


def generate_default_rules():
    """生成默认WAF规则"""
    rules = [
        {"rule_id": "rule-sqli-001", "name": "SQL注入防护", "category": "注入攻击", "enabled": True, "severity": "high", "description": "检测SQL注入攻击"},
        {"rule_id": "rule-sqli-002", "name": "SQL注入防护-Union", "category": "注入攻击", "enabled": True, "severity": "high", "description": "检测Union注入"},
        {"rule_id": "rule-xss-001", "name": "XSS攻击防护", "category": "跨站脚本", "enabled": True, "severity": "high", "description": "检测XSS攻击"},
        {"rule_id": "rule-xss-002", "name": "XSS攻击防护-标签", "category": "跨站脚本", "enabled": True, "severity": "high", "description": "检测恶意HTML标签"},
        {"rule_id": "rule-cmdi-001", "name": "命令注入防护", "category": "注入攻击", "enabled": True, "severity": "high", "description": "检测系统命令注入"},
        {"rule_id": "rule-lfi-001", "name": "路径遍历防护", "category": "文件包含", "enabled": True, "severity": "medium", "description": "检测目录遍历攻击"},
        {"rule_id": "rule-upload-001", "name": "恶意文件上传防护", "category": "文件上传", "enabled": True, "severity": "high", "description": "检测恶意文件上传"},
        {"rule_id": "rule-scan-001", "name": "目录扫描防护", "category": "扫描攻击", "enabled": True, "severity": "low", "description": "检测敏感目录扫描"},
        {"rule_id": "rule-brute-001", "name": "暴力破解防护", "category": "暴力破解", "enabled": True, "severity": "medium", "description": "检测暴力破解攻击"},
        {"rule_id": "rule-csrf-001", "name": "CSRF防护", "category": "跨站请求", "enabled": True, "severity": "medium", "description": "检测CSRF攻击"},
    ]
    return rules


# ==================== 验证码 ====================

# 验证码存储（简单实现，生产环境应使用Redis）
captcha_store = {}

@app.get("/api/captcha")
async def get_captcha():
    """生成验证码图片"""
    # 生成4位随机验证码
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    captcha_id = str(uuid.uuid4())
    
    # 存储验证码（5分钟有效）
    captcha_store[captcha_id] = {
        "code": code.lower(),
        "expire": datetime.now() + timedelta(minutes=5)
    }
    
    # 创建图片
    width, height = 120, 40
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # 尝试使用系统字体
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except:
        font = ImageFont.load_default()
    
    # 绘制验证码文本
    for i, char in enumerate(code):
        x = 10 + i * 25
        y = random.randint(2, 8)
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        draw.text((x, y), char, font=font, fill=color)
    
    # 添加干扰线
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)
    
    # 返回图片
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    response = Response(content=img_io.getvalue(), media_type="image/png")
    response.headers["X-Captcha-Id"] = captcha_id
    return response


# ==================== 页面路由 ====================

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/attacks", response_class=HTMLResponse)
async def attacks_page(request: Request):
    return templates.TemplateResponse("attacks.html", {"request": request})


@app.get("/rules", response_class=HTMLResponse)
async def rules_page(request: Request):
    return templates.TemplateResponse("rules.html", {"request": request})


@app.get("/blacklist", response_class=HTMLResponse)
async def blacklist_page(request: Request):
    return templates.TemplateResponse("blacklist.html", {"request": request})


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    users = load_users()
    for user in users:
        user.pop('password', None)
    return templates.TemplateResponse("users.html", {"request": request, "users": users})


@app.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request):
    login_logs = load_json(LOGIN_LOGS_FILE)[-100:]
    audit_logs = load_json(AUDIT_LOGS_FILE)[-100:]
    return templates.TemplateResponse("audit.html", {
        "request": request,
        "login_logs": login_logs,
        "audit_logs": audit_logs
    })


@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    return templates.TemplateResponse("change-password.html", {"request": request})


# ==================== API 路由 ====================

@app.post("/api/login")
async def login(request: LoginRequest):
    users = load_users()
    username = request.username
    password = request.password

    login_log = {
        "log_id": str(uuid.uuid4()),
        "username": username,
        "login_time": datetime.now().isoformat(),
        "login_result": "failed",
        "fail_reason": "",
        "ip_address": "127.0.0.1"
    }

    user = next((u for u in users if u['username'] == username), None)

    if not user:
        login_log["fail_reason"] = "用户不存在"
        save_login_log(login_log)
        return {"success": False, "message": "用户名或密码错误"}

    is_locked, lock_msg = check_user_locked(user)
    if is_locked:
        login_log["fail_reason"] = "账号锁定"
        save_login_log(login_log)
        return {"success": False, "message": lock_msg}

    if user['password'] != hash_password(password):
        record_login_failed(user)
        save_users(users)

        login_log["fail_reason"] = "密码错误"
        save_login_log(login_log)

        remaining = 5 - user.get('login_failed_count', 0)
        return {"success": False, "message": f"用户名或密码错误，剩余{remaining}次机会"}

    user['login_failed_count'] = 0
    user['locked_until'] = None
    save_users(users)

    login_log["login_result"] = "success"
    save_login_log(login_log)

    password_expired = check_password_expired(user)
    must_change = user.get('must_change_password', False)

    return {
        "success": True,
        "message": "登录成功",
        "must_change_password": must_change or password_expired,
        "user": {
            "username": user['username'],
            "role": user['role'],
            "real_name": user['real_name']
        }
    }


@app.post("/api/change-password")
async def change_password(request: ChangePasswordRequest):
    users = load_users()

    user = next((u for u in users if u['username'] == request.username), None)
    if not user:
        return {"success": False, "message": "用户不存在"}

    if user['password'] != hash_password(request.old_password):
        return {"success": False, "message": "原密码错误"}

    is_valid, msg = check_password_complexity(request.new_password)
    if not is_valid:
        return {"success": False, "message": msg}

    if user['password'] == hash_password(request.new_password):
        return {"success": False, "message": "新密码不能与旧密码相同"}

    user['password'] = hash_password(request.new_password)
    user['must_change_password'] = False
    user['last_password_change'] = datetime.now().isoformat()
    save_users(users)

    save_audit_log({
        "log_id": str(uuid.uuid4()),
        "username": request.username,
        "action": "change_password",
        "action_time": datetime.now().isoformat(),
        "action_detail": "用户修改密码",
        "ip_address": "127.0.0.1"
    })

    return {"success": True, "message": "密码修改成功"}


@app.post("/api/users/create")
async def create_user(request: CreateUserRequest):
    users = load_users()

    if any(u['username'] == request.username for u in users):
        return {"success": False, "message": "用户名已存在"}

    is_valid, msg = check_password_complexity(request.password)
    if not is_valid:
        return {"success": False, "message": msg}

    new_user = {
        "user_id": str(uuid.uuid4()),
        "username": request.username,
        "password": hash_password(request.password),
        "role": request.role,
        "real_name": request.real_name,
        "must_change_password": True,
        "last_password_change": datetime.now().isoformat(),
        "login_failed_count": 0,
        "locked_until": None,
        "created_at": datetime.now().isoformat()
    }

    users.append(new_user)
    save_users(users)

    save_audit_log({
        "log_id": str(uuid.uuid4()),
        "username": "admin",
        "action": "create_user",
        "action_time": datetime.now().isoformat(),
        "action_detail": f"创建用户: {request.username}",
        "ip_address": "127.0.0.1"
    })

    return {"success": True, "message": "用户创建成功"}


@app.delete("/api/users/{username}")
async def delete_user(username: str):
    if username == "admin":
        return {"success": False, "message": "不能删除管理员账号"}

    users = load_users()
    users = [u for u in users if u['username'] != username]
    save_users(users)

    save_audit_log({
        "log_id": str(uuid.uuid4()),
        "username": "admin",
        "action": "delete_user",
        "action_time": datetime.now().isoformat(),
        "action_detail": f"删除用户: {username}",
        "ip_address": "127.0.0.1"
    })

    return {"success": True}


@app.get("/api/users")
async def get_users():
    users = load_users()
    for user in users:
        user.pop('password', None)
    return {"success": True, "data": users}


@app.get("/api/stats")
async def get_stats():
    logs = load_attack_logs()
    rules = load_waf_rules()
    blacklist = load_ip_blacklist()
    users = load_users()
    login_logs = load_json(LOGIN_LOGS_FILE)

    # 今日攻击统计
    today = datetime.now().strftime('%Y-%m-%d')
    today_attacks = [l for l in logs if l['attack_time'].startswith(today)]
    blocked_attacks = [l for l in today_attacks if l['action'] == 'blocked']

    # 攻击类型统计
    attack_types = {}
    for log in today_attacks:
        at = log['attack_type']
        attack_types[at] = attack_types.get(at, 0) + 1

    # 高危攻击
    high_risk = [l for l in today_attacks if l['severity'] == 'high']

    # 规则统计
    enabled_rules = len([r for r in rules if r['enabled']])

    return {
        "success": True,
        "data": {
            "total_attacks": len(logs),
            "today_attacks": len(today_attacks),
            "blocked_attacks": len(blocked_attacks),
            "high_risk_attacks": len(high_risk),
            "attack_types": attack_types,
            "total_rules": len(rules),
            "enabled_rules": enabled_rules,
            "blacklist_count": len(blacklist),
            "total_users": len(users),
            "today_logins": len([l for l in login_logs if l['login_time'].startswith(today) and l['login_result'] == 'success'])
        }
    }


@app.get("/api/attacks")
async def get_attacks(limit: int = 100, attack_type: str = None, severity: str = None):
    logs = load_attack_logs()

    if attack_type:
        logs = [l for l in logs if l['attack_type'] == attack_type]
    if severity:
        logs = [l for l in logs if l['severity'] == severity]

    return {"success": True, "data": logs[:limit]}


@app.get("/api/rules")
async def get_rules():
    rules = load_waf_rules()
    return {"success": True, "data": rules}


@app.post("/api/rules/toggle")
async def toggle_rule(request: RuleUpdateRequest):
    rules = load_waf_rules()

    for rule in rules:
        if rule['rule_id'] == request.rule_id:
            rule['enabled'] = request.enabled
            save_json(WAF_RULES_FILE, rules)

            save_audit_log({
                "log_id": str(uuid.uuid4()),
                "username": "admin",
                "action": "toggle_rule",
                "action_time": datetime.now().isoformat(),
                "action_detail": f"{'启用' if request.enabled else '禁用'}规则: {rule['name']}",
                "ip_address": "127.0.0.1"
            })

            return {"success": True, "message": f"规则已{'启用' if request.enabled else '禁用'}"}

    return {"success": False, "message": "规则不存在"}


@app.get("/api/blacklist")
async def get_blacklist():
    blacklist = load_ip_blacklist()
    return {"success": True, "data": blacklist}


@app.post("/api/blacklist/add")
async def add_to_blacklist(request: AddIPRequest):
    blacklist = load_ip_blacklist()

    if any(b['ip'] == request.ip for b in blacklist):
        return {"success": False, "message": "IP已在黑名单中"}

    entry = {
        "id": str(uuid.uuid4()),
        "ip": request.ip,
        "reason": request.reason,
        "added_time": datetime.now().isoformat(),
        "expire_time": (datetime.now() + timedelta(days=request.expire_days)).isoformat() if request.expire_days > 0 else None,
        "added_by": "admin"
    }

    blacklist.append(entry)
    save_json(IP_BLACKLIST_FILE, blacklist)

    save_audit_log({
        "log_id": str(uuid.uuid4()),
        "username": "admin",
        "action": "add_blacklist",
        "action_time": datetime.now().isoformat(),
        "action_detail": f"添加IP到黑名单: {request.ip}",
        "ip_address": "127.0.0.1"
    })

    return {"success": True, "message": "IP已添加到黑名单"}


@app.delete("/api/blacklist/{ip}")
async def remove_from_blacklist(ip: str):
    blacklist = load_ip_blacklist()
    blacklist = [b for b in blacklist if b['ip'] != ip]
    save_json(IP_BLACKLIST_FILE, blacklist)

    save_audit_log({
        "log_id": str(uuid.uuid4()),
        "username": "admin",
        "action": "remove_blacklist",
        "action_time": datetime.now().isoformat(),
        "action_detail": f"从黑名单移除IP: {ip}",
        "ip_address": "127.0.0.1"
    })

    return {"success": True}


@app.get("/api/whitelist")
async def get_whitelist():
    whitelist = load_ip_whitelist()
    return {"success": True, "data": whitelist}


@app.post("/api/whitelist/add")
async def add_to_whitelist(request: AddIPRequest):
    whitelist = load_ip_whitelist()

    if any(w['ip'] == request.ip for w in whitelist):
        return {"success": False, "message": "IP已在白名单中"}

    entry = {
        "id": str(uuid.uuid4()),
        "ip": request.ip,
        "reason": request.reason,
        "added_time": datetime.now().isoformat(),
        "added_by": "admin"
    }

    whitelist.append(entry)
    save_json(IP_WHITELIST_FILE, whitelist)

    return {"success": True, "message": "IP已添加到白名单"}


@app.delete("/api/whitelist/{ip}")
async def remove_from_whitelist(ip: str):
    whitelist = load_ip_whitelist()
    whitelist = [w for w in whitelist if w['ip'] != ip]
    save_json(IP_WHITELIST_FILE, whitelist)

    return {"success": True}


@app.get("/api/audit/login-logs")
async def get_login_logs():
    logs = load_json(LOGIN_LOGS_FILE)
    return {"success": True, "data": logs}


@app.get("/api/audit/audit-logs")
async def get_audit_logs():
    logs = load_json(AUDIT_LOGS_FILE)
    return {"success": True, "data": logs}


@app.get("/knowledge-base", response_class=HTMLResponse)
async def knowledge_base_page(request: Request):
    """知识库管理页面"""
    return templates.TemplateResponse("knowledge-base.html", {"request": request})


# ==================== WAF引擎API ====================

@app.post("/api/check-request")
async def check_request(request_data: dict):
    """
    检测HTTP请求
    
    请求体格式:
    {
        "url": "http://example.com?id=1",
        "method": "GET",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "body": "",
        "cookies": "",
        "query_string": "id=1"
    }
    """
    try:
        alerts = waf_engine.check_request(request_data)
        return {
            "success": True,
            "alerts": alerts,
            "risk_level": "high" if len(alerts) > 0 else "safe",
            "alert_count": len(alerts)
        }
    except Exception as e:
        return {"success": False, "message": f"检测失败: {str(e)}"}


@app.get("/api/waf-stats")
async def get_waf_stats():
    """获取WAF规则统计"""
    try:
        stats = waf_engine.get_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        return {"success": False, "message": f"获取统计失败: {str(e)}"}


@app.post("/api/test-waf")
async def test_waf():
    """测试WAF引擎检测能力"""
    try:
        test_results = waf_engine.test_detection()
        return {"success": True, "data": test_results}
    except Exception as e:
        return {"success": False, "message": f"测试失败: {str(e)}"}




# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    return {
        "success": False,
        "message": f"服务器错误: {str(exc)}",
        "detail": traceback.format_exc() if __debug__ else None
    }



# 健康检查端点
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now().isoformat(),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)

# ===== 登录失败锁定机制 =====
import time

LOGIN_ATTEMPTS = {}
LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION = 1800

def check_lockout(username: str) -> dict:
    if username in LOGIN_ATTEMPTS:
        attempts, lockout_time = LOGIN_ATTEMPTS[username]
        if attempts >= LOCKOUT_THRESHOLD:
            elapsed = time.time() - lockout_time
            if elapsed < LOCKOUT_DURATION:
                remaining = int(LOCKOUT_DURATION - elapsed)
                return {"locked": True, "remaining_minutes": remaining // 60}
            else:
                del LOGIN_ATTEMPTS[username]
    return {"locked": False}

def record_login_failure(username: str):
    if username not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[username] = [0, 0]
    LOGIN_ATTEMPTS[username][0] += 1
    if LOGIN_ATTEMPTS[username][0] >= LOCKOUT_THRESHOLD:
        LOGIN_ATTEMPTS[username][1] = time.time()
