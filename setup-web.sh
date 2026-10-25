#!/usr/bin/env bash
# ============================================================
# TanSuo Web · 一键部署脚本（WSL / Ubuntu）
# 作用：创建 front 用户 -> 同步前端源码 -> 安装依赖 -> 可选启动
#
# 用法：
#   sudo bash /mnt/f/TanSuo/setup-web.sh          # 只安装
#   sudo bash /mnt/f/TanSuo/setup-web.sh --dev    # 安装后启动开发服务器
#
# 启动后通过 Windows 浏览器访问：http://localhost:5173
# ============================================================

set -eo pipefail

APP_USER="front"
SRC_DIR="/mnt/f/TanSuo/tansuo-web"
APP_DIR="/home/${APP_USER}/tansuo-web"
NPM_REGISTRY="https://registry.npmmirror.com"

if [ "$(id -u)" -ne 0 ] && [ "$(id -un)" != "$APP_USER" ]; then
  echo "请用 root 运行：sudo bash $0"
  exit 1
fi

if [ "$(id -un)" != "$APP_USER" ]; then
  if ! id "$APP_USER" >/dev/null 2>&1; then
    echo ">>> 创建用户 ${APP_USER}"
    useradd -m -s /bin/bash "$APP_USER"
  else
    echo ">>> 用户 ${APP_USER} 已存在"
  fi
  echo ">>> 切换到 ${APP_USER} 执行安装"
  exec su - "$APP_USER" -c "bash '$0' $*"
fi

# ---- 以下以 front 用户身份执行 ----
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  set +e
  . "$NVM_DIR/nvm.sh"
  set -e
fi

if ! command -v node >/dev/null 2>&1; then
  echo "未找到 node。请先以 ${APP_USER} 用户运行 setup-node.sh 安装 nvm + Node.js LTS。"
  exit 1
fi

echo ">>> Node $(node -v) / npm $(npm -v)"

echo ">>> 同步源码：${SRC_DIR} -> ${APP_DIR}"
mkdir -p "$APP_DIR"
cp -r "$SRC_DIR/." "$APP_DIR/"

cd "$APP_DIR"

echo ">>> 安装依赖（使用 npmmirror 源）"
# 部分 WSL 网络环境会中断 TLS 1.3 握手，强制使用 TLS 1.2 可避免 ECONNRESET
NODE_OPTIONS="--tls-max-v1.2" npm install --registry="$NPM_REGISTRY"

echo ">>> 安装完成"

if [ "${1:-}" = "--dev" ]; then
  echo ">>> 启动开发服务器：http://localhost:5173"
  exec npm run dev -- --host 0.0.0.0
fi

echo ">>> 启动命令："
echo "    su - ${APP_USER} -c 'cd ${APP_DIR} && source ~/.nvm/nvm.sh && npm run dev -- --host 0.0.0.0'"
