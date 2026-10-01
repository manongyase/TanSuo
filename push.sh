#!/usr/bin/env bash
# ============================================================
#   TanSuo Repo Push Entry (Git Bash / WSL)
#   Usage:
#     ./push.sh                      -> popup for commit msg
#     ./push.sh -Log "your message"   -> CLI with inline msg
#   Deps: Git Bash or WSL + Windows built-in PowerShell
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  TanSuo Repo Push (push.sh)"
echo "============================================================"
echo ""

if [[ "$SCRIPT_DIR" == /mnt/* ]]; then
    PS1_PATH="$(wslpath -w "$SCRIPT_DIR/push.ps1")"
else
    PS1_PATH="$(cygpath -w "$SCRIPT_DIR/push.ps1")"
fi

echo ">>> Launching push.ps1 ..."
echo "    args: $@"
echo ""

powershell.exe -ExecutionPolicy Bypass -File "$PS1_PATH" "$@"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo ">>> Push done."
else
    echo ">>> Push FAILED.  exit code: $EXIT_CODE"
fi