#!/usr/bin/env bash
# TanSuo 数据恢复脚本
# 用法: ./scripts/restore-db.sh                     # 用最新 tansuo.db 覆盖
#      ./scripts/restore-db.sh tansuo-20261025.db   # 指定某个时间戳快照
#      ./scripts/restore-db.sh --from-json          # 用 tansuo-data.json 通过 API 重灌（最安全）
set -euo pipefail

DB_DIR="${TANSUO_DB_DIR:-/home/front/.tansuo-web}"
DB_FILE="${TANSUO_DB:-$DB_DIR/tansuo.db}"
BACKUP_ROOT="/mnt/d/前端_页面"
DATA_DIR="$BACKUP_ROOT/data"
MODE="${1:-db}"

YELLOW='\033[1;33m'; GREEN='\033[1;32m'; RED='\033[1;31m'; NC='\033[0m'

echo -e "${YELLOW}=== TanSuo DB 恢复 ===${NC}"
echo "模式: $MODE"
echo "目标: $DB_FILE"
echo

mkdir -p "$DB_DIR"

if [ "$MODE" = "--from-json" ]; then
  # 方式 A: 通过本地 Vite API 导入（走 SQLite + watch 持久化）
  echo -e "${YELLOW}[JSON → API]  先清空再批量导入...${NC}"
  if ! curl -s http://localhost:5173/api/health >/dev/null 2>&1; then
    echo -e "${RED}✗ 本地 Vite 没在跑 (localhost:5173)，先启动守护进程${NC}"
    echo "  cd /home/front/scripts && ./daemon-start.sh"
    exit 1
  fi
  curl -s -X POST http://localhost:5173/api/items/clear >/dev/null
  curl -s -X POST http://localhost:5173/api/memos/clear >/dev/null
  curl -s -X POST http://localhost:5173/api/migrate \
    -H 'Content-Type: application/json' \
    --data-binary "@$DATA_DIR/tansuo-data.json" >/dev/null
  echo -e "${GREEN}✓ JSON 导入完成${NC}"
  exit 0
fi

# 方式 B: 直接 .db 文件覆盖（最快最彻底）
SRC_FILE="$DATA_DIR/$MODE"
[ "$MODE" = "db" ] && SRC_FILE="$DATA_DIR/tansuo.db"

if [ ! -f "$SRC_FILE" ]; then
  echo -e "${RED}✗ 找不到备份文件: $SRC_FILE${NC}"
  echo "可用文件:"
  ls "$DATA_DIR/tansuo"* 2>/dev/null || echo "  （data 目录是空的）"
  exit 1
fi

echo -e "${YELLOW}[DB 文件直接覆盖] $SRC_FILE → $DB_FILE${NC}"

# 停守护进程避免写入冲突
cd /home/front/scripts && bash daemon-stop.sh 2>/dev/null || true
sleep 2

# 备份当前 db（以防手滑）
if [ -f "$DB_FILE" ]; then
  cp -f "$DB_FILE" "$DB_FILE.bak-$(date +%Y%m%d-%H%M%S)"
fi

# 覆盖
cp -f "$SRC_FILE" "$DB_FILE"
# 清 WAL/SHM（让覆盖生效）
rm -f "$DB_FILE-wal" "$DB_FILE-shm" "$DB_FILE-journal"

# 重启守护
bash /home/front/scripts/daemon-start.sh 2>/dev/null || true
sleep 3

# 验证
echo
curl -s http://localhost:5173/api/health
echo
echo -e "${GREEN}=== 恢复完成 ✓ ===${NC}"
