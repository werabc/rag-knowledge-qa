

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python环境，请先安装Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python环境检查通过

REM 检查虚拟环境
if not exist "venv" (
    echo 📦 创建虚拟环境...
    python -m venv venv
)

echo 🚀 激活虚拟环境...
call venv\Scripts\activate

echo 📦 安装依赖包...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ⚙️  配置环境变量...
if not exist ".env" (
    copy .env.example .env
    echo ✅ 环境变量配置文件已创建
)

echo.
echo ========================================
echo  启动企业知识库问答系统
echo ========================================
echo.

REM 启动系统
python run.py

pause