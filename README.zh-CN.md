# 医院 WAF 管理系统

**发行版本：** v1.0.0

**语言:** [English](README.md) | [简体中文](README.zh-CN.md)

面向医院场景的 **Web 应用防火墙管理台** 与 **HTTP 请求检测引擎**，可选通过 **MCP（Model Context Protocol）** 向大模型/IDE 暴露检测能力。检测基于 Python `re` 对 JSON 规则集（默认 `rules/waf_rules.mcp.json`）进行匹配。

---

## 目录

1. [功能概览](#1-功能概览)
2. [系统架构](#2-系统架构)
3. [运行环境](#3-运行环境)
4. [快速开始](#4-快速开始)
5. [配置说明](#5-配置说明)
6. [Web 页面](#6-web-页面)
7. [HTTP API 摘要](#7-http-api-摘要)
8. [WAF 规则流水线](#8-waf-规则流水线)
9. [MCP 服务](#9-mcp-服务)
10. [测试](#10-测试)
11. [安全与局限](#11-安全与局限)
12. [目录结构](#12-目录结构)

---

## 1. 功能概览

### 1.1 Web 管理台

| 模块 | 说明 |
|------|------|
| **仪表盘** | 攻击统计、规则数量、黑名单规模、登录次数等（数据来自 JSON）。 |
| **攻击日志** | 列表与筛选；无数据时可能生成 **演示用模拟日志**。 |
| **规则管理（界面）** | 对 `data/waf_rules.json` 中的规则做 **启用/禁用**（元数据）。该文件 **不会自动同步** 到引擎用的正则规则文件；引擎规则见 [第 8 节](#8-waf-规则流水线)。 |
| **黑白名单** | 对 JSON 的增删查；**默认未接入** `POST /api/check-request` 拦截逻辑，需自行扩展。 |
| **用户管理** | 创建/删除用户；界面展示角色：管理员 / 安全员 / 审计员。 |
| **审计** | 登录日志与操作日志（JSON）。 |
| **知识库** | `/api/knowledge-base/*` 模块激活、合并等（见 `knowledge_base_routes.py`）。 |
| **修改密码** | 复杂度校验、首次登录修改、90 天过期标记。 |

### 1.2 WAF 检测引擎

- **输入**：URL、method、headers、body、cookies（见 `WAFEngine.check_request`）。
- **规则文件**：`rules/waf_rules.mcp.json`，可通过 **`WAF_RULES_FILE`** 覆盖。
- **接口**：`POST /api/check-request`、`GET /api/waf-stats`、`POST /api/test-waf`（内置四类样例自检）。

### 1.3 等保相关能力（演示级）

- 登录失败锁定（写入 `data/users.json`）。
- 密码复杂度与轮换字段。
- 登录页验证码：**请确认是否与后端校验闭环**后再用于生产（见 [第 11 节](#11-安全与局限)）。

---

## 2. 系统架构

```text
┌─────────────────┐     ┌──────────────┐     ┌─────────────────────────┐
│  浏览器 (UI)    │────▶│  FastAPI     │────▶│  JSON 数据 (data/)      │
└─────────────────┘     │  app.py      │     └─────────────────────────┘
                          │              │
                          │  WAFEngine   │◀──── rules/waf_rules.mcp.json
                          └──────┬───────┘      （或 WAF_RULES_FILE）
                                 │
                          ┌──────▼───────┐
                          │  MCP 服务    │  stdio | http | sse（三选一）
                          │  waf_mcp/    │
                          └──────────────┘
```

---

## 3. 运行环境

| 项目 | 说明 |
|------|------|
| Python | **建议 3.10+**（MCP / FastMCP 要求；Web 亦建议同版本） |
| Web | FastAPI、Uvicorn、Jinja2、Pillow |
| MCP | `fastmcp`（见 `requirements-mcp.txt`） |
| Docker | 可选：`Dockerfile`（Web）、`Dockerfile.mcp`（MCP HTTP） |

建议服务器：2 核 CPU、4 GB 内存、20 GB 磁盘（日志与规则）。

---

## 4. 快速开始

### 4.1 直接运行 Web

```bash
pip install -r requirements.txt
python app.py
```

访问：`http://服务器IP:8083`  
默认账号：`admin` / `Admin@123` — **首次登录请修改密码**。

### 4.2 Docker 部署（Web）

```bash
chmod +x deploy.sh
./deploy.sh
```

或使用仓库内 `docker-compose.yml`、`Dockerfile`。

---

## 5. 配置说明

| 环境变量 | 作用范围 | 说明 |
|----------|----------|------|
| `WAF_RULES_FILE` | Web、`WAFEngine`、MCP | 引擎使用的 **正则规则 JSON** 路径；默认 `rules/waf_rules.mcp.json`。 |
| `WAF_MCP_TRANSPORT` | MCP | `stdio`（默认）、`http`（Streamable HTTP）、`sse`。**每个进程仅一种传输。** |
| `WAF_MCP_HOST` | MCP | 网络监听地址，默认 `127.0.0.1`。 |
| `WAF_MCP_PORT` | MCP | 端口，默认 `8000`。 |

---

## 6. Web 页面

| 路径 | 说明 |
|------|------|
| `/` | 登录 |
| `/dashboard` | 仪表盘 |
| `/attacks` | 攻击日志 |
| `/rules` | 规则开关（元数据） |
| `/blacklist` | 黑名单等 |
| `/users` | 用户管理 |
| `/audit` | 审计 |
| `/change-password` | 修改密码 |
| `/knowledge-base` | 知识库管理页 |

---

## 7. HTTP API 摘要

**说明：** 示例代码中多数 API **未统一做会话/JWT 鉴权**，部署前请在可信网络内使用或自行增加认证中间件。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/captcha` | 验证码图片（响应头 `X-Captcha-Id`） |
| POST | `/api/login` | 登录 |
| POST | `/api/change-password` | 修改密码 |
| GET / POST / DELETE | `/api/users` 等 | 用户管理 |
| GET | `/api/stats` | 仪表盘统计 |
| GET | `/api/attacks` | 攻击日志 |
| GET / POST | `/api/rules`、`/api/rules/toggle` | 界面规则元数据 |
| GET / POST / DELETE | `/api/blacklist`、`/api/whitelist` | 黑白名单 |
| GET | `/api/audit/login-logs`、`/api/audit/audit-logs` | 审计 |
| POST | `/api/check-request` | 对请求体执行 WAF 检测 |
| GET | `/api/waf-stats` | 引擎统计（含 `compile_failed` 等） |
| POST | `/api/test-waf` | 引擎自检 |
| * | `/api/knowledge-base/*` | 知识库 API |

**`POST /api/check-request` 请求体示例：**

```json
{
  "url": "https://example.com/search?q=test",
  "method": "GET",
  "headers": { "User-Agent": "Mozilla/5.0" },
  "body": "",
  "cookies": ""
}
```

---

## 8. WAF 规则流水线

1. **源库**：`knowledge-base/waf_rules.json`（体积大、含 ModSecurity 语义等）。
2. **生成 MCP 兼容集**：  
   `python3 scripts/build_mcp_rules.py`  
   输出/更新 `rules/waf_rules.mcp.json`（Python `re` 可编译；剔除不支持的运算符与 `%{...}` 宏）。
3. **校验**：  
   `python3 scripts/validate_rules.py`
4. **可选医院增补**：编辑 `rules/hospital_supplement.json`，构建时合并。

---

## 9. MCP 服务

```bash
pip install -r requirements-mcp.txt
python3 -m waf_mcp
```

| 工具 | 说明 |
|------|------|
| `waf_check_request` | 请求检测，返回告警列表 |
| `waf_rule_stats` | 规则与编译统计 |
| `waf_reload_rules` | 热加载规则文件 |
| `waf_run_self_tests` | 内置自检样例 |

- **`WAF_MCP_TRANSPORT=http`** 时，MCP 端点一般为 `http(s)://主机:端口/mcp`；探活：`GET /health`。
- 客户端配置示例见 `mcp-examples/`。
- **更完整的 MCP 约定（魔搭单一传输等）：** [README-MCP.md](README-MCP.md)

容器（仅 HTTP）：`Dockerfile.mcp`。

---

## 10. 测试

```bash
python3 scripts/run_functional_tests.py
```

覆盖：规则校验、引擎自检、恶意样例、`/health` 与主要 API；若已安装 `fastmcp` 则验证 MCP 模块导入。

---

## 11. 安全与局限

- **非反向代理型 WAF**：不自动截断生产流量；检测需调用 API/MCP。
- **界面规则**（`data/waf_rules.json`）与 **引擎规则**（`rules/waf_rules.mcp.json`）分离，变更后注意同步策略。
- **黑白名单** 默认不参与 `check_request`。
- **密码存储** 示例为 SHA-256，生产请加强（加盐、慢哈希等）。
- **验证码** 请确认前后端校验策略满足等保/院内规范。
- **角色权限** 未在所有 API 上强制，生产需补全鉴权。

---

## 12. 目录结构

```text
app.py                 # FastAPI 主程序
waf_engine.py          # 正则 WAF 引擎
waf_mcp/               # MCP 包（config、server、入口）
rules/                 # waf_rules.mcp.json、hospital_supplement.json
data/                  # 用户、日志、界面规则元数据、黑白名单等
knowledge-base/        # 知识库源数据
web/templates/         # Jinja2 页面
scripts/               # 构建/校验/功能测试脚本
mcp-examples/          # MCP 客户端配置示例
Dockerfile / Dockerfile.mcp
```

---

## 版本

**v1.0.0** — 以仓库根目录 [`version.py`](version.py) 中的 `__version__` 为准。
