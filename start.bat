@echo off
chcp 65001 >nul
echo 🚀 启动 Teambition API Tool...

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未安装 Python
    pause
    exit /b 1
)

:: 检查依赖
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo 📦 安装依赖...
    pip install -r requirements.txt
)

:: 启动应用
echo 🌐 应用将在 http://localhost:8501 启动
echo 按 Ctrl+C 停止应用
streamlit run app.py

pause
