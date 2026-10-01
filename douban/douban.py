import os
import sys
import json
import requests
from datetime import datetime

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

DOUBAN_API = "https://movie.douban.com/j/search_subjects"

CATEGORIES = [
    {"key": "movie", "label": "电影",
     "tags": ["热门", "豆瓣高分", "最新", "经典", "冷门佳片"]},
    {"key": "tv", "label": "电视剧",
     "tags": ["热门", "国产剧", "韩剧", "美剧", "日剧"]},
    {"key": "variety", "label": "综艺",
     "tags": ["热门", "豆瓣高分", "最新", "经典"]},
    {"key": "cartoon", "label": "动漫",
     "tags": ["热门", "豆瓣高分", "最新", "经典"]},
]


def fetch_list(category_key, tag, limit=15):
    params = {
        "type": category_key,
        "tag": tag,
        "sort": "recommend",
        "page_limit": limit,
        "page_start": 0,
    }
    try:
        r = requests.get(DOUBAN_API, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("subjects", [])
    except Exception as e:
        print(f"[WARN] {category_key}/{tag} 请求失败: {e}")
        return []


def build_markdown(all_data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.append(f"# 豆瓣榜单简报")
    lines.append(f"> 生成时间: {now}")
    lines.append(f"> 数据源: 豆瓣官方 /j/search_subjects")
    lines.append(f"> 覆盖品类: 电影 / 电视剧 / 综艺 / 动漫")
    lines.append("")

    for cat in CATEGORIES:
        cat_key = cat["key"]
        cat_label = cat["label"]
        lines.append(f"## 🎬 {cat_label}")
        lines.append("")

        for tag in cat["tags"]:
            subjects = all_data.get(f"{cat_key}__{tag}", [])
            if not subjects:
                lines.append(f"### {tag}")
                lines.append("_暂无数据_")
                lines.append("")
                continue

            lines.append(f"### {tag}")
            lines.append("")
            lines.append("| # | 评分 | 标题 | 简介 | 链接 |")
            lines.append("|---|------|------|------|------|")
            for i, s in enumerate(subjects, 1):
                title = s.get("title", "未知")
                rate = s.get("rate", "N/A")
                url = s.get("url", "")
                episodes = s.get("episodes_info", "")
                playable = s.get("playable", False)
                status_icon = "▶" if playable else "📖"
                brief = episodes if episodes else f"{status_icon}{'可播放' if playable else '豆瓣条目'}"
                link_md = f"[🔗]({url})" if url else ""
                lines.append(f"| {i} | **{rate}** | {title} | {brief} | {link_md} |")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("### 📝 备注")
    lines.append("- 数据来自豆瓣公开 JSON 接口，仅供参考")
    lines.append("- 「经典」tag 多为豆瓣高分老片")
    lines.append("- 「📖」表示仅豆瓣条目无在线播放，「▶」表示可播放")
    lines.append("- 读书榜单暂缺（豆瓣读书 JSON 接口已下线）")
    lines.append("")

    return "\n".join(lines)


def main():
    result_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "豆瓣榜单结果")
    os.makedirs(result_dir, exist_ok=True)

    print("=" * 50)
    print("  豆瓣榜单爬取")
    print("=" * 50)

    all_data = {}
    for cat in CATEGORIES:
        cat_key = cat["key"]
        cat_label = cat["label"]
        for tag in cat["tags"]:
            print(f"  拉取 {cat_label} / {tag} ...", end=" ", flush=True)
            subjects = fetch_list(cat_key, tag)
            all_data[f"{cat_key}__{tag}"] = subjects
            print(f"✓ {len(subjects)} 条")

    md_content = build_markdown(all_data)
    now_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(result_dir, f"豆瓣榜单_{now_ts}.md")
    json_path = os.path.join(result_dir, f"豆瓣原始数据_{now_ts}.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print("=" * 50)
    print(f"  ✓ Markdown: {md_path}")
    print(f"  ✓ JSON备份: {json_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()