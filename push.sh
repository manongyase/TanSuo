#!/usr/bin/env bash
# ============================================================
#   TanSuo 仓库推送入口 (Git Bash / WSL 版)
#   用法:
#     ./push.sh                      # 弹窗输入 commit message
#     ./push.sh -Log "改动说明"       # 直接带参数
#   依赖: Git Bash 或 WSL + Windows 自带 PowerShell
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  TanSuo 仓库推送 (push.sh)"
echo "============================================================"
echo ""

if [[ "$SCRIPT_DIR" == /mnt/* ]]; then
    PS1_PATH="$(wslpath -w "$SCRIPT_DIR/push.ps1")"
else
    PS1_PATH="$(cygpath -w "$SCRIPT_DIR/push.ps1")"
fi

echo ">>> 触发 push.ps1 ..."
echo "    参数: $@"
echo ""

powershell.exe -ExecutionPolicy Bypass -File "$PS1_PATH" "$@"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo ">>> 推送完成 ✓"
else
    echo ">>> 推送失败 ✗ (exit code: $EXIT_CODE)"
fi