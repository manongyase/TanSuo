import os
import json
import requests
from datetime import datetime
from html import unescape
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
AMAP_KEY = "863c484af2931885cbcb4041b02b38cf"
AMAP_PLACE = "https://restapi.amap.com/v3/place/text"
AMAP_DISTRICT = "https://restapi.amap.com/v3/config/district"
AMAP_POID = "https://restapi.amap.com/v3/place/detail"

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

RSS_FEEDS = [
    {"name": "IT之家", "url": "https://www.ithome.com/rss/"},
    {"name": "爱范儿", "url": "https://www.ifanr.com/feed"},
    {"name": "极客公园", "url": "https://www.geekpark.net/rss"},
    {"name": "少数派", "url": "https://sspai.com/feed"},
    {"name": "雷锋网", "url": "https://www.leiphone.com/feed"},
    {"name": "人民网-社会", "url": "http://www.people.com.cn/rss/society.xml"},
    {"name": "人民网-财经", "url": "http://www.people.com.cn/rss/finance.xml"},
]


def amap_poi_search(keyword, city="太原", max_count=50):
    print(f"🔍 高德搜 POI [{keyword}] in {city} ...")
    collected = []
    for page in range(1, 6):
        params = {
            "key": AMAP_KEY,
            "keywords": keyword,
            "city": city,
            "output": "JSON",
            "offset": 25,
            "page": page,
            "extensions": "base",
        }
        r = requests.get(AMAP_PLACE, params=params, headers=UA, timeout=10)
        d = r.json()
        if d.get("status") != "1":
            print(f"   ❌ 高德失败: {d.get('info')}")
            break
        pois = d.get("pois", [])
        if not pois:
            break
        collected.extend(pois)
        print(f"   第{page}页: +{len(pois)} 条, 累计 {len(collected)}")
        if len(pois) < 25 or len(collected) >= max_count:
            break
    return collected[:max_count]


