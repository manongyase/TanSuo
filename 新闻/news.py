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
TOPURL_NEWS_URL = "https://news.topurl.cn/api"

FUNNY_KEYWORDS = [
    "搞笑", "沙雕", "爆笑", "离谱", "整活", "好笑", "段子",
    "神评", "社死", "摸鱼", "摆烂", "奇葩", "无语", "脑洞",
    "喜剧", "吐槽", "梗", "翻车", "尴尬", "神操作", "骚操作",
    "迷惑行为", "抽象", "搞怪", "玩梗", "鬼畜", "名场面", "炸裂",
    "小丑竟是我自己", "栓Q", "笑死", "哈哈哈", "笑不活了",
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


def _funny_score(title: str, excerpt: str) -> int:
    hay = (title + " " + excerpt).lower()
    return sum(2 for kw in FUNNY_KEYWORDS if kw.lower() in hay)


def pick_funny(items: list, max_count: int = 10) -> list:
    scored = [(s, it) for s, it in ((_funny_score(i["title"], i["excerpt"]), i) for i in items) if s > 0]
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


def build_markdown(zhihu_funny: list, zhihu_all: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = ["# 🤣 搞笑热点精选", "", f"> 更新时间：{now}", ""]

    source = zhihu_funny if zhihu_funny else zhihu_all[:10]
    if not zhihu_funny:
        lines.append("_今天热榜里没明显搞笑的，直接给你前 10 条热榜_")
        lines.append("")

    for i, it in enumerate(source, 1):
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

    lines.append("---")
    lines.append("")
    lines.append("_数据来源：知乎热榜_")
    lines.append(f"_生成时间：{now}_")
    return "\n".join(lines)


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(out_dir)
    result_dir = os.path.join(out_dir, "..", "新闻结果")
    os.makedirs(result_dir, exist_ok=True)

    print("=" * 50)
    print("  🤣 搞笑热点爬取")
    print("=" * 50)

    print("\n🔄 抓取知乎热榜 ...")
    zhihu_all = []
    try:
        zhihu_all = fetch_zhihu_hot(limit=50)
        print(f"   ✅ {len(zhihu_all)} 条")
    except Exception as e:
        print(f"   ❌ 失败: {type(e).__name__}: {str(e)[:80]}")

    if not zhihu_all:
        print("\n⚠️  所有源都挂了")
        return

    funny = pick_funny(zhihu_all, max_count=10)
    md = build_markdown(funny, zhihu_all)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(result_dir, f"搞笑热点_{ts}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    json_path = os.path.join(result_dir, f"搞笑原始数据_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"zhihu_hot": zhihu_all, "funny_picks": funny}, f, ensure_ascii=False, indent=2)

    print(f"\n🤣 挑出 {len(funny)} 条搞笑向")
    print(f"{'=' * 50}")
    print(f"  📝 Markdown 简报 → {md_path}")
    print(f"  💾 原始数据     → {json_path}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()