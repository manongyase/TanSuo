@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

rem ============================================================
rem  TanSuo → GitHub 一键推送
rem  仓库: https://github.com/manongyase/WebPage
rem  目标: D:\前端_页面
rem  用法: 双击运行即可，或右键"以管理员身份运行"
rem ============================================================

set "REPO_URL=https://github.com/manongyase/WebPage.git"
set "TARGET=D:\前端_页面"
set "BRANCH=main"

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       TanSuo → GitHub 一键推送脚本       ║
echo  ╚══════════════════════════════════════════╝
echo.

rem ---- 1. 检查目录 ----
if not exist "%TARGET%\.git" (
  echo  ✗ %TARGET% 不是 git 仓库
  echo  正在执行 git init...
  cd /d "%TARGET%"
  git init -q
  git config user.email "manongyase@users.noreply.github.com"
  git config user.name "manongyase"
  git checkout -q -b master 2>nul
) else (
  cd /d "%TARGET%"
  echo  ✓ 找到 git 仓库: %TARGET%
)

rem ---- 2. 检查 git ----
where git >nul 2>&1
if errorlevel 1 (
  echo  ✗ 没装 git，去 https://git-scm.com 下载安装
  pause
  exit /b 1
)

rem ---- 3. 配置 remote ----
echo.
echo  检查 remote...
git remote | findstr /c:"origin" >nul 2>&1
if errorlevel 1 (
  echo  + 添加 origin: %REPO_URL%
  git remote add origin "%REPO_URL%"
) else (
  for /f "tokens=*" %%R in ('git remote get-url origin 2^>nul') do set "CURRENT=%%R"
  echo  ✓ origin = !CURRENT!
  if not "!CURRENT!"=="%REPO_URL%" (
    echo  ~ URL 不匹配，更新为正确地址
    git remote set-url origin "%REPO_URL%"
  )
)

rem ---- 4. 分支 ----
echo.
echo  当前分支:
git branch --show-current
git branch --list "%BRANCH%" | findstr "%BRANCH%" >nul 2>&1
if errorlevel 1 (
  echo  + 创建分支 %BRANCH%
  git checkout -q -b %BRANCH% 2>nul
) else (
  git checkout -q %BRANCH% 2>nul
)

rem ---- 5. 有改动就自动 commit ----
echo.
echo  检查改动...
git status --porcelain | findstr "." >nul 2>&1
if errorlevel 1 (
  echo  ✓ 没有新改动，跳过 commit
) else (
  echo  + 发现改动，自动 commit...
  set "MSG=update: %date:~0,4%-%date:~5,2%-%date:~8,2% %time:~0,2%:%time:~3,2%"
  set "MSG=!MSG: =0!"
  git add -A
  git commit -m "!MSG!"
  if errorlevel 1 (
    echo  ✗ commit 失败
    pause
    exit /b 1
  )
  echo  ✓ commit 成功
)

rem ---- 6. push ----
echo.
echo  ── 推送到 GitHub ──
git push -u origin %BRANCH%
if errorlevel 1 (
  echo.
  echo  ✗ push 失败，常见原因:
  echo     1) 没配置 GitHub credential → 运行: gh auth login
  echo        或 https://github.com/settings/tokens 生成 token 后用
  echo        git remote set-url origin https://manongyase:TOKEN@github.com/...
  echo     2) 仓库是私有的但没权限
  echo     3) 网络不通 github.com
  echo.
  pause
  exit /b 1
)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║              ✓ 推送完成 ✓                 ║
echo  ║       https://github.com/manongyase/WebPage
echo  ╚══════════════════════════════════════════╝
echo.
pause
