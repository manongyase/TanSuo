#!/usr/bin/env bash
# ============================================================
# TanSuo Web · 停止普通后台进程
# 用法：bash stop.sh         （root 或 front 用户均可）
# ============================================================
set -eo pipefail

APP_USER="front"
APP_DIR="/home/front/tansuo-web"
PORT="5173"
RUN_DIR="$APP_DIR/.run"
PID_FILE="$RUN_DIR/vite.pid"
DAEMON_PID_FILE="$RUN_DIR/daemon.pid"

if [ "$(id -un)" != "$APP_USER" ]; then
  if [ "$(id -u)" -eq 0 ]; then
    exec su - "$APP_USER" -c "bash '$0' $*"
  fi
  echo "请用 root 或 ${APP_USER} 用户运行"
  exit 1
fi

is_running() {
  [ -f "$PID_FILE" ] || return 1
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

if [ -f "$DAEMON_PID_FILE" ] && kill -0 "$(cat "$DAEMON_PID_FILE" 2>/dev/null)" 2>/dev/null; then
  echo "检测到守护模式正在运行，请使用 daemon-stop.sh 停止"
  exit 1
fi

if ! is_running; then
  echo "TanSuo Web 未运行"
  rm -f "$PID_FILE"
  exit 0
fi

PID="$(cat "$PID_FILE")"
echo ">>> 停止 TanSuo Web（PID ${PID}）..."
kill -TERM -- "-${PID}" 2>/dev/null || kill -TERM "${PID}" 2>/dev/null || true

for _ in $(seq 1 15); do
  kill -0 "$PID" 2>/dev/null || break
  sleep 1
done

if kill -0 "$PID" 2>/dev/null; then
  echo ">>> 进程未退出，强制结束"
  kill -KILL -- "-${PID}" 2>/dev/null || kill -KILL "${PID}" 2>/dev/null || true
fi

rm -f "$PID_FILE"
echo "已停止（端口 ${PORT} 已释放）"
