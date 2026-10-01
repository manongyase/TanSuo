import os
import json
from datetime import datetime


FEEDS_FILE = "feeds.json"


def load_config() -> dict:
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


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


def build_markdown(cfg: dict, pois: list, city: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"# 🥢 {city}山西菜指南", f"", f"> 更新时间：{now}", ""]

    src_note = cfg.get("source_note", "")
    if src_note:
        lines.append(f"> 📌 {src_note}")
        lines.append("")

    lines.append("> 🚫 本模块为纯静态数据，**不调用任何远程 API**")
    lines.append("")

    kb = cfg.get("knowledge_base", [])
    price_tiers = cfg.get("price_tiers", [])

    lines.append("## 🏆 深圳山西菜餐厅一览")
    lines.append("")
    lines.append(f"共收录 **{len(pois)}** 家山西菜/西北菜/刀削面相关餐厅，按评分排序：")
    lines.append("")

    if price_tiers and pois:
        price_groups = filter_by_price(pois, price_tiers)
        for tier_label, group in price_groups.items():
            if not group:
                continue
            lines.append(f"### {tier_label}（{len(group)} 家）")
            lines.append("")
            lines.append("| # | 店名 | 评分 | 人均 | 地址 |")
            lines.append("|---|------|------|------|------|")
            for i, s in enumerate(group, 1):
                rating = f"⭐ {s['rating']}" if s.get("rating") else "-"
                cost = f"¥{float(s['cost']):.0f}" if s.get("cost") else "-"
                addr = (s.get("address", "") or "")[:30]
                lines.append(f"| {i} | {s['name']} | {rating} | {cost} | {addr} |")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📋 全部餐厅详情")
    lines.append("")
    for i, s in enumerate(pois, 1):
        rating = f"⭐ {s.get('rating', '-')}" if s.get("rating") else "-"
        cost = f"¥{float(s['cost']):.0f}" if s.get("cost") else "-"
        tel = s.get("tel", "")
        if isinstance(tel, list):
            tel = "; ".join(tel)
        tag = s.get("tag", "")
        if isinstance(tag, list):
            tag = ", ".join(tag)
        typ = s.get("type", "")
        lines.append(f"**{i}. {s['name']}**  {rating}  {cost}")
        lines.append(f"- 📍 {s.get('address', '-')}")
        if tel:
            lines.append(f"- 📞 {tel}")
        if typ:
            lines.append(f"- 🏷 {typ}")
        if tag:
            lines.append(f"- 🥘 推荐：{tag[:80]}")
        lines.append("")

    for sec in kb:
        lines.append("---")
        lines.append("")
        lines.append(f"## 🍽 {sec['category']} · 必点菜品")
        lines.append("")
        for it in sec.get("items", []):
            lines.append(f"- **{it['name']}** — {it['desc']}")
        lines.append("")

        shops = sec.get("recommended_shops", [])
        if shops:
            lines.append("<details>")
            lines.append("<summary>📌 本地老饕推荐</summary>")
            lines.append("")
            for s in shops:
                lines.append(f"- 🏪 **{s['name']}** — {s['desc']}")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 💡 山西菜小贴士")
    lines.append("")
    tips = [
        "山西菜核心是碳水：面食（刀削面、莜面、剔尖）+ 过油肉 + 大盘鸡",
        "深圳的山西菜馆多夹杂西北菜/新疆菜，纯正晋菜以老太原菜馆、九毛九为代表",
        "西贝莜面村主打莜面和羊肉，属于西北风味但莜面栲栳栳是山西名吃",
        "大盘鸡一定要加宽面，面比鸡还香",
        "刀削面讲究'三棱六边中间厚'，手工削的比机器的筋道",
        "莜面栲栳栳蘸羊肉蘑菇汤吃最正宗",
    ]
    for t in tips:
        lines.append(f"- 💡 {t}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"_数据来源：高德地图（{cfg.get('source_note', '')}）_")
    lines.append(f"_生成时间：{now}_")

    return "\n".join(lines)


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(out_dir)
    result_dir = os.path.join(out_dir, "..", "山西菜结果")
    os.makedirs(result_dir, exist_ok=True)

    print("=" * 50)
    print("  🥢 深圳山西菜指南（纯静态，不调远程 API）")
    print("=" * 50)

    cfg = load_config()
    city = cfg.get("city", "深圳")
    pois = cfg.get("static_poi", [])
    kb = cfg.get("knowledge_base", [])

    print(f"\n📍 城市：{city}")
    print(f"📊 静态 POI：{len(pois)} 家餐厅")
    for sec in kb:
        items = len(sec.get("items", []))
        shops = len(sec.get("recommended_shops", []))
        print(f"   🍽 {sec['category']}: {items} 道菜, {shops} 家推荐店")

    pois_sorted = sorted(pois, key=lambda x: float(x.get("rating") or 0), reverse=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_content = build_markdown(cfg, pois_sorted, city)
    md_path = os.path.join(result_dir, f"山西菜简报_{ts}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    raw = {
        "city": city,
        "no_remote_api": True,
        "source_note": cfg.get("source_note", ""),
        "poi_static": pois_sorted,
        "knowledge_base": kb,
        "generated_at": datetime.now().isoformat(),
    }
    json_path = os.path.join(result_dir, f"山西菜原始数据_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 50}")
    print(f"  📝 Markdown 简报 → {md_path}")
    print(f"  💾 原始数据     → {json_path}")
    print(f"  🗂  源配置       → {os.path.join(out_dir, FEEDS_FILE)}")
    print(f"{'=' * 50}")
    print("  ✅ 完成！全程未访问任何远程 API")


if __name__ == "__main__":
    main()