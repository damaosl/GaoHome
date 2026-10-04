@echo off
chcp 936 >nul
setlocal
cd /d "%~dp0"

set "VCVARS=d:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%VCVARS%" (
    echo [ERROR] MSVC environment not found: %VCVARS%
    pause
    exit /b 1
)

call "%VCVARS%"
if errorlevel 1 (
    echo [ERROR] Failed to load MSVC environment.
    pause
    exit /b 1
)

if not exist build mkdir build

echo [1/3] Compiling resources...
"d:\Windows Kits\10\bin\10.0.26100.0\x64\rc.exe" /nologo /fo build\app.res app.rc
if errorlevel 1 (
    echo [ERROR] Resource compile failed.
    pause
    exit /b 1
)

echo [2/3] Compiling...
cl /nologo /W3 /O2 /std:c++17 /EHsc /utf-8 /DUNICODE /D_UNICODE ^
   src\main.cpp src\converter.cpp build\app.res ^
   /Fo:build\ /Fe:build\VideoToAudio.exe ^
   /link /SUBSYSTEM:WINDOWS user32.lib gdi32.lib comdlg32.lib shell32.lib comctl32.lib
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

copy /y build\VideoToAudio.exe "¸ßµºµÄ¸ÖÇÙ¿Î.exe" >nul
echo [3/3] Done: ¸ßµºµÄ¸ÖÇÙ¿Î.exe
pause