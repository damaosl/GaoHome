@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY%" (
    "%PY%" main.py
) else (
    echo [错误] 未找到 Python 3.12，请先安装：winget install Python.Python.3.12
    pause
)
