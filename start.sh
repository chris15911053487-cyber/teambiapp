#!/bin/bash
# Teambition API Tool 启动脚本

echo "🚀 启动 Teambition API Tool..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未安装 Python3"
    exit 1
fi

# 检查依赖
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "📦 安装依赖..."
    pip3 install -r requirements.txt
fi

# 启动应用
echo "🌐 应用将在 http://localhost:8501 启动"
streamlit run app.py
