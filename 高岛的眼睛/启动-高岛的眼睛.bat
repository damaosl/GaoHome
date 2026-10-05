@echo off
chcp 936 >nul
title 高岛的眼睛
cd /d "%~dp0"

if not exist "dist\index.js" (
    echo [高岛的眼睛] 未找到构建产物，先执行构建...
    call npm run build
    if errorlevel 1 (
        echo [错误] 构建失败，请先运行 npm install 再重试。
        pause
        exit /b 1
    )
)

echo.
echo    高岛的眼睛
echo    代理    127.0.0.1:8888
echo    控制台  http://127.0.0.1:8787
echo    关闭本窗口即停止服务
echo.

rem 2 秒后自动打开控制台页面
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8787'"

node dist\index.js

echo.
echo [高岛的眼睛] 已停止。
pause
