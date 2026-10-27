========================================
  TanSuo 项目 · AI 常见错误清单
  最后更新: 2026-10-28
  用途: 每次犯新错追加一条，下次别再犯
========================================


═══════════════════════════════════════
 【Git 类错误】
═══════════════════════════════════════

❌ 错误 #1: 只推 TanSuo 忘了推 WebPage
   现象: 本地改了, Vercel 没反应
   根因: Vercel 绑的是 manongyase/WebPage, 不是 TanSuo
   修复: 每次 push TanSuo 后, 必须同步 WebPage (见 SESSION_START.md)

❌ 错误 #2: 乱加 vercel.json 把 WebPage 搞坏
   现象: Vercel 报 "Invalid vercel.json" / "no output was created"
   根因: 1) "root" 字段 Vercel 不认; 2) 子目录已有 vercel.json 冲突
   修复: WebPage 根目录 **不要有 vercel.json**。用 Vercel Dashboard 设置:
         Root Directory = tansuo-web
         Framework = Vite
         Build Command = npm install && npm run build
         Output Directory = dist
         API Rewrites = 在 Dashboard 的 Functions 里配 /api/:path* → /api/handler

❌ 错误 #3: 强推 --force 前没确认当前 WebPage HEAD
   现象: 把别人(或旧的)的 commit 覆盖掉
   修复: git log --oneline -3 先看, reset --hard 也先确认

❌ 错误 #4: 只复制 handler.js 不复制 lib/ 和 route.js
   现象: Vercel 上登录 500, API 请求全挂
   根因: TanSuo 已拆 Vercel Route Handlers (api/items/route.js 等)
   修复: **不要手动同步 api 层**! 让 WebPage 的 api 保持原样, 只复制 src/ 和 public/


═══════════════════════════════════════
 【Vue / 前端类错误】
═══════════════════════════════════════

❌ 错误 #5: 模板里直接写 import.meta.env.DEV
   现象: Vite build 报 "import.meta may appear only with 'sourceType: module'"
   根因: Vue template 用 compiler-core parse, 不认 ESM import.meta
   修复: script 里先 const isDev = import.meta.env.DEV, 模板用 isDev

❌ 错误 #6: Element.closest() 不认 .xxx-* 通配符
   现象: 运行时 SyntaxError, closest('.head-*') 炸了, 整个事件链崩
   根因: .xxx-* 是 SCSS 语法, 原生 CSS 选择器不支持
   修复: 改成 [class*="head-"] 属性选择器

❌ 错误 #7: 生产构建里留 debug 按钮
   现象: Vercel 上用户看到齿轮按钮
   修复: 用 isDev 控制 v-if, production 完全隐藏


═══════════════════════════════════════
 【WSL / node / 环境类错误】
═══════════════════════════════════════

❌ 错误 #8: 直接用 "wsl node" —— 找不到命令
   现象: bash: node: command not found
   根因: wsl -d Ubuntu 默认 non-login shell, 不加载 .bashrc (没有 nvm)
   修复: 
     1) 用完整路径 /home/front/.nvm/versions/node/v24.22.1/bin/node
     2) 或 wsl -d Ubuntu -- bash -l (login shell 才加载 .bashrc)

❌ 错误 #9: WSL npm install 在 /mnt/f 路径上 ENOTDIR
   现象: npm error ENOTDIR: not a directory, mkdir 'node_modules'
   根因: Windows ↔ WSL 文件系统桥接冲突, Windows 那边删不干净 node_modules
   修复: 
     1) Windows PowerShell: Remove-Item -Recurse -Force node_modules
     2) WSL 确认: ls -la | grep node_modules (应该不存在)
     3) 再 WSL 里 npm install
     4) 不行就 npm install 到 WSL 本地, 再拷回来:
        npm install --prefix ~/tansuo-web-tmp
        cp -r ~/tansuo-web-tmp/node_modules /mnt/f/TanSuo/tansuo-web/

❌ 错误 #10: node_modules/.bin/vite 有 CRLF
   现象: /usr/bin/env: 'bash\r': No such file or directory
   根因: Windows 挂载 + PowerShell 复制带 CRLF
   修复: 不要用 .bin/vite, 直接 node node_modules/vite/bin/vite.js


═══════════════════════════════════════
 【本地开发 / Vite 类错误】
═══════════════════════════════════════

❌ 错误 #11: 改了代码浏览器没更新
   根因 A: Vite HMR 卡死 → rm -rf node_modules/.vite + 重启 vite
   根因 B: 浏览器模块缓存 → **关掉标签页重新打开**, Ctrl+Shift+R 不够
   根因 C: WSL 文件桥接延迟 → 等 5-10 秒再看

❌ 错误 #12: Element Plus 组件拦截 mousemove
   现象: 能 mousedown 但 mousemove 冒泡不到 document, 拖不动
   根因: EP 内部事件 stopPropagation
   修复: pointerdown 时对 target 调 setPointerCapture(e.pointerId)
         后续所有 pointermove/up 事件被强制定向到 target


═══════════════════════════════════════
 【推送前 Checklist】
═══════════════════════════════════════

每次 commit push 前，过一遍：
  □ 只改了 src/*.vue / src/*.css / public/* —— 没动 api/ (除非明确要动)
  □ 没加 vercel.json —— Vercel Dashboard 里配
  □ 生产环境 debug 按钮用 isDev 控制了吗？
  □ 模板里有 import.meta 吗？ —— 不能有！
  □ TanSuo push 完 → 同步 WebPage 了吗？
  □ 两个仓库 hash 一致吗？ git ls-remote origin refs/heads/main
