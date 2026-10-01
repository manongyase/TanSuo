import os
import re
import time
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from html import unescape


FEEDS_FILE = "feeds.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FoodCrawler/1.0; +https://example.com)"
}


def load_config() -> dict:
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict):
    with open(FEEDS_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


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


def is_shenzhen_food(item: dict, keywords: list) -> bool:
    title = item.get("title", "")
    desc = clean_html(item.get("description", ""))
    combined = title + " " + desc[:100]
    if "深圳" not in combined:
        return False
    return any(kw in combined for kw in keywords)


DAILY_LIMIT = 4000
CALL_STATE_FILE = "_amap_call_state.json"


def _load_call_state() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(CALL_STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        if state.get("date") != today:
            state = {"date": today, "calls": 0}
    except (FileNotFoundError, json.JSONDecodeError):
        state = {"date": today, "calls": 0}
    return state


def _save_call_state(state: dict):
    with open(CALL_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def fetch_amap_poi(keyword: str, city: str, api_key: str, offset: int = 10, call_state: dict = None) -> list:
    if not api_key:
        return []

    if call_state is not None:
        state = _load_call_state()
        if state["calls"] >= DAILY_LIMIT:
            print(f"      ❌ 今日高德调用已达上限 {DAILY_LIMIT}，剩余关键词全部跳过")
            return []

    retries = 0
    max_retries = 2
    base_delay = 0.4

    while retries <= max_retries:
        try:
            resp = requests.get(
                "https://restapi.amap.com/v3/place/text",
                params={
                    "key": api_key,
                    "keywords": keyword,
                    "city": city,
                    "citylimit": "true",
                    "offset": offset,
                    "page": 1,
                    "extensions": "all",
                    "sortrule": "weight",
                },
                timeout=15,
            )

            if call_state is not None:
                state = _load_call_state()
                state["calls"] += 1
                _save_call_state(state)

            data = resp.json()
            if data.get("status") != "1":
                info = data.get("info", "未知错误")
                if "EXCEEDED_THE_LIMIT" in info or "TIMEOUT" in info:
                    retries += 1
                    if retries <= max_retries:
                        delay = base_delay * (2 ** retries)
                        print(f"      ⚠️ 限流/超时（第 {retries} 次），等 {delay:.1f}s 重试...")
                        time.sleep(delay)
                        continue
                print(f"      ⚠️ 高德返回: {info}")
                return []

            pois = data.get("pois", [])
            results = []
            for p in pois:
                results.append({
                    "name": p.get("name", ""),
                    "address": p.get("address", "") or p.get("pname", "") + p.get("cityname", ""),
                    "rating": p.get("biz_ext", {}).get("rating", "") if isinstance(p.get("biz_ext"), dict) else "",
                    "cost": p.get("biz_ext", {}).get("cost", "") if isinstance(p.get("biz_ext"), dict) else "",
                    "tel": p.get("tel", ""),
                    "tag": p.get("tag", ""),
                    "type": p.get("type", ""),
                    "dist": p.get("distance", ""),
                    "source": "高德地图",
                })
            return results

        except Exception as e:
            retries += 1
            if retries <= max_retries:
                delay = base_delay * (2 ** retries)
                print(f"      ⚠️ 请求异常（第 {retries} 次）: {type(e).__name__}，等 {delay:.1f}s 重试...")
                time.sleep(delay)
                continue
            print(f"      ❌ 高德请求失败: {type(e).__name__}: {str(e)[:50]}")
            return []

    return []


def fetch_all_pois(cfg: dict) -> dict:
    api_key = cfg.get("amap_key", "").strip()
    city = cfg.get("amap_city", "深圳")
    categories = cfg.get("poi_categories", [])

    if not api_key:
        print("\n⚠️  未配置高德地图 API Key，跳过动态 POI 抓取")
        print("   📝 免费注册：https://console.amap.com/dev/key/app")
        print("   拿到 Key 后填入 feeds.json 的 amap_key 字段即可")
        return {}

    state = _load_call_state()
    remaining = DAILY_LIMIT - state["calls"]
    print(f"\n🗺  高德地图 POI 搜索（城市={city}）")
    print(f"   📊 今日已调用 {state['calls']} / {DAILY_LIMIT}，剩余 {remaining}")

    if remaining <= 0:
        print("   ❌ 今日额度已用尽，全部跳过")
        return {}

    total_before = state["calls"]
    all_pois = {}
    for cat in categories:
        state = _load_call_state()
        if state["calls"] >= DAILY_LIMIT:
            print("   ❌ 额度用尽，剩余分类全部跳过")
            break

        label = cat["label"]
        keywords = cat.get("keywords") or [cat.get("keyword", "")]
        seen = set()
        merged = []
        for kw in keywords:
            state = _load_call_state()
            if state["calls"] >= DAILY_LIMIT:
                break
            print(f"   🔍 [{label}] 关键词='{kw}' ...")
            pois = fetch_amap_poi(kw, city, api_key, offset=6, call_state=True)
            time.sleep(0.35)
            for p in pois:
                key = p["name"] + "|" + p.get("address", "")
                if key not in seen:
                    seen.add(key)
                    merged.append(p)
        merged.sort(key=lambda x: float(x.get("rating") or 0), reverse=True)
        all_pois[label] = merged
        if merged:
            print(f"      ✅ 去重后 {len(merged)} 家店铺（合并 {len(keywords)} 个关键词）")
        else:
            print(f"      🚫 无结果")

    state = _load_call_state()
    used = state["calls"] - total_before
    print(f"\n   📊 本次消耗 {used} 次，今日累计 {state['calls']} / {DAILY_LIMIT}")

    return all_pois


def filter_by_price(pois: list, tiers: list) -> dict:
    result = {}
    for tier in tiers:
        label = tier["label"]
        min_c = tier.get("min_cost", 0)
        max_c = tier.get("max_cost", 99999)
        bucket = []
        for p in pois:
            try:
                cost = float(p.get("cost") or 0)
            except ValueError:
                continue
            if min_c <= cost <= max_c:
                bucket.append(p)
        result[label] = bucket
    return result


def fetch_dynamic_news(cfg: dict) -> list:
    sources = cfg.get("rss_sources", [])
    keywords = cfg.get("food_keywords", [])
    results = []

    for src in sources:
        name = src["name"]
        url = src["url"]
        status = src.get("status", "untested")
        if status == "fail":
            continue
        try:
            print(f"🔄 抓取 [{name}] ...")
            items = parse_rss(fetch_rss(url))
            matched = [it for it in items if is_shenzhen_food(it, keywords)]
            src["status"] = "ok"
            src["reason"] = ""
            if matched:
                print(f"   ✅ {len(items)} 条中筛出 {len(matched)} 条深圳美食相关")
                for it in matched:
                    results.append({"source": name, **it})
            else:
                print(f"   ✅ {len(items)} 条 (无深圳美食相关)")
        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)[:60]}"
            print(f"   ❌ 失败: {err_msg}")
            src["status"] = "fail"
            src["reason"] = err_msg

    save_config(cfg)
    return results


def build_markdown(cfg: dict, dynamic: list, poi_map: dict, city: str = "深圳") -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"# 🍜 {city}美食指南", f"", f"> 更新时间：{now}", ""]

    kb = cfg.get("knowledge_base", [])
    stat_src = cfg.get("static_source", "")
    price_tiers = cfg.get("price_tiers", [])
    tips = cfg.get("tips", [])
    districts = cfg.get("districts", {})

    if stat_src:
        lines.append(f"> 📌 {stat_src}")
        lines.append("")

    cat_map = {s["category"]: s for s in kb}
    label_map = {c["label"]: c["label"] for c in cfg.get("poi_categories", [])}

    all_sections = []
    seen_cat = set()
    for c in cfg.get("poi_categories", []):
        all_sections.append(c["label"])
        seen_cat.add(c["label"])
    for s in kb:
        if s["category"] not in seen_cat:
            all_sections.append(s["category"])

    for cat in all_sections:
        kb_sec = cat_map.get(cat, {})
        items = kb_sec.get("items", [])
        static_shops = kb_sec.get("recommended_shops", [])
        dynamic_shops = poi_map.get(cat, [])

        emoji_map = {
            "粤式早茶": "🥟", "潮汕牛肉火锅": "🐂", "椰子鸡": "🥥", "客家菜": "🏡",
            "港式烧腊": "🦆", "港式糖水/甜品": "🍮", "海鲜大排档": "🦐", "日料": "🍣",
            "韩餐": "🥘", "烧烤/烤鱼": "🍢", "川菜/湘菜": "🌶", "奶茶/咖啡": "🧋",
            "小龙虾": "🦞", "夜宵": "🌙", "网红打卡": "📸",
        }
        emoji = emoji_map.get(cat, "🍽")

        lines.append(f"## {emoji} {cat}")
        lines.append("")

        if dynamic_shops:
            if price_tiers:
                price_groups = filter_by_price(dynamic_shops, price_tiers)
                has_price = any(v for v in price_groups.values())
                if has_price:
                    for tier_label, group in price_groups.items():
                        if not group:
                            continue
                        lines.append(f"**{tier_label} Top {min(len(group), 5)}：**")
                        lines.append("")
                        lines.append("| # | 店名 | 评分 | 人均 | 地址 |")
                        lines.append("|---|------|------|------|------|")
                        for i, s in enumerate(group[:5], 1):
                            rating = f"⭐ {s['rating']}" if s.get("rating") else "-"
                            cost = f"¥{s['cost']}" if s.get("cost") else "-"
                            addr = (s.get("address", "") or "")[:28]
                            name = s["name"]
                            lines.append(f"| {i} | {name} | {rating} | {cost} | {addr} |")
                        lines.append("")
                else:
                    lines.append("**🏆 高德地图评分 Top（实时数据）：**")
                    lines.append("")
                    lines.append("| # | 店名 | 评分 | 人均 | 地址 |")
                    lines.append("|---|------|------|------|------|")
                    for i, s in enumerate(dynamic_shops[:8], 1):
                        rating = f"⭐ {s['rating']}" if s.get("rating") else "-"
                        cost = f"¥{s['cost']}" if s.get("cost") else "-"
                        addr = (s.get("address", "") or "")[:28]
                        name = s["name"]
                        lines.append(f"| {i} | {name} | {rating} | {cost} | {addr} |")
                    lines.append("")
            else:
                lines.append("**🏆 高德地图评分 Top（实时数据）：**")
                lines.append("")
                lines.append("| # | 店名 | 评分 | 人均 | 地址 |")
                lines.append("|---|------|------|------|------|")
                for i, s in enumerate(dynamic_shops[:8], 1):
                    rating = f"⭐ {s['rating']}" if s.get("rating") else "-"
                    cost = f"¥{s['cost']}" if s.get("cost") else "-"
                    addr = (s.get("address", "") or "")[:28]
                    name = s["name"]
                    lines.append(f"| {i} | {name} | {rating} | {cost} | {addr} |")
                lines.append("")
        elif static_shops:
            lines.append("<details>")
            lines.append("<summary>📌 静态推荐（公开整理，点开查看）</summary>")
            lines.append("")
            for s in static_shops:
                lines.append(f"- 🏪 **{s['name']}** — {s['desc']}")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        if items:
            lines.append("<details>")
            lines.append("<summary>🥢 必点菜品（点开查看）</summary>")
            lines.append("")
            for it in items:
                lines.append(f"- **{it['name']}** — {it['desc']}")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    if districts:
        lines.append("---")
        lines.append("")
        lines.append("## 📍 各区觅食地图")
        lines.append("")
        lines.append("| 区域 | 推荐聚集地 |")
        lines.append("|------|------------|")
        for dist, shops in districts.items():
            lines.append(f"| {dist} | {', '.join(shops)} |")
        lines.append("")

    if tips:
        lines.append("---")
        lines.append("")
        lines.append("## 💡 深圳美食小贴士")
        lines.append("")
        for t in tips:
            lines.append(f"- 💡 {t}")
        lines.append("")

    if dynamic:
        lines.append("---")
        lines.append("")
        lines.append("## 📰 近期美食动态")
        lines.append("")
        for i, it in enumerate(dynamic[:8], 1):
            title = it.get("title", "")
            src = it.get("source", "")
            link = it.get("link", "")
            desc = clean_html(it.get("description", ""))
            if len(desc) > 100:
                desc = desc[:100] + "…"
            lines.append(f"**{i}. {title}**  _（来自 {src}）_")
            if desc:
                lines.append(f"   > {desc}")
            if link:
                lines.append(f"   🔗 {link}")
            lines.append("")

    if not cfg.get("amap_key", "").strip():
        lines.append("---")
        lines.append("")
        lines.append("## 🔑 升级：开启动态餐厅排名")
        lines.append("")
        lines.append("本报告中的餐厅推荐来自我维护的静态清单。")
        lines.append("想要**真实的大众点评/美团聚合评分排名 + 按价格分组**？只需 2 步：")
        lines.append("")
        lines.append("1. 打开 [高德开放平台](https://console.amap.com/dev/key/app) 免费注册")
        lines.append("2. 创建一个 Web 服务 Key，粘贴到 `food/feeds.json` 的 `amap_key` 字段")
        lines.append("")
        lines.append("每日 5000 次免费调用额度，完全够用 ✅")
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
    result_dir = os.path.join(out_dir, "..", "美食结果")
    os.makedirs(result_dir, exist_ok=True)

    print("=" * 50)
    print("  🍜 深圳美食指南爬取")
    print("=" * 50)

    cfg = load_config()

    print("\n📚 加载深圳美食知识库...")
    kb = cfg.get("knowledge_base", [])
    total_items = sum(len(s.get("items", [])) for s in kb)
    total_shops = sum(len(s.get("recommended_shops", [])) for s in kb)
    print(f"   ✅ {len(kb)} 个分类, {total_items} 道特色菜, {total_shops} 家推荐店")

    poi_map = fetch_all_pois(cfg)
    total_dynamic = sum(len(v) for v in poi_map.values())
    print(f"\n📊 动态 POI: {total_dynamic} 家餐厅")

    print("\n🔍 抓取公开源中的深圳美食动态...")
    dynamic = fetch_dynamic_news(cfg)
    print(f"\n📊 抓到 {len(dynamic)} 条近期深圳美食相关动态")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_content = build_markdown(cfg, dynamic, poi_map)
    md_path = os.path.join(result_dir, f"美食简报_{ts}.md")
    save_markdown(md_path, md_content)

    raw = {
        "knowledge_base": kb,
        "districts": cfg.get("districts", {}),
        "dynamic_news": dynamic,
        "poi_dynamic": poi_map,
        "generated_at": datetime.now().isoformat(),
    }
    json_path = os.path.join(result_dir, f"美食原始数据_{ts}.json")
    save_json(json_path, raw)

    print(f"\n{'=' * 50}")
    print(f"  📝 Markdown 简报 → {md_path}")
    print(f"  💾 原始数据     → {json_path}")
    print(f"  🗂  源配置       → {FEEDS_FILE}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()