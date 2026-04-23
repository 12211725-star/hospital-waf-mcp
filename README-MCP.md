# 医院 WAF — MCP 说明（魔搭规范 / 单一传输）

**文档语言:** 本文档为中文。完整功能说明（中英文）见项目根目录 [README.md](README.md) / [README.zh-CN.md](README.zh-CN.md)。

**发行版本：** v1.0.0（与根目录 `version.py` 一致）。

## 设计约定

- **每个运行进程只启用一种传输**：由环境变量 `WAF_MCP_TRANSPORT` 唯一指定，禁止混用或并列多种。
- **取值**（与 [FastMCP 文档](https://gofastmcp.com/deployment/running-server) 一致）：
  - `stdio`：标准输入输出，适合本机 Cursor / Claude Desktop 子进程拉起。
  - `http`：**Streamable HTTP**（魔搭 / 云托管推荐），MCP 端点默认为 `http://<host>:<port>/mcp`。
  - `sse`：旧版 SSE 传输，仅当客户端仍要求 SSE 时使用；新集成请用 `http`。
- 别名：`streamable-http` → `http`。

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `WAF_MCP_TRANSPORT` | `stdio` / `http` / `sse` | `stdio` |
| `WAF_MCP_HOST` | 网络监听地址（`http`/`sse`） | `127.0.0.1` |
| `WAF_MCP_PORT` | 监听端口 | `8000` |
| `WAF_RULES_FILE` | 规则 JSON 路径 | `rules/waf_rules.mcp.json` |

探活（与 MCP 同进程，**仅在网络传输时可用**）：`GET /health`。

## 依赖与启动

需要 **Python 3.10+**。

```bash
pip install -r requirements-mcp.txt
```

**本机 stdio（默认）**

```bash
python3 -m waf_mcp
# 等价于 WAF_MCP_TRANSPORT=stdio
```

**魔搭 / 远程 Streamable HTTP**

```bash
export WAF_MCP_TRANSPORT=http
export WAF_MCP_HOST=0.0.0.0
export WAF_MCP_PORT=8000
python3 -m waf_mcp
```

客户端填写 MCP URL：`http(s)://你的域名:端口/mcp`。

**兼容 SSE（不推荐新项目）**

```bash
export WAF_MCP_TRANSPORT=sse
python3 -m waf_mcp
```

具体路径请以客户端/SDK 要求为准（示例见 `mcp-examples/modelscope-sse-legacy.json`）。

## 配置示例文件

| 文件 | 用途 |
|------|------|
| `mcp-examples/cursor-stdio.json` | Cursor 本地 stdio |
| `mcp-examples/modelscope-streamable-http.json` | 魔搭等远程 HTTP |
| `mcp-examples/modelscope-sse-legacy.json` | 旧版 SSE |

## Docker（仅 HTTP）

```bash
docker build -f Dockerfile.mcp -t hospital-waf-mcp .
docker run -p 8000:8000 hospital-waf-mcp
```

## 规则维护

- 默认规则：`rules/waf_rules.mcp.json`
- 重新生成：`python3 scripts/build_mcp_rules.py && python3 scripts/validate_rules.py`
- 可选增补：`rules/hospital_supplement.json`

## Tools

| 工具 | 说明 |
|------|------|
| `waf_check_request` | URL/headers/body/cookie 规则匹配 |
| `waf_rule_stats` | 统计与编译失败信息 |
| `waf_reload_rules` | 热加载规则文件 |
| `waf_run_self_tests` | 内置四类攻击样例自检 |

## 与 Web 管理台

`app.py` 中 WAF 引擎与 MCP 共用 `rules/waf_rules.mcp.json`（或 `WAF_RULES_FILE`），检测逻辑一致；管理界面与 MCP **传输无关**。
