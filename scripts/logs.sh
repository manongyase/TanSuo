#!/usr/bin/env bash
# ============================================================
# TanSuo Web · 查看运行状态与最近日志
# 用法：bash logs.sh         （root 或 front 用户均可）
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

if [ "$(id -un)" != "$APP_USER" ]; then
  if [ "$(id -u)" -eq 0 ]; then
    exec su - "$APP_USER" -c "bash '$0' $*"
  fi
  echo "请用 root 或 ${APP_USER} 用户运行"
  exit 1
fi

read_pid() {
  cat "$1" 2>/dev/null || true
}

format_duration() {
  local total="${1:-0}"
  local h=$((total / 3600))
  local m=$(((total % 3600) / 60))
  local s=$((total % 60))
  if [ "$h" -gt 0 ]; then
    printf '%dh %dm %ds' "$h" "$m" "$s"
  elif [ "$m" -gt 0 ]; then
    printf '%dm %ds' "$m" "$s"
  else
    printf '%ds' "$s"
  fi
}

line() {
  printf '%s\n' '----------------------------------------------'
}

echo "===== TanSuo Web 服务状态 ====="
echo "时间: $(date '+%F %T')"
echo

DAEMON_RUNNING=0
if [ -f "$DAEMON_PID_FILE" ] && kill -0 "$(read_pid "$DAEMON_PID_FILE")" 2>/dev/null; then
  DAEMON_RUNNING=1
fi

VITE_RUNNING=0
if [ -f "$VITE_PID_FILE" ] && kill -0 "$(read_pid "$VITE_PID_FILE")" 2>/dev/null; then
  VITE_RUNNING=1
fi

if [ "$DAEMON_RUNNING" -eq 1 ]; then
  echo "运行模式: 守护模式（daemon PID $(read_pid "$DAEMON_PID_FILE")）"
elif [ "$VITE_RUNNING" -eq 1 ]; then
  echo "运行模式: 普通模式（PID $(read_pid "$VITE_PID_FILE")）"
else
  echo "运行模式: 未运行"
fi

if [ "$VITE_RUNNING" -eq 1 ]; then
  VITE_PID="$(read_pid "$VITE_PID_FILE")"
  echo "vite 进程: 运行中（PID ${VITE_PID}）"
  UPTIME="$(ps -o etimes= -p "$VITE_PID" 2>/dev/null | tr -d ' ' || true)"
  if [ -n "$UPTIME" ]; then
    echo "运行时长: $(format_duration "$UPTIME")"
  fi
  RSS_KB="$(ps -o rss= -p "$VITE_PID" 2>/dev/null | tr -d ' ' || true)"
  if [ -n "$RSS_KB" ]; then
    echo "内存占用: $((RSS_KB / 1024)) MB"
  fi
else
  echo "vite 进程: 未运行"
fi

if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
  echo "端口 ${PORT}: 监听中"
else
  echo "端口 ${PORT}: 未监听"
fi

if command -v curl >/dev/null 2>&1; then
  RESULT="$(curl -s -o /dev/null -w '%{http_code} %{time_total}' --max-time 3 "http://localhost:${PORT}/" 2>/dev/null || true)"
  CODE="${RESULT%% *}"
  COST="${RESULT##* }"
  if [ -n "$CODE" ] && [ "$CODE" != "000" ]; then
    echo "HTTP 检查: ${CODE}（耗时 ${COST}s）"
  else
    echo "HTTP 检查: 无法访问"
  fi
else
  echo "HTTP 检查: 未安装 curl，跳过"
fi

LOCAL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "访问地址: http://localhost:${PORT}"
if [ -n "$LOCAL_IP" ]; then
  echo "局域网:   http://${LOCAL_IP}:${PORT}"
fi

echo
echo "日志文件:"
echo "  vite:   ${VITE_LOG}"
echo "  daemon: ${DAEMON_LOG}"

echo
echo "最近 10 条 vite 日志:"
line
if [ -f "$VITE_LOG" ] && [ -s "$VITE_LOG" ]; then
  tail -n 10 "$VITE_LOG"
else
  echo "（暂无日志文件）"
fi
line

if [ "$DAEMON_RUNNING" -eq 1 ] && [ -f "$DAEMON_LOG" ]; then
  echo
  echo "最近 5 条守护日志:"
  line
  tail -n 5 "$DAEMON_LOG"
  line
fi

echo
if [ "$DAEMON_RUNNING" -eq 1 ]; then
  echo "停止服务: bash /home/front/scripts/daemon-stop.sh"
elif [ "$VITE_RUNNING" -eq 1 ]; then
  echo "停止服务: bash /home/front/scripts/stop.sh"
else
  echo "启动服务: bash /home/front/scripts/start.sh 或 bash /home/front/scripts/daemon-start.sh"
fi
