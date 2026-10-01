@echo off
REM ============================================================
REM   TanSuo 仓库推送入口 (Windows 双击版)
REM   用法:
REM     双击 push.bat                 # 弹窗输入 commit message
REM     push.bat -Log "改动说明"      # 命令行带参数
REM   依赖: 无（Windows 自带 PowerShell）
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo   TanSuo 仓库推送 (push.bat)
echo ============================================================
echo.
echo ^>^>^> 触发 push.ps1 ...
echo.

powershell.exe -ExecutionPolicy Bypass -File ".\push.ps1" %*
set EXIT_CODE=%ERRORLEVEL%

echo.
if %EXIT_CODE% EQU 0 (
    echo ^>^>^> 推送完成 ✓
) else (
    echo ^>^>^> 推送失败 ✗  (exit code: %EXIT_CODE%)
)

echo.
pause