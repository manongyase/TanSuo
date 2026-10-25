#!/usr/bin/env bash
# ============================================================
# TanSuo Web · 停止守护模式（含守护进程与 vite）
# 用法：bash daemon-stop.sh     （root 或 front 用户均可）
# ============================================================
set -eo pipefail

APP_USER="front"
APP_DIR="/home/front/tansuo-web"
PORT="5173"
RUN_DIR="$APP_DIR/.run"
VITE_PID_FILE="$RUN_DIR/vite.pid"
DAEMON_PID_FILE="$RUN_DIR/daemon.pid"

if [ "$(id -un)" != "$APP_USER" ]; then
  if [ "$(id -u)" -eq 0 ]; then
    exec su - "$APP_USER" -c "bash '$0' $*"
  fi
  echo "请用 root 或 ${APP_USER} 用户运行"
  exit 1
fi

vite_alive() {
  [ -f "$VITE_PID_FILE" ] || return 1
  local pid
  pid="$(cat "$VITE_PID_FILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

stop_vite_leftover() {
  if vite_alive; then
    local pid
    pid="$(cat "$VITE_PID_FILE")"
    kill -TERM -- "-${pid}" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      kill -KILL -- "-${pid}" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$VITE_PID_FILE"
}

if [ ! -f "$DAEMON_PID_FILE" ]; then
  stop_vite_leftover
  echo "守护模式未运行"
  exit 0
fi

DAEMON_PID="$(cat "$DAEMON_PID_FILE" 2>/dev/null || true)"
if [ -z "$DAEMON_PID" ] || ! kill -0 "$DAEMON_PID" 2>/dev/null; then
  rm -f "$DAEMON_PID_FILE"
  stop_vite_leftover
  echo "守护模式未运行"
  exit 0
fi

echo ">>> 停止守护进程（PID ${DAEMON_PID}）及其 vite ..."
kill -TERM -- "-${DAEMON_PID}" 2>/dev/null || kill -TERM "${DAEMON_PID}" 2>/dev/null || true

for _ in $(seq 1 15); do
  kill -0 "$DAEMON_PID" 2>/dev/null || break
  sleep 1
done

if kill -0 "$DAEMON_PID" 2>/dev/null; then
  echo ">>> 守护进程未退出，强制结束"
  kill -KILL -- "-${DAEMON_PID}" 2>/dev/null || kill -KILL "${DAEMON_PID}" 2>/dev/null || true
fi

stop_vite_leftover
rm -f "$DAEMON_PID_FILE"
echo "已停止（端口 ${PORT} 已释放）"