def fetch_rss(url, timeout=15):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_rss_items(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        import re
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", xml_text)
        cleaned = re.sub(r"&(?!(amp;|lt;|gt;|quot;|apos;|#\d+;|#x[\da-fA-F]+;))", "&amp;", cleaned)
        root = ET.fromstring(cleaned)
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


def clean_html(text):
    import re
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def collect_huawei_news():
    keywords = ["mate90", "mate 90", "Mate90", "Mate 90", "华为90", "华为mate"]
    print("\n📰 扫描 RSS 新闻源找华为 Mate 90 相关 ...")
    results = []
    for feed in RSS_FEEDS:
        try:
            print(f"  🔄 {feed['name']} ...", end=" ")
            items = parse_rss_items(fetch_rss(feed["url"]))
            hit = []
            for it in items:
                title = it.get("title", "")
                desc = clean_html(it.get("description", ""))
                combined = (title + " " + desc).lower()
                if any(k.lower() in combined for k in keywords):
                    hit.append(it)
            results.append({"source": feed["name"], "hits": hit})
            print(f"✅ {len(items)} 条里命中 {len(hit)} 条")
        except Exception as e:
            print(f"❌ {type(e).__name__}: {str(e)[:60]}")
    return results


def search_taiyuan_mentions(news_results):
    taiyuan_hits = []
    province_words = ["山西", "太原"]
    for r in news_results:
        src = r["source"]
        for it in r["hits"]:
            title = it.get("title", "")
            desc = clean_html(it.get("description", ""))
            combined = title + " " + desc
            if any(w in combined for w in province_words):
                taiyuan_hits.append({"source": src, **it})
    return taiyuan_hits


def filter_valid_stores(pois):
    exclude_bad = ["维修", "服务中心", "售后", "客服"]
    valid = []
    seen = set()
    for p in pois:
        name = p.get("name", "")
        addr = p.get("address", "")
        for bad in exclude_bad:
            if bad in name:
                break
        else:
            key = name + addr
            if key in seen:
                continue
            seen.add(key)
            valid.append({
                "name": name,
                "address": addr,
                "area": p.get("adname", ""),
                "tel": p.get("tel", ""),
                "type": p.get("type", ""),
                "rating": p.get("biz_ext", {}).get("rating", "") if isinstance(p.get("biz_ext"), dict) else "",
                "cost": p.get("biz_ext", {}).get("cost", "") if isinstance(p.get("biz_ext"), dict) else "",
                "lng": p.get("location", ",").split(",")[0],
                "lat": p.get("location", ",").split(",")[1] if "," in p.get("location", "") else "",
            })
    return valid


def build_markdown(valid_experience, valid_authorized, taiyuan_news, all_news):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# 🔍 太原华为 Mate 90 系列售卖情况调研",
        f"",
        f"> 调研时间：{now}",
        f"> 数据来源：高德地图 POI + RSS 新闻源",
        f"",
        f"---",
        f"",
        f"## 📊 门店概览",
        f"",
    ]

    area_stats = {}
    for s in valid_experience + valid_authorized:
        area = s["area"] or "未知区域"
        area_stats[area] = area_stats.get(area, 0) + 1

    lines.append(f"| 类型 | 数量 |")
    lines.append(f"|------|------|")
    lines.append(f"| 华为体验店 | {len(valid_experience)} |")
    lines.append(f"| 华为授权店 | {len(valid_authorized)} |")
    lines.append(f"| **合计** | **{len(valid_experience) + len(valid_authorized)}** |")
    lines.append("")
    lines.append(f"**区域分布：**")
    lines.append("")
    for area, cnt in sorted(area_stats.items(), key=lambda x: -x[1]):
        lines.append(f"- **{area}**: {cnt} 家")
    lines.append("")

    def store_table(stores, title):
        lines.append(f"### {title}（{len(stores)} 家）")
        lines.append("")
        lines.append("| # | 店名 | 区域 | 地址 | 电话 | 评分 |")
        lines.append("|---|------|------|------|------|------|")
        for i, s in enumerate(stores, 1):
            tel = s["tel"] or "-"
            rating = s["rating"] or "-"
            addr_short = s["address"][:30] + "…" if len(s["address"]) > 30 else s["address"]
            lines.append(f"| {i} | {s['name']} | {s['area']} | {addr_short} | {tel} | {rating} |")
        lines.append("")

    store_table(valid_experience, "🏬 华为官方体验店")
    store_table(valid_authorized, "🏪 华为授权零售店")

    lines.append("---")
    lines.append("")
    lines.append("## 📰 相关新闻与活动报道")
    lines.append("")

    if taiyuan_news:
        lines.append("### 🎯 太原/山西相关报道")
        lines.append("")
        for i, it in enumerate(taiyuan_news, 1):
            title = it.get("title", "")
            link = it.get("link", "")
            desc = clean_html(it.get("description", ""))
            if len(desc) > 150:
                desc = desc[:150] + "…"
            lines.append(f"**{i}. {title}**  _（{it['source']}）_")
            if desc:
                lines.append(f"   > {desc}")
            if link:
                lines.append(f"   🔗 {link}")
            lines.append("")
    else:
        lines.append("_RSS 源暂未命中太原本地相关报道_")
        lines.append("")

    lines.append("### 🌐 全国 Mate 90 相关动态（精选）")
    lines.append("")
    all_hits = []
    for r in all_news:
        for it in r["hits"]:
            all_hits.append({"source": r["source"], **it})
    all_hits = all_hits[:15]
    for i, it in enumerate(all_hits, 1):
        title = it.get("title", "")
        link = it.get("link", "")
        desc = clean_html(it.get("description", ""))
        if len(desc) > 120:
            desc = desc[:120] + "…"
        lines.append(f"{i}. **{title}**  _（{it['source']}）_")
        if desc:
            lines.append(f"   > {desc}")
        if link:
            lines.append(f"   🔗 {link}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 🛒 购买建议")
    lines.append("")
    lines.append("1. **优先选华为体验店** —— 确保正品、可当场验货、有官方售后保障")
    lines.append("2. **授权零售店次之** —— 也有正品保障，但活动可能略少")
    lines.append("3. **购买前可先电话咨询** —— 确认 Mate 90 现货库存、颜色选择、是否有礼包")
    lines.append("4. **在线渠道** —— 华为商城、京东/天猫华为旗舰店可对比价格")
    lines.append("5. **推荐购机时间** —— 节后首周（10/8-10/10）门店活动可能回归常态")
    lines.append("")
    lines.append("---")
    lines.append(f"_生成时间：{now}_")
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("  🔍 太原华为 Mate 90 系列 · 售卖情况调研")
    print("=" * 60)

    experience_raw = amap_poi_search("华为体验店 手机", "太原", 30)
    authorized_raw = amap_poi_search("华为授权店 手机", "太原", 30)
    store_hint = amap_poi_search("华为 Mate90 在售", "太原", 20)
    print(f"\n  补充搜索：华为 Mate90 在售相关 POI {len(store_hint)} 条")

    valid_exp = filter_valid_stores(experience_raw)
    valid_auth = filter_valid_stores(authorized_raw)
    print(f"\n✅ 有效门店：体验店 {len(valid_exp)} 家, 授权店 {len(valid_auth)} 家")

    news_results = collect_huawei_news()
    taiyuan_mentions = search_taiyuan_mentions(news_results)
    print(f"\n🗞  全国 Mate 90 相关新闻共 {sum(len(r['hits']) for r in news_results)} 条")
    print(f"🏙  太原/山西命中 {len(taiyuan_mentions)} 条")

    md = build_markdown(valid_exp, valid_auth, taiyuan_mentions, news_results)

    result_dir = os.path.join(OUT_DIR, "华为太原调研结果")
    os.makedirs(result_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    md_path = os.path.join(result_dir, f"太原华为Mate90售卖调研_{ts}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    raw = {
        "_timestamp": ts,
        "experience_stores": valid_exp,
        "authorized_stores": valid_auth,
        "extra_poi_hint": store_hint,
        "taiyuan_news": taiyuan_mentions,
        "all_news": news_results,
    }
    json_path = os.path.join(result_dir, f"太原华为Mate90原始数据_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"  📝  Markdown 报告 → {md_path}")
    print(f"  💾  原始数据      → {json_path}")
    print(f"{'=' * 60}")
    print(f"\n🏬 太原华为门店 Top 10（体验店）：")
    for i, s in enumerate(valid_exp[:10], 1):
        print(f"  {i}. {s['name']} | {s['area']} | {s['address'][:40]}")

    print(f"\n🏪 华为授权店 Top 10：")
    for i, s in enumerate(valid_auth[:10], 1):
        print(f"  {i}. {s['name']} | {s['area']} | {s['address'][:40]}")

    if taiyuan_mentions:
        print(f"\n🎯 太原本地相关报道：")
        for it in taiyuan_mentions[:5]:
            print(f"  · {it.get('title','')[:60]}  ({it['source']})")


if __name__ == "__main__":
    main()