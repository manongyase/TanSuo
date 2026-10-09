import os
import sys
import re
import json
import time
import requests
from datetime import datetime
from urllib.parse import quote

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )
}

TOP250_URL = "https://book.douban.com/top250?start={start}"
TAG_URL = "https://book.douban.com/tag/{tag}?start={start}&type=T"

KEYWORDS = [
    "自我提升", "自我成长", "个人成长", "时间管理", "自我管理",
    "习惯养成", "思维方式", "认知", "心理学", "励志",
    "高效能", "自律", "专注", "决策", "沟通",
    "学习方法", "记忆", "复盘", "意志力", "性格",
    "情商", "人生", "成长", "改变", "行动",
]

TAG_LIST = [
    "自我提升", "个人成长", "时间管理", "自我管理",
    "心理学", "思维", "习惯", "励志", "高效能",
]


def fetch_html(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=12)
            r.raise_for_status()
            return r.text
        except Exception as e:
            if i < retries - 1:
                time.sleep(1)
    return None


def parse_top250(html):
    items = re.findall(r"(?s)<tr class=\"item\">.*?</tr>", html)
    results = []
    for item in items:
        title_m = re.search(r'title="([^"]+)"', item)
        href_m = re.search(r'href="(https://book\.douban\.com/subject/\d+/)"', item)
        score_m = re.search(r'rating_nums">([\d.]+)', item)
        info_m = re.search(r'class="pl">(.*?)</p>', item, re.S)
        quote_m = re.search(r'class="inq">(.*?)</span>', item, re.S)
        title = title_m.group(1).strip() if title_m else ""
        href = href_m.group(1) if href_m else ""
        score = float(score_m.group(1)) if score_m else 0.0
        info = re.sub(r'<[^>]+>', '', info_m.group(1)).strip() if info_m else ""
        quote = quote_m.group(1).strip() if quote_m else ""
        if title and href:
            results.append({
                "title": title, "href": href, "score": score,
                "info": info, "quote": quote, "source": "Top250",
            })
    return results


def parse_tag_page(html, source_tag):
    items = re.findall(r'(?s)<div class="subject-item">.*?</div>\s*</div>', html)
    results = []
    for item in items:
        title_m = re.search(r'<a[^>]*title="([^"]+)"', item)
        href_m = re.search(r'href="(https://book\.douban\.com/subject/\d+/)"', item)
        score_m = re.search(r'rating_nums[^\d]*([\d.]+)', item)
        pub_m = re.search(r'class="pub">(.*?)</div>', item, re.S)
        if not pub_m:
            pub_m = re.search(r'class="pl">(.*?)</p>', item, re.S)
        title = title_m.group(1).strip() if title_m else ""
        href = href_m.group(1) if href_m else ""
        score = float(score_m.group(1)) if score_m else 0.0
        info = re.sub(r'<[^>]+>', '', pub_m.group(1)).strip() if pub_m else ""
        if title and href:
            results.append({
                "title": title, "href": href, "score": score,
                "info": info, "quote": "", "source": f"tag:{source_tag}",
            })
    return results


def match_score(book):
    text = f"{book['title']} {book['info']} {book['quote']}"
    hits = sum(1 for kw in KEYWORDS if kw in text)
    kw_bonus = hits * 2.0
    return book["score"] + kw_bonus


def dedupe(books):
    seen = set()
    out = []
    for b in books:
        key = b["href"]
        if key not in seen:
            seen.add(key)
            out.append(b)
    return out


def build_markdown(top30, all_count):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.append("# 📚 经典自我提升书单 Top 30")
    lines.append(f"> 生成时间: {now}")
    lines.append(f"> 数据源: 豆瓣 Top250 + 豆瓣 tag 聚合")
    lines.append(f"> 候选池: {all_count} 本 → 按关键词匹配 + 评分排序 → Top 30")
    lines.append(f"> 关键词覆盖: {', '.join(KEYWORDS[:6])} ... 共 {len(KEYWORDS)} 个")
    lines.append("")
    lines.append("| # | 评分 | 匹配度 | 书名 | 作者 / 出版 | 豆瓣链接 |")
    lines.append("|---|------|--------|------|------------|----------|")
    for i, b in enumerate(top30, 1):
        score_str = f"**{b['score']:.1f}**" if b["score"] > 0 else "N/A"
        text = f"{b['title']} {b['info']} {b['quote']}"
        hits = sum(1 for kw in KEYWORDS if kw in text)
        match_str = f"×{hits}" if hits > 0 else "-"
        info_short = b["info"][:40] + ("…" if len(b["info"]) > 40 else "")
        link = f"[🔗]({b['href']})" if b["href"] else ""
        lines.append(f"| {i} | {score_str} | {match_str} | {b['title']} | {info_short} | {link} |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("### 📖 入选理由（前 5 本关键词命中）")
    lines.append("")
    for b in top30[:5]:
        text = f"{b['title']} {b['info']} {b['quote']}"
        hits = [kw for kw in KEYWORDS if kw in text]
        reason = "、".join(hits[:3]) if hits else "豆瓣高分经典"
        lines.append(f"- **《{b['title']}》** — 关键词命中: {reason}")
    lines.append("")

    return "\n".join(lines)


def main():
    result_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "书籍结果",
    )
    os.makedirs(result_dir, exist_ok=True)

    print("=" * 55)
    print("  📚 经典自我提升书单 Top 30 爬取")
    print("=" * 55)

    all_books = []

    print("\n🔸 第一步: 豆瓣 Top250（经典基底）")
    for start in [0, 25, 50, 75]:
        url = TOP250_URL.format(start=start)
        print(f"  拉取 start={start:3d} ...", end=" ", flush=True)
        html = fetch_html(url)
        if html:
            items = parse_top250(html)
            all_books.extend(items)
            print(f"✓ {len(items)} 本")
        else:
            print("✗ 失败")
        time.sleep(0.5)

    print(f"\n🔸 第二步: 豆瓣 tag 聚合（自我提升方向）")
    for tag in TAG_LIST:
        url = TAG_URL.format(tag=quote(tag), start=0)
        print(f"  拉取 tag={tag} ...", end=" ", flush=True)
        html = fetch_html(url)
        if html:
            items = parse_tag_page(html, tag)
            all_books.extend(items)
            print(f"✓ {len(items)} 本")
        else:
            print("✗ 失败")
        time.sleep(0.5)

    all_books = dedupe(all_books)
    print(f"\n🔸 合并去重后候选池: {len(all_books)} 本")

    scored = [(match_score(b), b) for b in all_books]
    scored.sort(key=lambda x: x[0], reverse=True)

    top30 = [b for _, b in scored[:30]]

    md_content = build_markdown(top30, len(all_books))
    now_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(result_dir, f"自我提升书单_{now_ts}.md")
    json_path = os.path.join(result_dir, f"自我提升原始数据_{now_ts}.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    json_out = {
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "keywords": KEYWORDS,
        "total_pool": len(all_books),
        "top30": top30,
        "all_books": scored,
    }

    class FloatEncoder(json.JSONEncoder):
        def default(self, o):
            return round(o, 2) if isinstance(o, float) else super().default(o)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_out, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 55)
    print(f"  ✓ Markdown: {md_path}")
    print(f"  ✓ JSON备份: {json_path}")
    print("=" * 55)

    print("\n🏆 Top 5 预览:")
    for i, b in enumerate(top30[:5], 1):
        print(f"  {i}. 《{b['title']}》 豆瓣 {b['score']:.1f}")


if __name__ == "__main__":
    main()