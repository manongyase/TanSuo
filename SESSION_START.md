========================================
  SESSION START · 新会话必读
  最后更新: 2026-10-28
  → 每次新会话开始, 先读这个文件 ←
========================================


═══════════════════════════════════════
 0. 快速三句话
═══════════════════════════════════════

1. 双仓库: TanSuo(开发) → WebPage(Vercel 部署)
   每次 push TanSuo 后, 必须把前端文件复制到 WebPage 再 push

2. 只改前端 (src/*.vue, src/*.css, public/*) —— 别动 api/
   除非明确说要改 API

3. Vercel 不用 vercel.json —— Dashboard 里配


═══════════════════════════════════════
 1. 仓库地图
═══════════════════════════════════════

  TanSuo  (开发主仓库)
  ├─ origin: https://github.com/manongyase/TanSuo.git  (master 分支)
  └─ 位置: f:\TanSuo

  WebPage (Vercel 部署仓库)
  ├─ origin: https://github.com/manongyase/WebPage.git  (main 分支)
  ├─ 位置: f:\WebPage  (刚 clone 下来的)
  └─ Vercel: happymira.vercel.app 绑的是这个

  ⚠️ 两个仓库都有 tansuo-web/ 子目录, 前端代码在里面


═══════════════════════════════════════
 2. 双仓库同步命令 (Windows PowerShell)
═══════════════════════════════════════

  # Step 1: 改 TanSuo 的 tansuo-web/src/* 代码 (工作目录)
  # Step 2: 推 TanSuo
  cd f:\TanSuo
  git add -A
  git commit -m "你的改动说明"
  git -c http.sslVerify=false push origin master

  # Step 3: 同步前端文件到 WebPage (⚠️ 只复制 src/ 和 public/)
  Copy-Item -Force f:\TanSuo\tansuo-web\src\*.vue f:\WebPage\tansuo-web\src\
  Copy-Item -Force f:\TanSuo\tansuo-web\src\*.css f:\WebPage\tansuo-web\src\
  Copy-Item -Force f:\TanSuo\tansuo-web\src\main.js f:\WebPage\tansuo-web\src\
  # public/ 整个目录复制 (版本文件等)
  Copy-Item -Recurse -Force f:\TanSuo\tansuo-web\public\* f:\WebPage\tansuo-web\public\

  # Step 4: 推 WebPage
  cd f:\WebPage
  git add -A
  git commit -m "sync: 同 TanSuo 那次 commit 说明"
  git -c http.sslVerify=false push origin main

  # Step 5: 验证
  git -c http.sslVerify=false ls-remote origin refs/heads/main
  # 等 30-60 秒 Vercel 自动部署


═══════════════════════════════════════
 3. 鉴权用户 (D1 SQLite 硬编码)
═══════════════════════════════════════

  admin / 宇宙之疯牛倜傥  → admin
  张文秀 / 张文秀        → viewer


═══════════════════════════════════════
 4. 本地起 dev server
═══════════════════════════════════════

  # WSL 里起 (推荐, 有 node v24)
  # 完整路径, 别依赖 PATH
  wsl -d Ubuntu -u front -- bash -c "cd /mnt/f/TanSuo/tansuo-web && /home/front/.nvm/versions/node/v24.22.1/bin/node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5180"

  # 关的话:
  wsl -d Ubuntu -u front -- bash -c "pkill -f vite"

  # 装依赖 (node_modules 坏了):
  wsl -d Ubuntu -u front -- bash -c "cd /mnt/f/TanSuo/tansuo-web && rm -rf node_modules && npm install --registry https://registry.npmmirror.com"


═══════════════════════════════════════
 5. Vercel Dashboard 配置 (不用 vercel.json!)
═══════════════════════════════════════

  Project: happymira
  Git Connected: manongyase/WebPage · main
  Root Directory: tansuo-web
  Framework: Vite (自动检测)
  Build Command: npm install && npm run build
  Output Directory: dist

  API Functions: /api/handler.js 自动识别 (Edge Runtime)
  部署完手动 Redeploy: Project → Deployments → ⋯ → Redeploy


═══════════════════════════════════════
 6. 生产环境 vs 开发环境
═══════════════════════════════════════

  Vite 里 import.meta.env.DEV 自动:
    本地 npm run dev  → DEV=true  (显示齿轮等 debug 功能)
    npm run build     → DEV=false (齿轮等自动隐藏)

  ⚠️ Vue 模板里不能直接写 import.meta.env.DEV!
     先 script 里 const isDev = import.meta.env.DEV
     模板里 v-if="isDev"


═══════════════════════════════════════
 7. 文件结构速查
═══════════════════════════════════════

  tansuo-web/
  ├── api/                          ← 后端 API (别乱改!)
  │   ├── handler.js                  Vercel Edge Functions 薄路由
  │   ├── lib/d1.js, auth.js, stores.js  业务逻辑
  │   └── items/route.js, memos/route.js  路径 handler
  ├── server/api.js, db.js          ← 本地开发用 better-sqlite3
  ├── src/                          ← 前端 (主要改这里!)
  │   ├── App.vue                     主组件 (模板 + script)
  │   ├── api.js                      前端 API 调用
  │   ├── style.css                   全局样式
  │   └── main.js                      入口
  ├── public/                       ← 静态文件 (版本号等)
  ├── index.html
  ├── package.json
  └── vite.config.js

  ⚠️ 模板分两份: v-if="isMobile" 和 v-else 各自独立, 改的时候两个分支都要改


═══════════════════════════════════════
 8. 常见错误 → 详见 TROUBLESHOOT.md
═══════════════════════════════════════

  十个坑, 下次别再踩
