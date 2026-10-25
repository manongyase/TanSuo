#!/usr/bin/env bash
# 在 WSL 的 front 用户下启动 TanSuo Web 开发服务器
export NVM_DIR="$HOME/.nvm"
set +e
. "$NVM_DIR/nvm.sh"
set -e

cd /home/front/tansuo-web
exec npm run dev -- --host 0.0.0.0
