@echo off
chcp 65001 >nul
title BLACK System Launcher
color 0A

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║                                                           ║
echo ║   🚀 BLACK System Launcher v5.0.0                        ║
echo ║   统一智能体调度核心                                       ║
echo ║                                                           ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM 检查Python环境
echo 📋 检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装，请先安装Python 3.10+
    pause
    exit /b 1
)
echo ✅ Python环境检查通过

REM 安装依赖
echo 📦 安装依赖...
pip install fastapi uvicorn httpx >nul 2>&1
if errorlevel 1 (
    echo ⚠️ 依赖安装失败，尝试使用现有环境...
)

echo.
echo 🟢 启动服务...
echo.

REM 1. 启动BLACK Core（端口9001）
echo [1/3] 启动 BLACK Core...
start "BLACK Core (端口9001)" cmd /k "python black_system/core/main.py"

REM 等待服务启动
timeout /t 3 /nobreak >nul

REM 2. 启动UFO³ Galaxy Gateway（端口9000）
echo [2/3] 启动 UFO³ Galaxy Gateway...
if exist "galaxy_gateway\main.py" (
    start "UFO³ Galaxy Gateway (端口9000)" cmd /k "python galaxy_gateway/main.py"
) else (
    echo ⚠️ UFO³ Galaxy Gateway 未找到
)

timeout /t 3 /nobreak >nul

REM 3. 启动Dashboard（端口3000）
echo [3/3] 启动 Dashboard...
if exist "dashboard\backend\main.py" (
    start "Dashboard (端口3000)" cmd /k "python dashboard/backend/main.py"
) else (
    echo ⚠️ Dashboard 未找到
)

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║                                                           ║
echo ║   ✅ 所有服务已启动！                                      ║
echo ║                                                           ║
echo ║   📋 服务地址：                                            ║
echo ║   - BLACK Core:    http://localhost:9001                 ║
echo ║   - UFO³ Galaxy:   http://localhost:9000                 ║
echo ║   - Dashboard:     http://localhost:3000                 ║
echo ║                                                           ║
echo ║   💡 快捷操作：                                            ║
echo ║   - F12: 打开 UFO³ Galaxy 控制面板                        ║
echo ║   - 浏览器访问 http://localhost:9001                      ║
echo ║   - 查看日志：black_system\logs                           ║
echo ║                                                           ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM 打开Dashboard
echo 🌐 正在打开 Dashboard...
start http://localhost:9001

echo 💡 按任意键查看帮助，或直接开始使用...
pause >nul

echo.
echo 📖 帮助信息：
echo   • 输入自然语言命令控制整个系统
echo   • 支持语音唤醒（"嘿BLACK"）
echo   • 支持跨设备协同
echo   • 支持多Agent统一调度
echo.
echo 🚀 开始使用吧！

pause
