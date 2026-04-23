# Hospital WAF Management System MCP Server

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-orange.svg)](https://github.com/anthropics/mcp)

English | [中文](README.zh-CN.md)

医院 Web 应用防火墙 MCP 服务器，为 AI 助手提供 WAF 规则检测能力。支持 SQL 注入、XSS、命令注入、路径遍历检测，内置医院场景专项规则。

## ✨ 功能特性

- 🔒 **SQL 注入检测** — 识别常见 SQLi 攻击模式（UNION注入、布尔盲注、时间盲注、报错注入）
- 🎯 **XSS 跨站脚本检测** — 检测反射型/存储型 XSS（script标签、事件处理器、JS URI）
- ⚡ **命令注入检测** — 识别 Unix/Windows 系统命令执行攻击
- 📁 **路径遍历检测** — 检测目录穿越攻击及编码绕过
- 🏥 **医院专项规则** — 覆盖 HIS/PACS/LIS/RIS 常见漏洞模式
- 🔄 **热重载规则** — 修改规则后无需重启服务
- 🧪 **自检测试** — 内置攻击样例验证引擎能力
- ⚡ **轻量运行** — 纯 Python 正则引擎，无外部依赖

## 🚀 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/12211725-star/hospital-waf-mcp.git
cd hospital-waf-mcp

# 安装依赖
pip install -r requirements-mcp.txt
```

### 2. 集成到 MCP 客户端

在 MCP 客户端配置文件中添加：

```json
{
  "mcpServers": {
    "hospital-waf-mcp": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Docker 方式

```json
{
  "mcpServers": {
    "hospital-waf-mcp": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### stdio 本地模式

```json
{
  "mcpServers": {
    "hospital-waf-mcp": {
      "command": "python",
      "args": ["-m", "waf_mcp"],
      "env": {
        "WAF_MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### Streamable HTTP 远程部署

```bash
export WAF_MCP_TRANSPORT=http
export WAF_MCP_HOST=0.0.0.0
export WAF_MCP_PORT=8000
python -m waf_mcp
```

MCP 端点：`http://<host>:8000/mcp`  
健康检查：`GET /health`

## 📖 使用方法

### 检测 SQL 注入

在 Claude / Cursor / 其他 MCP 客户端中：

```
请帮我检测这个请求是否有安全问题：
URL: https://example.com/search?q=1' OR '1'='1
```

AI 会调用 `waf_check_request` 工具，返回：

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

### 检测 XSS 攻击

```
检测这个 POST 请求的 body：
<script>alert('xss')</script>
```

### 查看规则统计

```
当前 WAF 引擎加载了多少规则？
```

## 🎯 提示词指南

### 安全评估场景

```
我需要对一个请求进行安全检测，
URL 是 https://hospital.example.com/api/patient?id=1 UNION SELECT，
请帮我分析是否存在攻击特征。
```

### 规则运维场景

```
我刚刚更新了 WAF 规则文件，
请帮我重新加载规则并确认加载成功。
```

### 引擎验证场景

```
请运行 WAF 引擎自检测试，
确认 SQL 注入和 XSS 检测功能正常。
```

### 日志分析场景

```
帮我检测这个可疑请求的完整参数：
URL: https://api.hospital.com/query
Method: POST
Body: {"filter": "'; DROP TABLE users; --"}
Headers: {"Content-Type": "application/json"}
```

## 🛠️ 工具列表

| 工具 | 描述 | 参数 |
|------|------|------|
| `waf_check_request` | WAF 请求检测 | `url`: 请求URL, `method`: HTTP方法, `headers`: 请求头, `body`: 请求体, `cookies`: Cookie |
| `waf_rule_stats` | 规则统计 | 无参数 |
| `waf_reload_rules` | 热重载规则 | 无参数 |
| `waf_run_self_tests` | 自检测试 | 无参数 |

## 📖 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `WAF_MCP_TRANSPORT` | 传输协议 (stdio/http/sse) | `stdio` |
| `WAF_MCP_HOST` | HTTP 监听地址 | `127.0.0.1` |
| `WAF_MCP_PORT` | HTTP 监听端口 | `8000` |
| `WAF_RULES_FILE` | 规则文件路径 | `rules/waf_rules.mcp.json` |

## 📋 检测能力

### SQL 注入检测

| 风险类型 | 严重程度 | 检测条件 |
|---------|---------|---------|
| UNION 注入 | High | UNION SELECT 等 |
| 布尔盲注 | High | AND/OR 布尔表达式 |
| 时间盲注 | High | SLEEP/BENCHMARK 等 |
| 报错注入 | High | EXTRACTVALUE/UPDATEXML 等 |
| 堆叠查询 | High | 分号分隔多条 SQL |

### XSS 检测

| 风险类型 | 严重程度 | 检测条件 |
|---------|---------|---------|
| script 标签 | High | `<script>` 标签注入 |
| 事件处理器 | High | onclick/onerror 等 |
| JavaScript URI | Medium | `javascript:` 协议 |
| SVG 注入 | Medium | `<svg onload>` 等 |

### 命令注入检测

| 风险类型 | 严重程度 | 检测条件 |
|---------|---------|---------|
| Unix 命令注入 | Critical | ; \| & $ ` 管道连接 |
| Windows 命令注入 | Critical | & \| ^ 命令连接 |
| 危险命令 | Critical | cat/ls/wget/curl 等 |

### 路径遍历检测

| 风险类型 | 严重程度 | 检测条件 |
|---------|---------|---------|
| 目录穿越 | High | `../` 路径穿越 |
| URL 编码绕过 | High | `%2e%2e/` 等编码 |
| 双重编码绕过 | High | `%252e%252e/` 等 |

### 医院场景专项

| 系统类型 | 关键词 |
|---------|--------|
| HIS | 医院信息系统、门诊、住院、挂号 |
| PACS | 影像、DICOM、放射 |
| LIS | 检验、实验室、生化 |
| RIS | 放射信息系统、影像诊断 |
| EMR | 电子病历、病程记录 |

## 🔧 开发

```bash
git clone https://github.com/12211725-star/hospital-waf-mcp.git
cd hospital-waf-mcp
pip install -e .

# 运行测试
python scripts/run_functional_tests.py

# 本地运行（HTTP模式）
export WAF_MCP_TRANSPORT=http
python -m waf_mcp
```

## 📁 项目结构

```
hospital-waf-mcp/
├── waf_mcp/                  # MCP 服务代码
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   └── server.py
├── waf_engine.py             # WAF 检测引擎
├── rules/                    # 规则文件
│   ├── waf_rules.mcp.json
│   └── hospital_supplement.json
├── scripts/                  # 脚本工具
├── modelscope.yaml           # 魔搭配置
├── mcp.json                  # MCP 元数据
├── mcp_config.json           # MCP 客户端配置
├── pyproject.toml            # Python 项目配置
└── README.md
```

## 📄 许可证

MIT License

## 🔗 链接

- **GitHub**: https://github.com/12211725-star/hospital-waf-mcp
- **Issues**: https://github.com/12211725-star/hospital-waf-mcp/issues
- **魔搭 MCP 广场**: https://modelscope.cn/mcp/servers
