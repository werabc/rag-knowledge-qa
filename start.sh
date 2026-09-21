#!/bin/bash

echo "========================================"
echo "  企业知识库问答系统 - 启动脚本"
echo "========================================"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3环境，请先安装Python 3.8+"
    exit 1
fi

echo "✅ Python环境检查通过"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

echo "🚀 激活虚拟环境..."
source venv/bin/activate

echo "📦 安装依赖包..."
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "⚙️  配置环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ 环境变量配置文件已创建"
fi

echo ""
echo "========================================"
echo "  启动企业知识库问答系统"
echo "========================================"
echo ""

# 启动系统
python run.py