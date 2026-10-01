import os
import re
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from html import unescape


FEEDS_FILE = "feeds.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsCrawler/1.0; +https://example.com)"
}

FUNNY_HIT_KEYWORDS = [
    "笑哭", "离谱", "奇葩", "沙雕", "神操作", "翻车", "社死",
    "万万没想到", "火了", "爆红", "刷屏", "惊呆",
    "迷惑行为", "名场面", "爆笑", "乐坏", "笑翻",
    "魔性", "搞怪", "骚操作",
    "狗子", "萌宠", "萌娃",
    "吐槽", "玩坏", "整活", "绝了", "脑洞", "反差",
    "看傻", "离谱到家", "笑不活", "绷不住", "破防",
    "太猛", "炸锅", "吵翻", "炸了",
]

SERIOUS_BLOCK_KEYWORDS = [
    "调查", "查处", "违纪", "违法", "犯罪", "逮捕", "起诉", "判刑",
    "受贿", "贪污", "腐败", "落马", "审查", "通报", "免职",
    "死亡", "遇难", "事故", "灾害", "救灾", "暴雨", "地震",
    "疫情", "确诊", "防控",
    "战争", "军事", "导弹",
    "政策", "条例", "法规", "通知",
    "高考", "法考", "公务员",
    "法院", "检察", "公安", "警方",
    "身亡", "涉嫌",
]


def load_feeds() -> dict:
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_feeds(feeds: dict):
    with open(FEEDS_FILE, "w", encoding="utf-8") as f:
        json.dump(feeds, f, ensure_ascii=False, indent=2)


def fetch_rss(url: str, timeout: int = 15) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _clean_xml(raw: str) -> str:
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw)
    raw = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<style[^>]*>.*?</style>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"&(?!(amp;|lt;|gt;|quot;|apos;|#\d+;|#x[\da-fA-F]+;))", "&amp;", raw)
    return raw


def parse_rss(xml_text: str) -> list:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        root = ET.fromstring(_clean_xml(xml_text))

    items = []
    for item in root.iter("item"):
        entry = {}
        for child in item:
            tag = child.tag.split("}")[-1]
            if tag in ("title", "link", "pubDate", "description"):
                entry[tag] = unescape(child.text or "").strip()
        if entry:
            items.append(entry)
    return items


def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def score_funny(item: dict) -> int:
    title = item.get("title", "")
    desc = clean_html(item.get("description", ""))
    combined = title + " " + desc[:60]

    block = sum(1 for k in SERIOUS_BLOCK_KEYWORDS if k in combined)
    hit = sum(1 for k in FUNNY_HIT_KEYWORDS if k in combined)
    return hit - block * 100


def collect_funny(items_by_source: dict, max_count: int = 10) -> list:
    scored = []
    for source, items in items_by_source.items():
        for it in items:
            s = score_funny(it)
            if s >= 1:
                scored.append((s, source, it))

    scored.sort(key=lambda x: x[0], reverse=True)

    seen_titles = set()
    result = []
    for s, src, it in scored:
        t = it.get("title", "")[:20]
        if t in seen_titles:
            continue
        seen_titles.add(t)
        result.append((src, it))
        if len(result) >= max_count:
            break
    return result


def fetch_all():
    feeds = load_feeds()
    tech_results = {}
    funny_pool = {}

    skipped = 0
    tried = 0
    failed_now = []

    for category in ("tech", "social"):
        for feed in feeds.get(category, []):
            name = feed["name"]
            url = feed["url"]
            status = feed.get("status", "untested")

            if status == "fail":
                skipped += 1
                continue

            tried += 1
            try:
                print(f"🔄 抓取 [{name}] ...")
                items = parse_rss(fetch_rss(url))
                tech_results[name] = items[:12] if category == "tech" else {}
                funny_pool[name] = items
                feed["status"] = "ok"
                feed["reason"] = ""
                print(f"   ✅ {len(items)} 条")
            except Exception as e:
                err_type = type(e).__name__
                err_msg = str(e)
                reason = f"{err_type}: {err_msg[:80]}"
                print(f"   ❌ 失败: {reason}")
                feed["status"] = "fail"
                feed["reason"] = reason
                failed_now.append(name)

    save_feeds(feeds)

    funny = collect_funny(funny_pool)

    print(f"\n📊 本次统计: 尝试 {tried} 个源, 跳过 {skipped} 个已标记失败, 新失败 {len(failed_now)} 个")
    if failed_now:
        print(f"   新失败源: {', '.join(failed_now)}")
    print(f"🎯 沙雕/搞笑新闻筛出 {len(funny)} 条")

    return tech_results, funny


def build_markdown(tech: dict, funny: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# 📰 每日简报 · {today}",
        f"",
        f"> 更新时间：{now}",
        f"",
        f"---",
        f"",
        f"## 🔬 科技热点",
        f"",
    ]
    idx = 1
    for source, items in tech.items():
        if not items:
            continue
        lines.append(f"### {source}")
        lines.append("")
        for it in items[:8]:
            title = it.get("title", "")
            link = it.get("link", "")
            desc = clean_html(it.get("description", ""))
            if len(desc) > 90:
                desc = desc[:90] + "…"
            lines.append(f"{idx}. **{title}**")
            idx += 1
            if desc:
                lines.append(f"   > {desc}")
            if link:
                lines.append(f"   🔗 {link}")
            lines.append("")
        lines.append("")

    lines.extend([
        f"---",
        f"",
        f"## 😂 沙雕/搞笑新闻",
        f"",
    ])
    if not funny:
        lines.append("_今日暂无特别沙雕的新闻 🥲_")
        lines.append("")
    else:
        for i, (src, it) in enumerate(funny, 1):
            title = it.get("title", "")
            link = it.get("link", "")
            desc = clean_html(it.get("description", ""))
            if len(desc) > 110:
                desc = desc[:110] + "…"
            lines.append(f"**{i}. {title}**  _（来自 {src}）_")
            if desc:
                lines.append(f"   > {desc}")
            if link:
                lines.append(f"   🔗 {link}")
            lines.append("")

    return "\n".join(lines)


def save_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def save_markdown(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(out_dir)
    result_dir = os.path.join(out_dir, "..", "新闻结果")
    os.makedirs(result_dir, exist_ok=True)

    print("=" * 50)
    print("  📰 每日热点爬取 (科技 + 沙雕/搞笑)")
    print("=" * 50)

    tech, funny = fetch_all()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_content = build_markdown(tech, funny)
    md_path = os.path.join(result_dir, f"新闻简报_{ts}.md")
    save_markdown(md_path, md_content)

    raw = {"tech": tech, "funny": [{"source": s, **{k: v for k, v in it.items() if k != "source"}} for s, it in funny]}
    json_path = os.path.join(result_dir, f"新闻原始数据_{ts}.json")
    save_json(json_path, raw)

    print(f"\n{'=' * 50}")
    print(f"  📝 Markdown 简报 → {md_path}")
    print(f"  💾 原始数据     → {json_path}")
    print(f"  🗂  源状态记录   → {FEEDS_FILE}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()