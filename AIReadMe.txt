========================================
  TanSuo 项目 · AI 踩坑经验手册
  生成: 2026-10-01
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
    ├── push.ps1          (推送脚本)
    ├── 推送文档.txt       (推送操作手册)
    ├── AIReadMe.txt       (本文件)
    ├── 天气结果/          (运行产物，gitignore)
    ├── 新闻结果/          (运行产物，gitignore)
    ├── 美食结果/          (运行产物，gitignore)
    ├── 山西菜结果/        (运行产物，gitignore)
    └── 豆瓣榜单结果/      (运行产物，gitignore)


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

========================================