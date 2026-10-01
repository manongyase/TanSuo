import os
import json
import requests
from datetime import datetime


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )
}

ZHIHU_HOT_URL = "https://api.zhihu.com/topstory/hot-list"
KR_HOT_URL = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"
HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

TECH_KEYWORDS = [
    "AI", "人工智能", "大模型", "机器学习", "深度学习", "算法",
    "编程", "代码", "程序员", "开发", "框架", "后端", "前端",
    "芯片", "半导体", "GPU", "CPU", "算力", "服务器", "云",
    "科技", "互联网", "科技公司", "大厂", "开源",
    "区块链", "Web3", "元宇宙", "VR", "AR", "量子",
    "安卓", "iOS", "苹果", "华为", "小米", "特斯拉",
    "机器人", "自动驾驶", "无人机", "卫星", "航天",
    "网络安全", "黑客", "漏洞",
]


def fetch_zhihu_hot(limit: int = 50) -> list:
    resp = requests.get(ZHIHU_HOT_URL, params={"limit": limit}, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    items = []
    for card in resp.json().get("data", []):
        t = card.get("target", {})
        items.append({
            "title": t.get("title", ""),
            "url": t.get("url", ""),
            "excerpt": t.get("excerpt", "") or "",
            "heat": card.get("detail_text", ""),
            "answer_count": t.get("answer_count", 0),
        })
    return items


def _tech_score(title: str, excerpt: str) -> int:
    hay = (title + " " + excerpt).lower()
    return sum(2 for kw in TECH_KEYWORDS if kw.lower() in hay)


def pick_tech(items: list, max_count: int = 10) -> list:
    scored = [(s, it) for s, it in ((_tech_score(i["title"], i["excerpt"]), i) for i in items) if s > 0]
    scored.sort(key=lambda x: -x[0])
    picks = [it for _, it in scored[:max_count]]
    if len(picks) >= max_count:
        return picks
    seen = {p["title"] for p in picks}
    for it in items:
        if it["title"] in seen:
            continue
        picks.append(it)
        if len(picks) >= max_count:
            break
    return picks


def fetch_36kr_hot(limit: int = 15) -> list:
    resp = requests.post(
        KR_HOT_URL,
        json={"partner_id": "wap", "param": {"siteId": 1, "platformId": 2}},
        headers={**HEADERS, "Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    items = []
    for it in resp.json().get("data", {}).get("hotRankList", [])[:limit]:
        tm = it.get("templateMaterial", {})
        item_id = tm.get("itemId", "")
        items.append({
            "title": tm.get("widgetTitle", ""),
            "url": f"https://36kr.com/p/{item_id}" if item_id else "",
            "author": tm.get("authorName", ""),
            "pub_time": tm.get("publishTime", 0),
            "desc": tm.get("widgetContent", "") or "",
        })
    return items


def fetch_hn_top(limit: int = 10) -> list:
    resp = requests.get(HN_TOP_URL, timeout=10)
    resp.raise_for_status()
    ids = resp.json()[:limit]
    items = []
    for hid in ids:
        try:
            r = requests.get(HN_ITEM_URL.format(hid), timeout=8)
            r.raise_for_status()
            d = r.json()
            items.append({
                "title": d.get("title", ""),
                "url": d.get("url", f"https://news.ycombinator.com/item?id={hid}"),
                "hn_url": f"https://news.ycombinator.com/item?id={hid}",
                "score": d.get("score", 0),
                "comments": d.get("descendants", 0),
                "by": d.get("by", ""),
            })
        except Exception:
            continue
    return items


def build_markdown(kr_items: list, zhihu_tech: list, hn_items: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 💻 科技新闻速览",
        "",
        f"> 更新时间：{now}",
        "",
    ]

    lines.append("## 🔥 36氪·热门科技/创投")
    lines.append("")
    if kr_items:
        for i, it in enumerate(kr_items, 1):
            lines.append(f"**{i}. [{it['title']}]({it['url']})**")
            meta = []
            if it.get("author"):
                meta.append(f"✍️ {it['author']}")
            if meta:
                lines.append(f"   {' · '.join(meta)}")
            if it.get("desc"):
                d = it["desc"].strip().replace("\n", " ")
                if len(d) > 150:
                    d = d[:150] + "..."
                lines.append(f"   > {d}")
            lines.append("")
    else:
        lines.append("_36氪 抓不到_")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 🧠 知乎热榜·科技向")
    lines.append("")
    if zhihu_tech:
        for i, it in enumerate(zhihu_tech, 1):
            lines.append(f"**{i}. [{it['title']}]({it['url']})**")
            meta = []
            if it.get("heat"):
                meta.append(f"🔥 {it['heat']}")
            if it.get("answer_count"):
                meta.append(f"💬 {it['answer_count']} 回答")
            if meta:
                lines.append(f"   {' · '.join(meta)}")
            exc = it.get("excerpt", "").strip().replace("\n", " ")
            if exc:
                if len(exc) > 150:
                    exc = exc[:150] + "..."
                lines.append(f"   > {exc}")
            lines.append("")
    else:
        lines.append("_知乎热榜里没明显科技向_")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 🌐 Hacker News Top Stories")
    lines.append("")
    if hn_items:
        for i, it in enumerate(hn_items, 1):
            lines.append(f"**{i}. [{it['title']}]({it['url']})**")
            meta = []
            if it.get("score"):
                meta.append(f"⬆️ {it['score']}")
            if it.get("comments"):
                meta.append(f"💬 [{it['comments']}]({it['hn_url']})")
            if it.get("by"):
                meta.append(f"by {it['by']}")
            if meta:
                lines.append(f"   {' · '.join(meta)}")
            lines.append("")
    else:
        lines.append("_HN 抓不到_")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("_数据来源：36氪 gateway API + 知乎热榜 + Hacker News_")
    lines.append(f"_生成时间：{now}_")
    return "\n".join(lines)


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(out_dir)
    result_dir = os.path.join(out_dir, "..", "新闻结果")
    os.makedirs(result_dir, exist_ok=True)

    print("=" * 50)
    print("  💻 科技新闻爬取 (36氪 + 知乎 + HN)")
    print("=" * 50)

    ok_sources = []
    raw = {}

    print("\n🔄 抓取 36氪 热榜 ...")
    kr_items = []
    try:
        kr_items = fetch_36kr_hot(limit=15)
        print(f"   ✅ {len(kr_items)} 条")
        ok_sources.append("36氪")
        raw["36kr_hot"] = kr_items
    except Exception as e:
        print(f"   ❌ 失败: {type(e).__name__}: {str(e)[:80]}")

    print("\n🔄 抓取知乎热榜 ...")
    zhihu_all = []
    zhihu_tech = []
    try:
        zhihu_all = fetch_zhihu_hot(limit=50)
        zhihu_tech = pick_tech(zhihu_all, max_count=10)
        print(f"   ✅ {len(zhihu_all)} 条热榜，挑出 {len(zhihu_tech)} 条科技向")
        ok_sources.append("知乎热榜")
        raw["zhihu_hot"] = zhihu_all
        raw["zhihu_tech_picks"] = zhihu_tech
    except Exception as e:
        print(f"   ❌ 失败: {type(e).__name__}: {str(e)[:80]}")

    print("\n🔄 抓取 Hacker News Top ...")
    hn_items = []
    try:
        hn_items = fetch_hn_top(limit=10)
        print(f"   ✅ {len(hn_items)} 条")
        ok_sources.append("Hacker News")
        raw["hn_top"] = hn_items
    except Exception as e:
        print(f"   ❌ 失败: {type(e).__name__}: {str(e)[:80]}")

    if not ok_sources:
        print("\n⚠️  所有源都挂了")
        return

    md = build_markdown(kr_items, zhihu_tech, hn_items)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(result_dir, f"科技新闻_{ts}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    raw["_sources"] = ok_sources
    json_path = os.path.join(result_dir, f"科技原始数据_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    print(f"\n📊 使用源: {', '.join(ok_sources)}")
    print(f"{'=' * 50}")
    print(f"  📝 Markdown 简报 → {md_path}")
    print(f"  💾 原始数据     → {json_path}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()