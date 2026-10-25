#!/usr/bin/env bash
# ============================================================
# TanSuo Web · 守护模式启动（进程崩溃自动拉起）
# 用法：bash daemon-start.sh   （root 或 front 用户均可）
# 说明：守护进程每 5 秒检查一次，vite 不在就自动重启
# ============================================================
set -eo pipefail

APP_USER="front"
APP_DIR="/home/front/tansuo-web"
PORT="5173"
RUN_DIR="$APP_DIR/.run"
VITE_PID_FILE="$RUN_DIR/vite.pid"
DAEMON_PID_FILE="$RUN_DIR/daemon.pid"
VITE_LOG="$RUN_DIR/vite.log"
DAEMON_LOG="$RUN_DIR/daemon.log"

# ---------- 内部模式：守护循环 ----------
if [ "${1:-}" = "--loop" ]; then
  export NVM_DIR="$HOME/.nvm"
  if [ -s "$NVM_DIR/nvm.sh" ]; then
    set +e
    . "$NVM_DIR/nvm.sh"
    set -e
  fi

  cd "$APP_DIR"
  mkdir -p "$RUN_DIR"

  vite_alive() {
    [ -f "$VITE_PID_FILE" ] || return 1
    local pid
    pid="$(cat "$VITE_PID_FILE" 2>/dev/null || true)"
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
  }

  start_vite() {
    local old
    if [ -f "$VITE_PID_FILE" ]; then
      old="$(cat "$VITE_PID_FILE" 2>/dev/null || true)"
      if [ -n "$old" ]; then
        kill -TERM -- "-${old}" 2>/dev/null || kill -TERM "${old}" 2>/dev/null || true
        sleep 1
        kill -KILL -- "-${old}" 2>/dev/null || kill -KILL "${old}" 2>/dev/null || true
      fi
      rm -f "$VITE_PID_FILE"
    fi
    echo "[$(date '+%F %T')] 启动 vite"
    setsid nohup npm run dev -- --host 0.0.0.0 --port "$PORT" >> "$VITE_LOG" 2>&1 < /dev/null &
    echo $! > "$VITE_PID_FILE"
  }

  on_exit() {
    echo "[$(date '+%F %T')] 守护进程退出，停止 vite"
    if vite_alive; then
      local pid
      pid="$(cat "$VITE_PID_FILE")"
      kill -TERM -- "-${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
    fi
    rm -f "$VITE_PID_FILE"
    exit 0
  }
  trap on_exit TERM INT

  echo "[$(date '+%F %T')] 守护进程启动（PID $$）"
  while true; do
    if ! vite_alive; then
      start_vite
      sleep 3
      if ! vite_alive; then
        echo "[$(date '+%F %T')] vite 启动失败，5 秒后重试"
        sleep 5
      fi
    fi
    sleep 5
  done
fi

# ---------- 外部模式：启动守护 ----------
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

daemon_alive() {
  [ -f "$DAEMON_PID_FILE" ] || return 1
  local pid
  pid="$(cat "$DAEMON_PID_FILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

vite_alive() {
  [ -f "$VITE_PID_FILE" ] || return 1
  local pid
  pid="$(cat "$VITE_PID_FILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

if daemon_alive; then
  echo "守护模式已在运行（PID $(cat "$DAEMON_PID_FILE")）：http://localhost:${PORT}"
  exit 0
fi

if vite_alive; then
  echo "检测到普通模式实例正在运行，请先执行：bash stop.sh"
  exit 1
fi

if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
  echo "端口 ${PORT} 已被占用："
  ss -ltnp 2>/dev/null | grep ":${PORT} " || true
  exit 1
fi

rm -f "$DAEMON_PID_FILE" "$VITE_PID_FILE"
: > "$VITE_LOG"

echo ">>> 以守护模式启动 TanSuo Web ..."
setsid nohup bash "$0" --loop >> "$DAEMON_LOG" 2>&1 < /dev/null &
echo $! > "$DAEMON_PID_FILE"

for _ in $(seq 1 30); do
  if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
    echo "守护模式启动成功（守护 PID $(cat "$DAEMON_PID_FILE")）：http://localhost:${PORT}"
    echo "退出守护请执行：bash daemon-stop.sh"
    exit 0
  fi
  if ! daemon_alive; then
    echo "守护进程意外退出，日志："
    tail -n 30 "$DAEMON_LOG" 2>/dev/null || true
    rm -f "$DAEMON_PID_FILE"
    exit 1
  fi
  sleep 1
done

echo "启动超时，请查看日志：$DAEMON_LOG"
tail -n 30 "$DAEMON_LOG" 2>/dev/null || true
exit 1
