#!/usr/bin/env bash
# TanSuo 数据备份脚本
# 用法: ./scripts/backup-db.sh
# 做三件事:
#   1. 从 WSL SQLite 导出 items + memos 成 JSON
#   2. 把 .db 文件（含 WAL/SHM）同步到 D:\前端_页面\data\
#   3. 把 JSON 也存一份到 D:\前端_页面\data\（便于迁移和跨平台查看）
set -euo pipefail

DB_DIR="${TANSUO_DB_DIR:-/home/front/.tansuo-web}"
DB_FILE="${TANSUO_DB:-$DB_DIR/tansuo.db}"
BACKUP_ROOT="/mnt/d/前端_页面"
DATA_DIR="$BACKUP_ROOT/data"
TS=$(date +%Y%m%d-%H%M%S)

# 颜色
YELLOW='\033[1;33m'; GREEN='\033[1;32m'; RED='\033[1;31m'; NC='\033[0m'

echo -e "${YELLOW}=== TanSuo DB 备份 ===${NC}"
echo "源: $DB_FILE"
echo "目标: $DATA_DIR"
echo

if [ ! -f "$DB_FILE" ]; then
  echo -e "${RED}✗ 数据库文件不存在: $DB_FILE${NC}"
  echo "环境变量 TANSUO_DB 或 TANSUO_DB_DIR 可能配错了"
  exit 1
fi

source ~/.nvm/nvm.sh 2>/dev/null || true

# ---------- 1. 导出 JSON ----------
echo -e "${YELLOW}[1/3] 导出 JSON...${NC}"

EXPORT_SCRIPT=$(cat <<'NODE'
const Database = require('/home/front/tansuo-web/node_modules/better-sqlite3');
const db = new Database(process.env.TANSUO_DB || '/home/front/.tansuo-web/tansuo.db', { readonly: true });
const items = db.prepare('SELECT * FROM items').all();
const memos = db.prepare('SELECT * FROM memos').all();
console.log(JSON.stringify({ exportedAt: new Date().toISOString(), items, memos }, null, 2));
db.close();
NODE
)

mkdir -p "$DATA_DIR"
node -e "$EXPORT_SCRIPT" > "$DATA_DIR/tansuo-data.json"

ITEM_COUNT=$(node -e "const d = require('$DATA_DIR/tansuo-data.json'); console.log(d.items.length)")
MEMO_COUNT=$(node -e "const d = require('$DATA_DIR/tansuo-data.json'); console.log(d.memos.length)")
echo -e "${GREEN}✓ JSON 导出: $ITEM_COUNT 条 items, $MEMO_COUNT 条 memos${NC}"

# ---------- 2. 拷贝 .db 文件（含 WAL/SHM） ----------
echo -e "${YELLOW}[2/3] 拷贝 SQLite 文件...${NC}"

# 先 checkpoint，确保 WAL 内容写进主 db
if command -v sqlite3 &>/dev/null; then
  sqlite3 "$DB_FILE" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
fi

cp -f "$DB_FILE" "$DATA_DIR/tansuo.db"
cp -f "$DB_FILE" "$DATA_DIR/tansuo-$TS.db"  # 时间戳快照
for ext in wal shm journal; do
  [ -f "$DB_FILE-$ext" ] && cp -f "$DB_FILE-$ext" "$DATA_DIR/" || true
done
echo -e "${GREEN}✓ .db 文件 + 时间戳快照${NC}"

# ---------- 3. 显示结果 ----------
echo -e "${YELLOW}[3/3] 目标目录结构${NC}"
ls -lh "$DATA_DIR"
echo
echo -e "${GREEN}=== 备份完成 ✓ ===${NC}"
echo "→ 同步到 git: cd '$BACKUP_ROOT' && git add data/ && git commit -m 'data: backup $TS' && git push"
