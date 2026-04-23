# Hospital WAF Management System

**Release:** v1.0.0

**Languages:** [English](README.md) | [简体中文](README.zh-CN.md)

A hospital-oriented **Web application firewall (WAF) management console** and **request-inspection engine**, with optional **MCP (Model Context Protocol)** exposure for AI assistants. The detection engine uses Python `re` against a curated JSON rule set (`rules/waf_rules.mcp.json`).

---

## Table of Contents

1. [Features](#1-features)
2. [Architecture](#2-architecture)
3. [Requirements](#3-requirements)
4. [Quick Start](#4-quick-start)
5. [Configuration](#5-configuration)
6. [Web UI & Routes](#6-web-ui--routes)
7. [HTTP API (Summary)](#7-http-api-summary)
8. [WAF Rules Pipeline](#8-waf-rules-pipeline)
9. [MCP Server](#9-mcp-server)
10. [Testing](#10-testing)
11. [Security & Limitations](#11-security--limitations)
12. [Project Layout](#12-project-layout)

---

## 1. Features

### 1.1 Web console

| Area | Description |
|------|-------------|
| **Dashboard** | Attack statistics, rule counts, blacklist size, login counts (aggregated from JSON stores). |
| **Attack logs** | List and filter logs; initial empty store may be backfilled with **simulated** sample logs for demo. |
| **Rules (UI)** | Enable/disable **metadata** rules in `data/waf_rules.json` (names, categories, toggles). This list is **not** automatically synced to the regex engine file; use the rules pipeline for engine rules. |
| **IP blacklist / whitelist** | CRUD on JSON files; **not** wired into `POST /api/check-request` (policy data only unless you extend the app). |
| **Users** | Create/delete users; roles stored (`admin` / `security` / `auditor` in UI). |
| **Audit** | Login logs and operation logs (JSON). |
| **Knowledge base** | Module merge/activate APIs under `/api/knowledge-base/*` (see `knowledge_base_routes.py`). |
| **Change password** | Complexity rules, first-login / 90-day rotation flags. |

### 1.2 WAF engine

- **Input**: URL, method, headers, body, cookies (as accepted by `WAFEngine.check_request`).
- **Rules**: `rules/waf_rules.mcp.json` (regex, MCP-compatible subset). Override with `WAF_RULES_FILE`.
- **APIs**: `POST /api/check-request`, `GET /api/waf-stats`, `POST /api/test-waf` (built-in self-test payloads).

### 1.3 Compliance-oriented login (demo level)

- Account lockout after failed attempts (persisted in `data/users.json`).
- Password complexity and rotation metadata.
- Captcha UI exists; **verify server-side integration** before production (see [Security](#11-security--limitations)).

---

## 2. Architecture

```text
┌─────────────────┐     ┌──────────────┐     ┌─────────────────────────┐
│  Browser (UI)   │────▶│  FastAPI     │────▶│  JSON files (data/)     │
└─────────────────┘     │  app.py      │     └─────────────────────────┘
                          │              │
                          │  WAFEngine   │◀──── rules/waf_rules.mcp.json
                          └──────┬───────┘      (or WAF_RULES_FILE)
                                 │
                          ┌──────▼───────┐
                          │  MCP server  │  stdio | http | sse
                          │  waf_mcp/    │
                          └──────────────┘
```

---

## 3. Requirements

| Component | Version / notes |
|-----------|------------------|
| Python | **3.10+** (required for MCP / FastMCP; web app may run on 3.9 in some setups—prefer 3.10+) |
| Web stack | FastAPI, Uvicorn, Jinja2, Pillow |
| MCP | `fastmcp` (see `requirements-mcp.txt`) |
| Docker | Optional (`Dockerfile`, `Dockerfile.mcp`) |

Suggested server: 2 vCPU, 4 GB RAM, 20 GB disk (for logs and rule JSON).

---

## 4. Quick Start

### 4.1 Web application

```bash
pip install -r requirements.txt
python app.py
```

Default URL: `http://<host>:8083`

Default admin: `admin` / `Admin@123` — **change password on first login**.

### 4.2 Docker (web)

```bash
chmod +x deploy.sh
./deploy.sh
```

Or use `docker-compose.yml` / `Dockerfile` as shipped.

---

## 5. Configuration

| Variable | Applies to | Description |
|----------|------------|-------------|
| `WAF_RULES_FILE` | `app.py`, MCP | Path to the **regex** rule JSON used by `WAFEngine`. Default: `rules/waf_rules.mcp.json`. |
| `WAF_MCP_TRANSPORT` | MCP | `stdio` (default), `http` (Streamable HTTP), or `sse`. **One process = one transport.** |
| `WAF_MCP_HOST` | MCP | Bind address for network transports (default `127.0.0.1`). |
| `WAF_MCP_PORT` | MCP | Listen port (default `8000`). |

---

## 6. Web UI & Routes

| Path | Purpose |
|------|---------|
| `/` | Login |
| `/dashboard` | Dashboard |
| `/attacks` | Attack log viewer |
| `/rules` | Rule toggles (metadata file) |
| `/blacklist`, implied whitelist UI if present | IP lists |
| `/users` | User admin |
| `/audit` | Audit viewer |
| `/change-password` | Password change |
| `/knowledge-base` | Knowledge-base management page |

---

## 7. HTTP API (Summary)

**Authentication:** APIs are **not** uniformly protected by session/JWT in the stock code; treat deployments as **internal/trusted network** or add middleware before production.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health JSON |
| GET | `/api/captcha` | CAPTCHA image (+ `X-Captcha-Id` header) |
| POST | `/api/login` | Login |
| POST | `/api/change-password` | Change password |
| GET/POST/DELETE | `/api/users`, `/api/users/create`, `/api/users/{username}` | Users |
| GET | `/api/stats` | Dashboard stats |
| GET | `/api/attacks` | Attack logs |
| GET/POST | `/api/rules`, `/api/rules/toggle` | UI rule metadata |
| GET/POST/DELETE | `/api/blacklist`, `/api/whitelist` | Lists |
| GET | `/api/audit/login-logs`, `/api/audit/audit-logs` | Audit |
| POST | `/api/check-request` | Run WAF engine on a JSON body |
| GET | `/api/waf-stats` | Engine stats (`compile_failed`, etc.) |
| POST | `/api/test-waf` | Engine self-tests |
| * | `/api/knowledge-base/*` | Knowledge-base module APIs |

Example **`POST /api/check-request`** body:

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

## 8. WAF Rules Pipeline

1. **Source**: `knowledge-base/waf_rules.json` (large / mixed semantics).
2. **Build MCP-compatible subset**:  
   `python3 scripts/build_mcp_rules.py`  
   Produces/updates `rules/waf_rules.mcp.json` (Python-`re`-compatible patterns; strips unsupported ModSecurity operators; skips `%{...}` macros).
3. **Validate**:  
   `python3 scripts/validate_rules.py`
4. **Optional hospital add-ons**: edit `rules/hospital_supplement.json` (merged at build time).

---

## 9. MCP Server

Expose the same engine to MCP clients (Cursor, ModelScope-style HTTP endpoints, etc.).

```bash
pip install -r requirements-mcp.txt
python3 -m waf_mcp
```

| Tool | Description |
|------|-------------|
| `waf_check_request` | Inspect a request; returns alert list. |
| `waf_rule_stats` | Rule and compile statistics. |
| `waf_reload_rules` | Reload rules from disk. |
| `waf_run_self_tests` | Built-in detection smoke tests. |

- **Streamable HTTP** endpoint (when `WAF_MCP_TRANSPORT=http`): typically `http://<host>:<port>/mcp`.
- **Health** (network modes): `GET /health`.

Sample client snippets: `mcp-examples/`.  
**Extended MCP notes (Chinese):** [README-MCP.md](README-MCP.md).

Docker image (HTTP only): `Dockerfile.mcp`.

---

## 10. Testing

```bash
python3 scripts/run_functional_tests.py
```

Covers: rule validation, engine self-tests, sample malicious URL, main FastAPI endpoints, optional `fastmcp` import.

---

## 11. Security & Limitations

- **Not a reverse-proxy WAF**: request inspection is **API/tool invoked**; it does not terminate production HTTP traffic by itself.
- **UI rule toggles** (`data/waf_rules.json`) and **engine rules** (`rules/waf_rules.mcp.json`) are separate; rebuild/sync as needed.
- **Blacklist/whitelist** in JSON are not automatically enforced in `check_request` in stock code.
- **Password storage** uses SHA-256 without per-user salt in the sample—harden for real deployments.
- **CAPTCHA**: confirm end-to-end validation matches your security model.
- **Role-based API authorization** is not fully enforced on all routes in the sample—add auth middleware for production.

---

## 12. Project Layout

```text
app.py                 # FastAPI web app
waf_engine.py          # Regex WAF engine
waf_mcp/               # MCP package (config, server, __main__)
rules/                 # waf_rules.mcp.json, hospital_supplement.json
data/                  # users, logs, UI rule metadata, lists
knowledge-base/        # Knowledge-base sources
web/templates/         # Jinja2 HTML
scripts/               # build_mcp_rules, validate_rules, run_functional_tests
mcp-examples/          # Client configuration examples
Dockerfile / Dockerfile.mcp
```

---

## Version

**v1.0.0** — canonical value in [`version.py`](version.py) (`__version__`).
