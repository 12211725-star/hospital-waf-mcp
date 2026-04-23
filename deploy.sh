#!/bin/bash

echo "========================================"
echo "   医院WAF管理系统 v1.0.0 部署脚本"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未安装 Python3"
    exit 1
fi

echo "✅ Python3: $(python3 --version)"

# 安装依赖
echo ""
echo "📦 安装依赖..."
pip3 install -r requirements.txt

# 启动服务
echo ""
echo "🚀 启动服务..."
echo "端口: 8083"
echo "访问: http://服务器IP:8083"
echo ""
echo "默认账号: admin"
echo "默认密码: Admin@123"
echo "⚠️  首次登录必须修改密码"
echo ""

python3 app.py
