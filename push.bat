@echo off
REM ============================================================
REM   TanSuo Repo Push Entry (Windows Double-Click)
REM   Usage:
REM     Double-click push.bat         -> popup for commit msg
REM     push.bat -Log "your message"  -> CLI with inline msg
REM   Deps: None (uses built-in PowerShell)
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo   TanSuo Repo Push (push.bat)
echo ============================================================
echo.
echo ^>^>^> Launching push.ps1 ...
echo.

powershell.exe -ExecutionPolicy Bypass -File ".\push.ps1" %*
set EXIT_CODE=%ERRORLEVEL%

echo.
if %EXIT_CODE% EQU 0 (
    echo ^>^>^> Push done.
) else (
    echo ^>^>^> Push FAILED.  exit code: %EXIT_CODE%
)

echo.
pause