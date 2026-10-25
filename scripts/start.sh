#!/usr/bin/env bash
# ============================================================
# TanSuo Web · 普通后台启动
# 用法：bash start.sh        （root 或 front 用户均可）
# ============================================================
set -eo pipefail

APP_USER="front"
APP_DIR="/home/front/tansuo-web"
PORT="5173"
RUN_DIR="$APP_DIR/.run"
PID_FILE="$RUN_DIR/vite.pid"
DAEMON_PID_FILE="$RUN_DIR/daemon.pid"
LOG_FILE="$RUN_DIR/vite.log"

if [ "$(id -un)" != "$APP_USER" ]; then
  if [ "$(id -u)" -eq 0 ]; then
    exec su - "$APP_USER" -c "bash '$0' $*"
  fi
  echo "请用 root 或 ${APP_USER} 用户运行"
  exit 1
fi

export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  set +e
  . "$NVM_DIR/nvm.sh"
  set -e
fi

if ! command -v node >/dev/null 2>&1; then
  echo "未找到 node，请先运行 setup-node.sh"
  exit 1
fi

if [ ! -d "$APP_DIR/node_modules" ]; then
  echo "依赖未安装，请先运行：sudo bash /mnt/f/TanSuo/setup-web.sh"
  exit 1
fi

mkdir -p "$RUN_DIR"

is_running() {
  [ -f "$PID_FILE" ] || return 1
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

if is_running; then
  echo "TanSuo Web 已在运行（PID $(cat "$PID_FILE")）：http://localhost:${PORT}"
  exit 0
fi

if [ -f "$DAEMON_PID_FILE" ] && kill -0 "$(cat "$DAEMON_PID_FILE" 2>/dev/null)" 2>/dev/null; then
  echo "守护模式正在运行，请使用 daemon-stop.sh 停止后再普通启动"
  exit 1
fi

rm -f "$PID_FILE"

if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
  echo "端口 ${PORT} 已被占用："
  ss -ltnp 2>/dev/null | grep ":${PORT} " || true
  exit 1
fi

cd "$APP_DIR"
echo ">>> 启动 TanSuo Web ..."
setsid nohup npm run dev -- --host 0.0.0.0 --port "$PORT" > "$LOG_FILE" 2>&1 < /dev/null &
echo $! > "$PID_FILE"

for _ in $(seq 1 30); do
  if grep -q "Local:" "$LOG_FILE" 2>/dev/null; then
    echo "启动成功（PID $(cat "$PID_FILE")）：http://localhost:${PORT}"
    echo "日志：$LOG_FILE"
    exit 0
  fi
  if ! is_running; then
    echo "启动失败，最近日志："
    tail -n 30 "$LOG_FILE" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 1
  fi
  sleep 1
done

echo "启动超时，请查看日志：$LOG_FILE"
tail -n 30 "$LOG_FILE" 2>/dev/null || true
exit 1
