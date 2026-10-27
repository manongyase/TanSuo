========================================
  TanSuo 项目 · AI 踩坑经验手册
  更新: 2026-10-25 v2 (新增鉴权系统、WSL 环境、Vercel 域名、Element Plus 图标)
  用途: 每次执行命令前先过一遍，避免重复踩同坑
========================================


═══════════════════════════════════════
 【一、目录结构铁律】
═══════════════════════════════════════

  ✅ 英文路径放代码，中文路径放运行产物
  ✅ 代码目录命名：douban / food / news / shanxi_food / weather
  ✅ 结果目录命名：天气结果 / 新闻结果 / 美食结果 / 山西菜结果 / 豆瓣榜单结果

  ❌ 禁止在中文路径下放 .py 代码
  ❌ 禁止在英文路径下放时间戳运行结果

  当前正确结构：
    TanSuo/
    ├── douban/           (代码：douban.py 豆瓣榜单)
    ├── food/             (代码)
    ├── news/             (代码：news.py 旧版聚合 / funny_news.py 搞笑 / tech_news.py 科技)
    ├── shanxi_food/      (代码)
    ├── weather/          (代码)
    ├── tansuo-web/       (Vue3 + Vite 前端 + Vercel Edge API + Cloudflare D1)
    │   ├── api/handler.js          ← Vercel Edge Functions 统一入口
    │   ├── lib/d1-client.js        ← D1 REST API 客户端(本地 + Vercel 通用)
    │   ├── server/api.js + db.js  ← 本地 dev 用 better-sqlite3
    │   ├── src/App.vue / api.js / modules.js / main.js
    │   ├── vite.config.js          ← 本地 5173，挂 server/api.js
    │   └── vercel.json             ← rewrites /api/* → /api/handler
    ├── push.ps1          (推送脚本)
    ├── AIReadMe.txt       (本文件)
    └── 其他结果目录       (gitignore)


═══════════════════════════════════════
 【二、API 源可用性实测（2026-10-01）】
═══════════════════════════════════════

  ✅ 能用的（无需 Key）：
    知乎热榜        https://api.zhihu.com/topstory/hot-list?limit=50
    36氪热榜        POST https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot
    Hacker News     https://hacker-news.firebaseio.com/v0/topstories.json
    topurl 新闻     https://news.topurl.cn/api?count=15
    Open-Meteo      https://api.open-meteo.com/v1/forecast（天气备选）
    hitokoto        https://v1.hitokoto.cn/?c=k（一言，随机句子）
    豆瓣影视榜      https://movie.douban.com/j/search_subjects（电影/剧/综艺/动漫）

  ⚠️ 能但要注意：
    高德天气         需 Key（weather/api.json 里有，别提交 git）
    topurl 分类     官方文档只支持 时事/国内/国际/商业，没有"科技"分类
    36氪 gateway    必须 POST，header 要带 Content-Type: application/json
    知乎热榜        纯 GET 就行，不需要 Cookie/签名
    豆瓣影视榜      不同品类支持的 tag 不一样，电视剧 tag 是热门/国产剧/韩剧/美剧/日剧
                    电影 tag 是热门/豆瓣高分/最新/经典/冷门佳片
                    豆瓣读书 JSON 接口已全下线（404），暂无解

  ❌ 实测挂了的（别浪费时间试）：
    api.vvhan.com          DNS 解析失败
    tenapi.cn              全部 502
    api.mcloc.cn            连不上
    api.jikapi.cn           连不上
    api.52vmy.cn            超时
    api.iyk0.com            连不上
    api.pearktrue.cn        连不上
    www.x17c.cn             连不上
    v2ex.com/api            连不上
    juejin 推荐 API         err_no=2 路由不存在
    weibo.com/ajax/hot      403 Forbidden
    ithome.com/rss          500/404（分类路由挂了，主 RSS 还行）
    36kr.com/api            返回 HTML（反爬，用 gateway.36kr.com 替代）


═══════════════════════════════════════
 【三、git 推送踩坑】
═══════════════════════════════════════

  推送标准流程（用 push.ps1 一键跑完）：
    powershell -ExecutionPolicy Bypass -File .\push.ps1
    powershell -ExecutionPolicy Bypass -File .\push.ps1 -Log "commit message"

  ⚠️ 手动步骤（push.ps1 自动化不了的）：
    1. 开 Watt Toolkit → 网络加速 → 勾选 GitHub → 点加速
    2. 首次推送前必须确认 git status 没有敏感文件（api.json 等）

  🔑 关键配置：
    # SSL 绕过（Watt Toolkit 加速时证书问题）
    git config --global http.sslVerify false
    git push -u origin master
    git config --global http.sslVerify true

    # 彻底消除 credential-osxkeychain 警告
    git config --global --unset credential.helper

  🔑 .gitignore 必须包含：
    天气结果/ 新闻结果/ 美食结果/ 山西菜结果/
    weather/api.json      ← 含高德 Key，敏感！
    *_call_state.json     ← 运行时状态
    feeds.json            ← 运行时缓存
    .push-logs/           ← push.ps1 自己的运行日志


═══════════════════════════════════════
 【四、Python / 编码坑】
═══════════════════════════════════════

  1. Windows PowerShell 默认 GBK，打印 emoji 🤣💻🔥 会报 UnicodeEncodeError
     解决：$env:PYTHONIOENCODING="utf-8" 再运行，或脚本里加
     import sys; sys.stdout.reconfigure(encoding='utf-8')

  2. 中文路径在 GBK 终端里显示乱码，但实际读写正常
     别因为显示乱码就以为文件坏了，Python open() 用 utf-8 读写就行

  3. requests.get 的 timeout 参数写 8-10 秒够用了
     太慢的 API 直接判死，别等太久


═══════════════════════════════════════
 【五、天气脚本踩坑】
═══════════════════════════════════════

  1. 高德天气 extensions 参数：base=实况，all=预报
  2. 城市转 adcode 要用高德 district API，不是直接用城市名当 key
  3. Open-Meteo 是完全免费无 Key 的备选，但国内城市名识别不如高德准
  4. weather/api.json 里存了 Key，绝对不能提交到 git


═══════════════════════════════════════
 【六、命令行排查模板】
═══════════════════════════════════════

  测某个 API 活不活：
    python -c "import requests; r=requests.get('URL',timeout=8,headers={'User-Agent':'Mozilla/5.0'}); print(r.status_code, len(r.text), r.text[:200])"

  测 36氪 POST：
    python -c "import requests,json; r=requests.post('https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot', json={'partner_id':'wap','param':{'siteId':1,'platformId':2}}, headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0'}, timeout=10); print(r.status_code, r.json().get('code'))"

  看 git 里到底有啥要推：
    cd f:\TanSuo ; git status --short


═══════════════════════════════════════
 【七、快速命令速查】
═══════════════════════════════════════

  推送：
    cd f:\TanSuo ; powershell -ExecutionPolicy Bypass -File .\push.ps1 -Log "改动说明"

  跑全部脚本（验证结构）：
    cd f:\TanSuo ; $env:PYTHONIOENCODING="utf-8"
    python .\weather\weather.py
    python .\food\food.py
    python .\shanxi_food\shanxi_food.py
    python .\news\news.py
    python .\news\funny_news.py
    python .\news\tech_news.py

  清理运行产物（可选）：
    Remove-Item -Recurse -Force "f:\TanSuo\天气结果","f:\TanSuo\新闻结果","f:\TanSuo\美食结果","f:\TanSuo\山西菜结果"


═══════════════════════════════════════
 【八、Cloudflare D1 REST API 踩坑 (2026-10-25)】
═══════════════════════════════════════

  🚨 核心铁律(三条):

  1. D1 REST API 只有 POST /query 端点,没有 /execute
     单条请求:  body: { sql: "SELECT * FROM items", params: [] }
     批量请求:  body: { batch: [{ sql: "...", params: [...] }, ...] }
     INSERT/UPDATE/DELETE 也走 /query,不需要专门的 execute 端点

  2. 响应格式有新旧两种,必须同时兼容:
     // 新版(D1 实际返回的):result[0].results 直接就是对象数组
     { result: [{ results: [{ id:"life-1", title:"饭馆", ... }, ...], success:true, meta:{...} }] }

     // 旧版(早期 D1 文档示例):result[0].columns + rows(二维数组)
     { result: [{ columns:["id","title",...], rows:[["life-1","饭馆",...],...] }] }

     // d1Query 正确写法(handler.js 和 d1-client.js 都要一样):
     async function d1Query(sql, params = []) {
       const result = await d1Fetch('/query', { sql, params })
       if (!result || !result.length) return []
       const first = result[0]
       if (first.results && Array.isArray(first.results)) return first.results   // 新版
       const { columns, rows } = first                                          // 旧版
       if (columns && rows) return rows.map(row => { ... })
       return []
     }

  3. 认证用 Bearer Token,三个环境变量:
     CLOUDFLARE_ACCOUNT_ID   (32 位 hex)
     CLOUDFLARE_D1_DATABASE_ID  (UUID,连字符格式)
     CLOUDFLARE_API_TOKEN    (cfat_ 开头)

  📁 相关文件:
    tansuo-web/api/handler.js     ← Vercel Edge Functions 用(生产)
    tansuo-web/lib/d1-client.js   ← 通用客户端(本地 d1-list/test-d1 脚本也用)
    这两个文件里的 d1Query / d1Execute / d1Batch 必须保持一致

  🔍 调试技巧:
    - /api/health 端点:真跑 SELECT COUNT(*),返回 itemsInDb / dbQueryError
    - /api/items/raw 端点:绕过 d1Query 解析,直接返回 D1 REST API 原始 JSON
    - 如果 itemsInDb === null 而不是 0,说明 d1Query 解析到了空数组(不是没数据)
    - PowerShell 里查外网接口经常被墙/超时,让用户在浏览器里访问后贴 JSON


═══════════════════════════════════════
 【九、tansuo-web 双仓库推送流程】
═══════════════════════════════════════

  两个独立仓库,每次前端 API 层改动要推两次:

    仓库 1:  D:\前端_页面        →  https://github.com/manongyase/WebPage.git  (main 分支)
    仓库 2:  f:\TanSuo           →  https://github.com/manongyase/TanSuo.git   (master 分支)

  推送流程(已验证):
    1. 改 f:\TanSuo\tansuo-web 下的源码
    2. 把改过的文件复制到 D:\前端_页面\tansuo-web
       Copy-Item "f:\TanSuo\tansuo-web\xxx.js" "D:\前端_页面\tansuo-web\xxx.js" -Force
    3. 先推 WebPage(Vercel 部署源):
       Set-Location "D:\前端_页面"
       git add . ; git commit -m "..."
       git config --global http.sslVerify false
       git push -u origin main
       git config --global http.sslVerify true
    4. 再推 TanSuo:
       Set-Location "f:\TanSuo"
       git add . ; git commit -m "..."
       git config --global http.sslVerify false
       git push -u origin master
       git config --global http.sslVerify true

  ⚠️ 注意:
    - Vercel 自动监听 WebPage 仓库 main 分支,推送后 30~60 秒部署完成
    - vercel.json rewrites 把 /api/* 全部转发给 /api/handler(Edge Function)
    - 本地 dev 用 better-sqlite3(server/db.js),不连 D1


═══════════════════════════════════════
 【十、安全:GitHub Push Protection】
═══════════════════════════════════════

  GitHub 仓库开了 secret-scanning,检测到 token 会拒绝推送:

    ❌ 不能推的文件:
       list-d1.cjs     ← 含硬编码 Cloudflare Account Token
       test-d1.cjs     ← 同上

    ✅ 解决办法:
       1. 本地保留文件(需要用),但加到 .gitignore
       2. git rm --cached list-d1.cjs test-d1.cjs  (从 git 追踪中移除,保留本地)
       3. git commit --amend -m "..."  (如果已经 commit 过,amend 掉)
       4. 推完后建议轮换 token(因为本地历史里有)

    .gitignore 追加:
       list-d1.cjs
       test-d1.cjs
       *.cjs.local


═══════════════════════════════════════
 【十一、WSL 本地开发环境 (关键!)】
═══════════════════════════════════════

  用户实际跑 dev server 的路径是:
    WSL Ubuntu:  /home/front/tansuo-web   ← 独立副本!
    Windows:     f:\TanSuo\tansuo-web      ← AI 改的是这份
    Vercel 部署:  D:\前端_页面\tansuo-web   ← 第三份副本

  三份副本必须同步,否则改了代码本地看不到效果!

  📋 同步流程(每次改完必做):
    # 1. WSL(front 用户,别用 mnys 默认用户,他没权限)
    wsl -d Ubuntu -u front -- bash -c '
      cp /mnt/f/TanSuo/tansuo-web/server/*.js /home/front/tansuo-web/server/
      cp /mnt/f/TanSuo/tansuo-web/src/*.vue /home/front/tansuo-web/src/
      cp /mnt/f/TanSuo/tansuo-web/src/*.css /home/front/tansuo-web/src/
      cp /mnt/f/TanSuo/tansuo-web/src/*.js /home/front/tansuo-web/src/
      cp /mnt/f/TanSuo/tansuo-web/api/handler.js /home/front/tansuo-web/api/   # 可选(本地不用)
    '

    # 2. D 盘(Vercel 部署源)
    Copy-Item "f:\TanSuo\tansuo-web\xxx" "D:\前端_页面\tansuo-web\xxx" -Force

  ⚠️ WSL 权限坑:
    - WSL 默认用户是 mnys(uid 1000),/home/front 属于 front 用户
    - 必须用 wsl -d Ubuntu -u front 执行,否则 Permission denied
    - 或者 sudo cp(但 sudo 可能要密码)

  ⚠️ WSL 目录对比:
    f:\TanSuo\tansuo-web  ──── 有 api/handler.js     ← Vercel Edge 用
    /home/front/tansuo-web ── 没有 api/ 目录!       ← 本地 dev 不需要
    本地 dev 只跑 server/api.js + server/db.js


═══════════════════════════════════════
 【十二、鉴权系统架构 (2026-10-25 上线)】
═══════════════════════════════════════

  🎯 设计原则:
    - 密码**绝对不硬编码在前端代码里**,哪怕是 SHA256 也不行
    - 用户数据存 SQLite(本地 dev) / Cloudflare D1(线上)
    - 密码只存 SHA256 哈希,不存明文
    - 登录凭证用 httpOnly cookie(session),不是 localStorage

  📊 表结构:
    CREATE TABLE users (
      username TEXT PRIMARY KEY,
      password_hash TEXT NOT NULL,     -- SHA256 64 位 hex
      role TEXT NOT NULL DEFAULT 'viewer',  -- 'admin' | 'viewer'
      created_at TEXT DEFAULT (datetime('now'))
    );

  🔑 种子用户(首次启动自动插入,后续启动不重复):
    admin  → SHA256('宇宙之疯牛倜傥')  → role: admin
    张文秀 → SHA256('张文秀')         → role: viewer

  📁 相关文件(本地 dev / 线上 Vercel 各一套):

    本地 SQLite(better-sqlite3):
      server/db.js    → init() 建 users 表,seedUsers() 种子用户,login(password 校验)
      server/api.js   → /api/login POST + /api/me GET + /api/logout POST
                       session 存内存 Map(3 天过期),Set-Cookie tansuo_session=xxx

    线上 D1(Vercel Edge):
      api/handler.js  → ensureUsersTable() 首次建表 + 种子用户
                       /api/login + /api/me + /api/logout
                       Edge 无状态 → cookie 存 base64(payload).HMAC-SHA256 签名
                       hmacSign() / hmacVerify() 用 CLOUDFLARE_API_TOKEN 当密钥

  🔐 密码哈希(两边都用 SHA256,结果一致):
    // Node.js 本地:
    crypto.createHash('sha256').update(pw).digest('hex')

    // Edge Runtime(Vercel):
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(pw))
    Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2,'0')).join('')

  🖥️ 前端 App.vue 鉴权流程:
    onMounted()  → checkAuth() 调 GET /api/me
      ├─ 有 cookie + 有效 → currentUser = { username, role }
      │                    → 自动 initializeFromBackend() + refreshDbBar()
      └─ 无 cookie/过期 → currentUser = null → 显示登录页

    doLogin()    → POST /api/login { username, password }
                   成功: Set-Cookie(浏览器自动存) + initializeFromBackend() + refreshDbBar()
                   失败: ElMessage.error(后端返回的错误)

    doLogout()   → POST /api/logout + 清本地状态

    canEdit      = computed(() => currentUser?.role === 'admin')
                   驱动所有增删改按钮 v-if / disabled

  ❌ 历史踩坑:
    1. 最初把 USERS 数组硬编码在 App.vue(含明文密码),用户一句话就改掉了
       → 教训:任何涉及密码/密钥的数据,绝不能出现在前端 .vue 文件里
    2. onMounted 加了 if (!checkAuth()) return 早退,但登录成功后没调 initializeFromBackend()
       → 侧栏一直显示"后端离线",DB 其实是好的
       → 教训:鉴权系统改动 onMounted 时,登录成功路径必须补跑所有初始化逻辑


═══════════════════════════════════════
 【十三、Vercel 固定域名】
═══════════════════════════════════════

  默认域名格式:  {项目名}-{随机后缀}-{用户名}.vercel.app
  例:            web-page-4olgwz4ln-mnys.vercel.app  ← 随机串看起来像每次部署都变,实际不变

  ✅ 改干净的固定域名:
    1. Vercel Dashboard → 项目 → Settings → General → Project Name
    2. 改成没被别人占用的名字(比如 happymira)
    3. **关键:改名后必须 Redeploy 一次 Production Deployment 才会生效!**
       Vercel Dashboard → Deploys → 最新的 Production 部署 → Redeploy
    4. 新域名: https://happymira.vercel.app

  ⚠️ 注意:
    - 旧的随机域名不会自动消失,还能访问,但以后只用新域名
    - 前端所有 API 路径都是相对路径(/api/login),域名变了不用改代码
    - 如果想彻底固定,Settings → Domains 可以绑自己的域名(需购买 + DNS 配置)


═══════════════════════════════════════
 【十四、Element Plus 图标名坑】
═══════════════════════════════════════

  element-plus/icons-vue 的图标名和直觉可能不一样:

    ❌ Target    → 不存在!靶心图标
    ✅ Aim       → 才是靶心图标(element-plus 官方图标)

  项目当前使用的所有图标(main.js 全局注册):
    Coffee       → 生活 ✓
    Compass      → 探索 ✓
    Briefcase    → 工作 ✓
    MagicStick   → 好奇 ✓(官方图标集里可能没有,但 main.js 全局注册了)
    Aim          → 规划 ✓(已从 Target 修正)

  🚀 快速查图标名: element-plus.org/zh-CN/component/icon
  查不到就试试 WebSearch "element-plus 图标名 xxx"

  main.js 里的全局注册:
    for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
      app.component(key, component)
    }
  所以 modules.js 里 icon 字段写的字符串必须和 @element-plus/icons-vue 里的导出名完全一致


═══════════════════════════════════════
 【十五、tansuo-web 完整文件清单(2026-10-25)】
═══════════════════════════════════════

  tansuo-web/
  ├── api/handler.js                ← Vercel Edge Functions 统一入口
  │    功能:D1 REST API 客户端,所有 /api/* 路由
  │    关键函数:d1Fetch(), d1Query(), d1Execute(), d1Batch()
  │            hashPassword(), ensureUsersTable()
  │            signSession(), verifySession(), hmacSign(), hmacVerify()
  │    路由:/api/health, /api/items, /api/items/raw, /api/items/clear
  │         /api/memos, /api/memos/clear, /api/migrate, /api/import-append
  │         /api/login, /api/me, /api/logout
  │
  ├── lib/d1-client.js               ← D1 REST API 客户端(通用)
  │    和 handler.js 里的 d1Query 保持一致(新旧格式都兼容)
  │
  ├── server/db.js                   ← 本地 SQLite 层(better-sqlite3)
  │    表:items, memos, users
  │    导出:getDb(), upsertItem(s), deleteItem(), listItems()
  │            upsertMemo(s), deleteMemo(), listMemos()
  │            login(username, password), getUser(username)
  │    首次启动自动建表 + 种子用户
  │
  ├── server/api.js                  ← Vite dev server 里挂的 REST 接口
  │    和 handler.js 功能镜像,但用 SQLite + 内存 session(Map)
  │    鉴权辅助函数:makeSession(), checkSession(), requireAdmin()
  │
  ├── src/App.vue                    ← 主组件(1070+ 行)
  │    鉴权模块:USERS 删除,改调 /api/login + /api/me + cookie session
  │    权限控制:canEdit 驱动所有增删改按钮 v-if
  │
  ├── src/api.js                     ← 前端 fetch 封装
  ├── src/modules.js                 ← 五个模块配置(life/explore/curiosity/work/plan)
  ├── src/main.js                    ← Vue + Element Plus + 全局图标注册
  ├── src/style.css                  ← 全局样式(登录页样式也在这里)
  ├── vite.config.js                 ← 本地 5173,挂 server/api.js
  └── vercel.json                    ← rewrites /api/* → /api/handler

═══════════════════════════════════════
 【十六、2026-10-25 会话实战记录 · 移动端弹窗修复】
═══════════════════════════════════════

  日期:2026-10-25
  目标:修复移动端按钮点击无弹窗 + 桌面端备忘按钮缺失 + safeTrigger/touchend 清理
  最终状态:✅ 全部修复,双仓库推送
  提交: TanSuo 9976c6f, WebPage 56e2ae3

  ┌─────────────────────────────────────────────┐
  │  一、原始 Bug 根因                          │
  └─────────────────────────────────────────────┘

  Bug #1: 移动端所有"新增/编辑/备忘/调试"按钮点了没反应
    → 根因:<el-dialog>/<el-drawer>写在 <div v-else class="desktop-root"> 内部
             移动端走 v-if 分支,desktop-root 不渲染
             → dialog 组件根本不在 DOM 里,openDialog() 设 dialogVisible=true 没用
             → browser_evaluate 确认:dialogInHTML=false,drawerInHTML=false

  Bug #2: 桌面端没有备忘按钮
    → 根因:mobile-app 的 topbar 有备忘按钮(line 778),desktop-root 的 topbar 没有
             desktop-root head-right 只有:DB标签 + 用户头像 + 登出
             移动端有:DB标签 + Bell备忘 + 用户头像 + 登出

  Bug #3: 所有按钮用 safeTrigger + @touchend.prevent 双绑定
    → safeTrigger(fn) 只做 300ms 防抖,其实没必要
    → @touchend.prevent 在某些移动浏览器里会吞掉 click 事件
    → 代码里到处都是:@click="safeTrigger(openDialog)" @touchend.prevent="safeTrigger(openDialog)"

  ┌─────────────────────────────────────────────┐
  │  二、我踩过的坑(必须记住)                    │
  └─────────────────────────────────────────────┘

  坑 #1: wsl -e bash -c 找不到 node
    现象:node command not found / bash: line 1: node: command not found
    根因:wsl -e bash -c 启动的是**非交互 shell**,不加载 .bashrc/.nvm
    用户纠正:"wsl里面有node啊,front@DESKTOP-AUTD1J5:~/scripts$ node → v24.22.1"
    正确写法:
      ✅ wsl -u front -e bash -ic 'which node'
      ✅ wsl -u root -e bash -c 'cd /mnt/f/TanSuo/tansuo-web && /home/front/.nvm/versions/node/v24.22.1/bin/node node_modules/vite/bin/vite.js'
    经验:wsl 里跑 npm/vite 必须显式指定 nvm 里的 node 绝对路径

  坑 #2: WSL 里 npm install 报 EPERM (Operation was rejected)
    现象:npm install → EPERM: operation not permitted, chmod ...babel-parser...
    根因:/mnt/f/ 挂载盘上 WSL 用户权限不够(Windows 侧 owner,Linux 侧不认)
    解决:用 root 用户跑 npm install
      wsl -u root -e bash -c 'cd /mnt/f/TanSuo/tansuo-web && npm install'
    注意:root 装完 node_modules 里的脚本有 CRLF 问题(Windows 挂载特性)

  坑 #3: node_modules/.bin/vite 有 CRLF,/usr/bin/env: 'bash\r': No such file
    现象:vite.js 脚本首行是 #!/usr/bin/env node\r,Linux 不认
    解决:直接用绝对路径 node 跳过 shebang
      ✅ /home/front/.nvm/versions/node/v24.22.1/bin/node node_modules/vite/bin/vite.js --host 0.0.0.0
    备选:find node_modules/.bin -type f -exec sed -i 's/\r$//' {} +

  坑 #4: PowerShell Set-Content 把文件搞成一行了!
    现象:想删除文件中间几行,用 PowerShell 数组切片 + Set-Content → 整个文件变成一行
    根因:Get-Content 读成数组但 Set-Content 默认编码/换行符处理有问题
    解决:立刻 git checkout -- tansuo-web/src/App.vue 恢复
    铁律:改 Vue 模板文件**只用 Edit 工具(old_string/new_string)**,别用 PowerShell 批量操作

  坑 #5: Vue 编译错误 "v-else has no adjacent v-if"
    第一次:我在 v-if 和 v-else 之间加了 dialog 块 → Vue 要求 v-if/v-else 必须是兄弟节点
    第二次:我删掉 dialog 块后,中间留了空行和注释 → **空行也会导致!**
    铁律:v-if 闭合 `</div>` 和 v-else 开启 `<div v-else>` 之间**不能有任何东西**
      ✅ </div>\n  <div v-else>
      ❌ </div>\n\n  <div v-else>  (空行)
      ❌ </div>\n  <!-- 注释 -->\n  <div v-else>  (注释)

  坑 #6: safeTrigger(() => func()) 正则没匹配上
    现象:PowerShell regex `safeTrigger\(\(\)\s*=>\s*([^)]+)\)` 没匹配嵌套括号
    根因:openEditDialog(item) 里有括号,regex 只匹配到第一个 `)`
    解决:用更宽松的 `safeTrigger\(\(\)\s*=>\s*([a-zA-Z_][a-zA-Z0-9_]*\([^)]*\))\)`

  坑 #7: 想搞 Vant4 + Element Plus 双框架
    我建议给移动端单独上 Vant4,被 Advisor 拦了
    Advisor 说得对:这是杀鸡用牛刀,问题出在模板结构不是 UI 框架
    铁律:遇到 bug 先定位根因,不要急着换框架/加新依赖

  坑 #8: 忘了"不影响原桌面功能"
    用户提醒:"老铁,要不咱们分成两套框架,PC用这套可以,但是安卓用 Vant4"
    背后隐含:之前的改动可能影响了桌面端!
    铁律:任何改动前先明确范围——只动什么,不动什么

  ┌─────────────────────────────────────────────┐
  │  三、正确修复步骤(下次照抄)                  │
  └─────────────────────────────────────────────┘

  Step 1: 确认原始状态
    cd f:\TanSuo; git --no-pager log --oneline -3

  Step 2: 跑 dev server
    wsl -u root -e bash -c 'cd /mnt/f/TanSuo/tansuo-web && /home/front/.nvm/versions/node/v24.22.1/bin/node node_modules/vite/bin/vite.js --host 0.0.0.0'

  Step 3: 浏览器测试
    - browser_evaluate 查 dialog 是否在 DOM 里
    - browser_snapshot 拿 ref → browser_click 点按钮

  Step 4: 模板修复(两个 Edit)
    Edit A: mobile-app </div> 后直接接 <div v-else>desktop-root
            (中间零空行零注释)
    Edit B: 所有 el-dialog/el-drawer/debug-fab 从 desktop-root 内部移到外面

  Step 5: 业务修复 -- 桌面端补备忘按钮
    在 desktop-root head-right 的 DB 标签后加:
      <el-button :icon="Bell" @click="openMemoDrawer" plain size="small" title="备忘录">备忘</el-button>

  Step 6: 清理 -- 全量删除 safeTrigger + @touchend.prevent
    - safeTrigger(fn) + @touchend.prevent → 纯 @click="fn"
    - safeTrigger(() => func()) + @touchend.prevent → 纯 @click="func()"
    - safeTrigger(() => func(item)) + @touchend.prevent → 纯 @click="() => func(item)"
    - 删除 safeTrigger 函数和 _lastTrigger 变量

  Step 7: 浏览器验证
    - 新增条目 → 弹窗 "新增 · [模块名]"
    - 编辑 → 弹窗 "编辑 · [模块名]"
    - 备忘 → el-drawer slide 出来
    - debug-fab → 调试助手弹窗

  Step 8: 双仓库同步
    cd f:\TanSuo
    git add tansuo-web/src/App.vue; git commit -m "fix: 描述"
    git -c http.sslVerify=false push origin master
    Copy-Item "f:\TanSuo\tansuo-web\src\App.vue" "D:\前端_页面\tansuo-web\src\App.vue" -Force
    cd "D:\前端_页面"
    git add tansuo-web/src/App.vue; git commit -m "fix: 描述"
    git -c http.sslVerify=false push origin main

  ┌─────────────────────────────────────────────┐
  │  四、关键思想沉淀                            │
  └─────────────────────────────────────────────┘

  思想 #1: 模板条件渲染中的"作用域陷阱"
    Vue 的 v-if/v-else-if/v-else 是排他渲染,只渲染一个分支
    但初学者容易把"全局组件"(dialog/drawer/overlay)放进某个分支里
    → 应该放在 v-if/v-else 的父级 template 里,不受条件分支影响
    → Element Plus 的 dialog 本身就是 teleport 到 body 的,放哪个 div 里都一样渲染

  思想 #2: v-if/v-else 的相邻约束
    Vue 编译器要求 v-if 和 v-else 是**直接兄弟节点**
    中间不能有:空行、HTML注释、任何其他元素
    这不是警告是编译错误
    解决:把条件分支尽量包裹在一个容器里,全局组件放容器外

  思想 #3: safeTrigger/@touchend.prevent 是反模式
    当初为了"移动端 300ms 延迟"加的,但实际上:
    - 现代浏览器已无 300ms 延迟(除了老旧 Android WebView)
    - @touchend.prevent 会吞掉 click,导致按钮点不动
    - 双重事件绑定在某些设备上触发两次
    结论:纯 @click = fn() 就够了

  思想 #4: PowerShell 不适合改 Vue 模板
    PowerShell 的编码/换行符/Set-Content 都会搞坏文件
    改模板文件:只用 Edit 工具(old_string → new_string)
    改脚本逻辑:Shell + .NET 函数(UTF8 + 不添加 BOM)

  思想 #5: 调试的最快路径
    1. 跑 dev server
    2. curl http://localhost:5173/src/App.vue | Select-String "Pre-transform" → 确认编译通过
    3. 浏览器 evaluate 查 DOM 状态
    4. 对比代码:代码里有什么 vs DOM 里有什么
    5. 差在哪?→ 模板结构!

  ┌─────────────────────────────────────────────┐
  │  五、关键命令速查                            │
  └─────────────────────────────────────────────┘

  # 启动 dev server(WSL)
  wsl -u root -e bash -c 'cd /mnt/f/TanSuo/tansuo-web && /home/front/.nvm/versions/node/v24.22.1/bin/node node_modules/vite/bin/vite.js --host 0.0.0.0'

  # 验证编译
  curl.exe -s "http://localhost:5173/src/App.vue" | Select-String "Pre-transform"

  # 查看端口占用
  netstat -ano | findstr ":5173" | findstr LISTENING

  # 杀掉 vite
  wsl -u root -e bash -c 'pkill -f vite'

  # 双仓库 git push(SSL 有问题时)
  git -c http.sslVerify=false push origin master

  ┌─────────────────────────────────────────────┐
  │  六、会话时间线                              │
  └─────────────────────────────────────────────┘

  15:00  会话开始 → 用户上传截图,反馈移动端按钮点不动
  15:05  确认 dev server 跑着 → 浏览器模拟移动端 → 弹窗不出
  15:10  发现根因:dialog 在 v-else 分支里,mobile 分支不渲染
  15:15  第一次修复:Edit 把 dialog 块移到 wrapper 外 → Vue 编译错误
  15:20  PowerShell Set-Content 把文件搞成一行 → git checkout 恢复
  15:25  第二次修复:两步 Edit 成功 → 弹窗验证通过
  15:30  同步 WebPage 仓库 → TanSuo 89a7f5a → WebPage 83dc3cf
  15:35  用户反馈桌面端三个问题(备忘按钮/左下角偏移/debug-fab)
  15:40  发现 desktop-root 根本没备忘按钮 + safeTrigger 还在(git restore 恢复了旧代码!)
  15:45  批量清理 safeTrigger + 补备忘按钮 → 编译错误又来了(空行在 v-if/v-else 之间)
  15:50  删掉 v-if/v-else 之间的空行 → 零编译错误
  15:55  浏览器全量验证通过
  16:00  TanSuo 9976c6f → WebPage 56e2ae3
  16:05  写本总结

========================================═══════════════════════════════════════
 【十七、2026-10-26 会话实战记录 · 重构 + 绘制修复】
═══════════════════════════════════════

  日期:2026-10-26
  目标:删 debug-fab + handler.js 拆模块 + dashboard/侧边栏按钮绘制修复
  最终状态:✅ 全部修复,双仓库推送
  提交链:e71ad7e → b032863 → 263c851 → 28b4624 → 0027bd0 → 9de5492 → ecaad16 → 8c26909

┌─────────────────────────────────────────────┐
│ 一、今日 5 大绘制/布局 Bug 的完整错误链     │
└─────────────────────────────────────────────┘

  Bug 1:handler.js 579 行臃肿
  ── 根因:全堆在一个文件里,所有 D1 调用/Auth/Stores 混在一起
  修复:拆成 api/lib/ 4 个模块
       handler.js 300 行 ← 薄路由,只做参数校验+路由分发
       api/lib/d1.js 114 行 ← D1 REST 客户端(query + batch)
       api/lib/auth.js  88 行 ← HMAC cookie session + verifySession
       api/lib/stores.js 98 行 ← Items/Memos CRUD 封装

  Bug 2:el-progress--dashboard 绘制偏差
  ── 根因:CSS 只覆盖了 .el-progress--circle,没覆盖 --dashboard
       Element Plus dashboard 模式默认 width/height/定位和 circle 不同
  修复:style.css 加一行
       .head-stats .el-progress--dashboard { width:64px; height:64px; margin:0 auto; }

  Bug 3:侧边栏检查/同步按钮不均衡(水平排列)
  ── 根因链(5 层):
    Layer 1:emoji 🔍💾 系统字体渲染,大小/基线和平台有关
    Layer 2:按钮类型不一致 — 一个 type="primary" 实心,一个 link type="success" 虚
    Layer 3:水平排列时两个按钮宽度由内容决定,emoji 本身宽度不一样
    Layer 4:同步按钮有 margin-left:12px(Element Plus .el-button--success 默认!)
    Layer 5:父容器 .foot-actions 只有 gap:6px 没处理 width/对齐
  修复链:
    L1:emoji → Element Plus :icon="Search" / :icon="RefreshRight"
    L2:统一 type,都用实心按钮
    L3:用户改需求 → 垂直排列(检查在上,同步在下)
    L4:margin:0 !important 清 Element Plus 默认 margin
    L5:width:100% + justify-content:center + gap:8px(防误触)

  Bug 4:Vite 预构建缓存不更新(反复出现!)
  ── 根因链:
    WSL 里跑 vite → Windows 侧 edit 文件 → WSL 进程能实时读到新文件 ✓
    但 vite 的预构建缓存(node_modules/.vite)可能还存着旧代码
    特别是 import 新图标名(RefreshRight)时,预构建产物里没有
    → HMR 更新了 App.vue 模板,但 icons-vue 的预构建产物还是旧的
    → :icon="RefreshRight" 在运行时变成 undefined,模板里没有 SVG
  症状:浏览器里看到旧代码,但本地文件是新的
  根因识别:curl http://localhost:5173/src/App.vue 看 vite serve 的实际代码
          如果 import 行里没有 RefreshRight,就是预构建缓存炸了
  修复:
    pkill -9 -f vite 2>/dev/null
    rm -rf node_modules/.vite
    重新启动 vite
    
  ⚠️ 关键教训:vite --force 只重优化依赖,不会删掉整个 .vite 目录里的 CSS 缓存
     如果是 style.css 的改动不生效,必须 rm -rf node_modules/.vite 再重启
     CSS 通过 __vite__css 字符串注入,缓存比 JS 模块更顽固

  Bug 5:WSL 多 vite 进程占端口
  ── 根因:之前 kill 没杀干净,两个 vite 进程同时监听 5173
       一个是 root 起的 --force,一个是 front 起的
       curl 能返回但内容是旧进程的
  修复:kill -9 两个进程,确认 ss -tlnp | grep 5173 为空再重启
  教训:多进程时要看 ps aux | grep vite,不要只看端口(端口只能看到一个)

┌─────────────────────────────────────────────┐
│ 二、Element Plus 按钮的隐藏默认值(巨坑)    │
└─────────────────────────────────────────────┘

  今天反复踩了 Element Plus .el-button 的坑,总结:

  1. .el-button--success 默认有 margin-left:12px
     (可能是为了和前面的按钮组合时的间距)
     → 必须用 margin:0 !important 清掉

  2. link 按钮和实心按钮高度不一样
     link 没有 border/padding 像链接,height 由 line-height 决定
     实心按钮 height 由 --el-button-height 变量决定(默认 32px)
     → 同组按钮必须统一 type 才能对齐

  3. .el-button 的 :icon 属性要求图标名已 import 且注册
     没 import 的图标在模板里会被当作 undefined
     → 浏览器里看不到 SVG,只剩文字
     → 检查 curl vite serve 的代码,看 import 行有没有

  4. Element Plus 组件的 CSS 变量优先级很高
     想用 :deep() 覆盖可能没用,得直接写具体类名
     → 比如 .head-stats .el-progress--dashboard { width:64px !important; }
     → !important 在这里是合理的,因为是精确作用域覆盖

┌─────────────────────────────────────────────┐
│ 三、Vite 缓存清除 SOP(照抄就能用)          │
└─────────────────────────────────────────────┘

  场景 1:改了 import 语句(加/删 icon、加新 import)→ 预构建缓存炸
  场景 2:改了 CSS 但浏览器里不生效 → HMR 没传播到 style injector
  场景 3:看到旧代码,刷新没用 → 多进程或旧缓存

  SOP:
    # 1. 杀所有 vite(注意 WSL 里可能有多个)
    ps aux | grep vite | grep -v grep | awk '{print $2}' | xargs kill -9

    # 2. 清预构建缓存(关键!)
    rm -rf node_modules/.vite

    # 3. 确认端口空了
    ss -tlnp | grep 5173 || echo "port free"

    # 4. 重启 vite
    npm run dev  # 或 node node_modules/vite/bin/vite.js --host 0.0.0.0

    # 5. 验证
    curl http://localhost:5173/src/App.vue | grep "RefreshRight"
    # 或浏览器 DevTools → Network → Disable cache + Ctrl+Shift+R

  ⚠️ Windows 侧杀进程:
     taskkill /F /PID 3148
     或 Get-Process node | Stop-Process -Force
     注意:WSL 里的进程在 Windows 侧可能看不到,
          优先用 wsl -u root -e bash -c 'pkill -9 -f vite'

┌─────────────────────────────────────────────┐
│ 四、今日 8 个 Commit 汇总                   │
└─────────────────────────────────────────────┘

  e71ad7e  fix: 删 debug-fab + console 劫持(-102 行)
  b032863  refactor: handler.js 拆 api/lib/{d1,auth,stores}(579→300 行)
  263c851  fix: 闭包 bug(method 显式传参) + COMPONENTS.md
  28b4624  fix: dashboard CSS 覆盖(.el-progress--dashboard width/height)
  0027bd0  fix: 按钮 emoji→Element Plus 图标 + 统一 type
  9de5492  fix: 侧边栏按钮垂直排列(flex-direction:column + width:100%)
  ecaad16  fix: 同步按钮 margin-left:12px→0(!important)
  8c26909  fix: 按钮间距 4px→8px 防误触

┌─────────────────────────────────────────────┐
│ 五、App.vue 要不要拆?→ 现在不拆             │
└─────────────────────────────────────────────┘

  当前 App.vue ≈ 1086 行(script ~300 行,template ~700,style ~26)
  handler.js 已拆到 300 行 ✅
  api/lib/* 各 88-114 行 ✅

  为什么现在不拆 App.vue:
  1. script 部分 300 行在临界点,再拆收益递减
  2. template 里所有 dialog/drawer 的 v-model 依赖顶层 ref
     拆成组件后需要 props + emits 通信链,至少 15 个 props 要传
  3. v-if/v-else 相邻约束是地雷(上次就是这个结构 bug)
  4. 任何 prop 传错类型会白屏

  什么时候该拆:
  - script 超过 400 行
  - 新增第 6 个模块
  - 加 vue-router 时(Layout 自然变成独立组件)

  已准备好 COMPONENTS.md 设计文档,未来拆的时候直接用。

┌─────────────────────────────────────────────┐
│ 六、核心思想沉淀(可迁移到其他项目)          │
└─────────────────────────────────────────────┘

  1. 「不要假设第三方组件的默认样式」
     Element Plus 的按钮有隐藏 margin,Progress 有隐藏尺寸
     → 先查 getComputedStyle 再决定怎么覆盖
     → 用精确选择器 + !important 作用域覆盖比全局 reset 安全

  2. 「垂直比水平更容易对齐」
     两个按钮水平排列时宽度受内容影响(图标宽度、文字长度)
     垂直排列时 width:100% 强制等宽,margin:0 强制对齐
     → 移动端按钮组优先考虑垂直排列

  3. 「curl vite serve 的代码判断缓存」
     浏览器 DevTools 可能显示旧代码(Service Worker 缓存)
     curl http://localhost:5173/src/App.vue | grep "关键字" 最准
     看到新内容 = 缓存问题,看到旧内容 = vite 没重启

  4. 「拆模块先看调用关系图」
     handler.js 里 auth 和 stores 是独立的,可以拆
     d1 是底层工具,auth/stores 都依赖它,所以 d1 放最前面
     → 依赖方向:d1 ← auth, d1 ← stores ← handler

  5. 「先定位根因再改,不要试错」
     侧边栏按钮不均衡,我先后改了 emoji、改了 type、改了排列方向
     最后用 getComputedStyle 查到 margin-left:12px 才是真根因
     → 下次看到对齐问题,先跑 getComputedStyle 看 4 个方向:
       margin/padding/width/height

  6. 「两个仓库推送的顺序」
     TanSuo 是主仓库(f:\TanSuo),WebPage 是 Vercel 部署仓库
     每次改完:先 push TanSuo → Copy-Item 同步 → push WebPage
     WebPage 绑的 Vercel 自动部署,所以那边是最终验证

┌─────────────────────────────────────────────┐
│ 七、时间线                                   │
└─────────────────────────────────────────────┘

  上午:
  - 09:30 用户反馈 3 问题(debug-fab 没用、handler.js 臃肿、dashboard 偏差)
  - 10:00 删 debug-fab(-102 行)
  - 10:30 handler.js 拆 api/lib/4 模块(踩闭包 bug)
  - 11:00 闭包 bug 修复 + COMPONENTS.md 写好
  - 11:30 同步 WebPage → Vercel 部署

  下午:
  - 14:00 用户反馈绘制偏差还在(截图确认)
  - 14:30 dashboard CSS 覆盖 style.css +1 行
  - 15:00 Vite 缓存炸了 → kill + rm -rf .vite + 重启
  - 15:30 验证 dashboard 渲染正常 → commit + push

  傍晚:
  - 16:00 用户反馈侧边栏按钮"根本不均衡对称"
  - 16:30 emoji→图标 + 统一 type → 验证对齐
  - 17:00 用户说"还是偏右" → getComputedStyle 查到 margin-left:12px
  - 17:30 margin:0 !important + width:100% → 完美对齐 left 差=0
  - 18:00 用户说"间距还是有,防误触" → gap 4→8px
  - 18:30 全部 push → 写本总结

========================================

═══════════════════════════════════════
 【十八、2026-10-26 晚 会话 · 移动端按钮 + 暗黑模式】
═══════════════════════════════════════

  日期:2026-10-26 晚
  目标:移动端加检查/同步按钮 + VSCode 风格明暗切换
  最终状态:✅ 全部完成,双仓库推送
  提交链:512037f → 5644651

┌─────────────────────────────────────────────┐
│ 一、移动端检查/同步按钮(最小侵入)          │
└─────────────────────────────────────────────┘

  问题:侧边栏 foot-actions 只在 desktop-root 里有(v-else 分支)
       移动端走 v-if="isMobile" 分支,按钮根本没渲染
  方案:移动端 head-right 区域加 circle icon-only 按钮
  位置:head-right,DB 标签之后,topbar-user 之前
  好处:不重排移动端布局,复用已有 toggleTheme 的模式

  HTML(移动端 L725 区域):
    <el-tooltip content="检查数据完整性" placement="bottom">
      <el-button size="small" circle :icon="Search"
                 :loading="checkingDb" @click="checkDbIntegrity" />
    </el-tooltip>
    <el-tooltip content="手动同步到 DB" placement="bottom" v-if="canEdit">
      <el-button size="small" circle type="success" :icon="RefreshRight"
                 :loading="syncingDb" @click="manualSyncToDb" />
    </el-tooltip>

  两端按钮对比:
    移动端 head-right: [DB在线] [🔍] [💾] [备忘] [🌙] [头像]
    桌面端 head-right: [DB·在线] [备忘] [🌙] [头像]
    桌面端额外在 sidebar-foot 里有垂直排列的[检查/同步]

┌─────────────────────────────────────────────┐
│ 二、明暗切换实现(Element Plus 内置方案)    │
└─────────────────────────────────────────────┘

  核心思路:html.dark 类名 + Element Plus 暗黑 CSS + 自定义变量覆盖

  改动 3 个文件:
  1. main.js 加 1 行:
     import 'element-plus/theme-chalk/dark/css-vars.css'
  2. App.vue script 加 ~15 行:
     const THEME_KEY = 'tansuo_theme'
     const isDark = ref(localStorage.getItem(THEME_KEY) === 'dark')
     function applyTheme() {
       if (isDark.value) document.documentElement.classList.add('dark')
       else document.documentElement.classList.remove('dark')
     }
     function toggleTheme() {
       isDark.value = !isDark.value
       localStorage.setItem(THEME_KEY, isDark.value ? 'dark' : 'light')
       applyTheme()
     }
     applyTheme()
     watch(isDark, applyTheme)
  3. App.vue template 加 2 处按钮(mobile + desktop 各一个)
     <el-tooltip :content="isDark ? '切到亮色' : '切到暗色'" placement="bottom">
       <el-button size="small" circle
                  :icon="isDark ? Sunny : Moon" @click="toggleTheme" />
     </el-tooltip>
  4. style.css 加 ~40 行 html.dark 覆盖:
     html.dark { --bg:#1a1c24; --ink:#e4e6f0; --muted:#8b91a3; --line:#2c3040 }
     html.dark body/topbar/hero/card/memo-card/drawer/user ...

  Element Plus 暗黑模式工作原理:
    element-plus/theme-chalk/dark/css-vars.css 定义了一套
    html.dark 下的 --el-color-* CSS 变量覆盖
    所有 el-button/el-card/el-dialog/el-table 等组件
    自动读取暗色变量,无需逐个组件写 class
    → 自定义组件(hero/item-card/sidebar)需要自己写 html.dark 覆盖

  验证结果(browser_evaluate):
    Init dark: false bg="rgb(244, 246, 251)"  ✅ 亮色
    After click: CLICKED                       ✅ 触发切换
    Dark mode: true bg="rgb(26, 28, 36)"       ✅ 暗色生效
    Back light: false                          ✅ 可切回亮

┌─────────────────────────────────────────────┐
│ 三、踩过的坑                                │
└─────────────────────────────────────────────┘

  坑 1:移动端 v-if/v-else 分支里的组件不共享
  ── desktop-root 的 sidebar-foot 按钮移动端看不到
     因为移动端渲染的是 mobile-app 分支,完全独立的模板
  教训:改任何功能先确认它在两个模板里各有一份

  坑 2:Element Plus 暗色模式只覆盖 --el-color-*
  ── 自定义 CSS 变量(--bg/--ink/--muted/--line)需要手动覆盖
     否则 body 背景还是亮色,el-button 已经变暗色 → 视觉断裂
  教训:自定义变量 + 组件内联颜色都要在 html.dark 下覆盖

  坑 3:isDark ref 初始化读 localStorage 的时机
  ── localStorage.getItem 是同步的,可以在 ref() 初始化里直接调
     不需要 onMounted 再读
  教训:能用同步 API 初始化就不要 defer 到 mounted

  坑 4:主题按钮位置——两端不一样但各自合理
  ── 移动端放 head-right(topbar-user 前)
     桌面端也放 head-right(备忘按钮后,topbar-user 前)
     两端 head-right 结构不一样(桌面没有检查/同步 circle 按钮)
     所以主题按钮不能放同一个位置,各自手动加
  教训:v-if/v-else 两边的模板结构不同,加按钮要各加各的

┌─────────────────────────────────────────────┐
│ 四、核心思想                                │
└─────────────────────────────────────────────┘

  1. 「Element Plus 暗色 = html.dark + 暗黑 CSS」
     记住:main.js 加 import,App.vue 切类名,就能让 90% 的
     Element Plus 组件自动变色。剩下的自定义组件用 html.dark
     覆盖自己的 CSS 变量就行。

  2. 「两端按钮位置不同但功能等价」
     移动端 head-right 紧凑排列 circle icon-only 按钮
     桌面端 sidebar-foot 有独立区域放垂直按钮
     → 不强制两端一样,追求各自最优体验

  3. 「最小侵入原则」
     加检查/同步按钮时我只加了 7 行 template,没改布局没改 CSS
     → 如果能在现有容器里塞下,就别重排整个区域

  4. 「Sunny/Moon 图标名」
     Element Plus icons-vue 包里有 Sunny/Moon 两个图标
     切主题时根据 isDark 动态切换:isDark ? Sunny : Moon
     → 保持视觉语义正确(暗色模式显示太阳,提示"点我切亮")

┌─────────────────────────────────────────────┐
│ 五、时间线                                  │
└─────────────────────────────────────────────┘

  20:00 用户反馈"手机上检查/同步按钮没了"
  20:10 查看 mobile-app 模板 → 确认没有 foot-actions
  20:15 在 head-right 加 circle icon-only 按钮
  20:20 vite 缓存炸了 → kill + rm -rf .vite + 重启
  20:30 验证按钮渲染正常 → 功能一致
  20:40 commit + 双仓库推(WebPage 512037f)
  20:50 用户说"加白天黑夜切换,VSCode 风格"
  20:55 main.js 加 dark/css-vars.css + App.vue 加 isDark/toggleTheme
  21:00 两端 head-right 各加主题按钮 + style.css 加 html.dark 覆盖
  21:10 启动 vite → 验证三状态(亮→暗→亮)全通
  21:20 commit + 双仓库推(WebPage 5644651)
  21:30 写本总结

========================================
