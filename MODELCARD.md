# Hospital WAF MCP Server

## 📋 基本信息

| 字段 | 内容 |
|------|------|
| **名称** | hospital-waf-mcp |
| **版本** | v1.0.0 |
| **作者** | Liu Tao |
| **协议** | MIT License |
| **传输方式** | Streamable HTTP / SSE / stdio |
| **Python版本** | ≥ 3.10 |

## 📖 简介

面向医院场景的 **Web 应用防火墙（WAF）检测引擎 MCP 服务**，支持：

- **SQL 注入检测**（SQLi）
- **跨站脚本检测**（XSS）
- **命令注入检测**（Command Injection）
- **路径遍历检测**（Path Traversal）
- **医院专项规则**（医疗系统常见漏洞模式）

可接入 Cursor、Claude Desktop、魔搭 MCP 广场等支持 MCP 协议的 AI 助手。

## 🔧 工具列表

| 工具名 | 功能说明 |
|--------|----------|
| `waf_check_request` | 对 HTTP 请求进行 WAF 规则检测，返回命中告警列表 |
| `waf_rule_stats` | 获取已加载规则的统计信息 |
| `waf_reload_rules` | 热重载规则文件（无需重启服务） |
| `waf_run_self_tests` | 运行内置攻击样例自检 |

## 🚀 快速部署

### 方式一：本地运行（stdio）

```bash
git clone https://github.com/12211725-star/hospital-waf-mcp.git
cd hospital-waf-mcp
pip install -r requirements-mcp.txt
python -m waf_mcp
```

### 方式二：HTTP 服务（魔搭托管推荐）

```bash
export WAF_MCP_TRANSPORT=http
export WAF_MCP_HOST=0.0.0.0
export WAF_MCP_PORT=8000
python -m waf_mcp
```

MCP 端点：`http://<host>:8000/mcp`

### 方式三：Docker 部署

```bash
docker build -f Dockerfile.mcp -t hospital-waf-mcp .
docker run -p 8000:8000 hospital-waf-mcp
```

## 📝 使用示例

### 检测请求

```json
{
  "url": "https://example.com/search?q=1' OR '1'='1",
  "method": "GET",
  "headers": {"User-Agent": "Mozilla/5.0"},
  "body": "",
  "cookies": ""
}
```

### 返回结果

```json
[
  {
    "rule_id": "sqli-001",
    "category": "SQL Injection",
    "severity": "high",
    "matched": "1' OR '1'='1",
    "description": "检测到 SQL 注入特征"
  }
]
```

## 🔗 相关链接

- **GitHub 仓库**: https://github.com/12211725-star/hospital-waf-mcp
- **问题反馈**: https://github.com/12211725-star/hospital-waf-mcp/issues

## 📜 许可证

MIT License
