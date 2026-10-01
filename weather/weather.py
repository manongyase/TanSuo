import os
import json
import requests
from datetime import datetime


API_FILE = "api.json"


def load_api_config() -> dict:
    with open(API_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_api_config(cfg: dict):
    with open(API_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_cities(path: str = "city.txt") -> list:
    with open(path, "r", encoding="utf-8") as f:
        cities = []
        for line in f:
            name = line.strip()
            if name and not name.startswith("#"):
                cities.append(name)
    return cities


WEEKDAY_MAP = {"1": "周一", "2": "周二", "3": "周三", "4": "周四", "5": "周五", "6": "周六", "7": "周日"}


def _city_to_adcode(city_name: str, api_key: str, district_url: str) -> dict:
    params = {"key": api_key, "keywords": city_name, "subdistrict": 0, "output": "JSON"}
    resp = requests.get(district_url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "1":
        raise ValueError(f"行政区查询失败: {data.get('info', '')}")
    districts = data.get("districts", [])
    if not districts:
        raise ValueError(f"未找到城市 adcode: {city_name}")
    d = districts[0]
    return {"adcode": d["adcode"], "citycode": d.get("citycode", ""), "name": d["name"]}


def _amap_weather(adcode: str, api_key: str, weather_url: str, extensions: str = "all") -> dict:
    params = {"key": api_key, "city": adcode, "extensions": extensions, "output": "JSON"}
    resp = requests.get(weather_url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "1":
        raise ValueError(f"高德天气失败: {data.get('info', '')}")
    return data


def fetch_amap(city_name: str, cfg: dict) -> dict:
    api_key = cfg["amap_key"]
    district_url = cfg["apis"][0]["district_url"]
    weather_url = cfg["apis"][0]["weather_url"]

    geo = _city_to_adcode(city_name, api_key, district_url)

    base = _amap_weather(geo["adcode"], api_key, weather_url, "base")
    all_data = _amap_weather(geo["adcode"], api_key, weather_url, "all")

    live = base["lives"][0]
    forecast = all_data["forecasts"][0]

    return {
        "geo": geo,
        "live": live,
        "forecast": forecast,
        "casts": forecast["casts"],
    }


def build_amap_markdown(results: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"# 🌤 天气简报（高德数据）", f"", f"> 更新时间：{now}", ""]

    for city_name, data in results:
        geo = data["geo"]
        live = data["live"]
        casts = data["casts"]
        province = live.get("province", "")
        reporttime = live.get("reporttime", "")

        lines.append(f"## 📍 {city_name}（{province} {geo['adcode']}）")
        lines.append("")
        lines.append(f"> 🕐 气象报告时间：{reporttime}")
        lines.append("")

        lines.append("### 🌡 当前实况")
        lines.append("")
        lines.append(f"| 项目 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 天气 | {live['weather']} |")
        lines.append(f"| 温度 | {live['temperature']}°C |")
        lines.append(f"| 湿度 | {live['humidity']}% |")
        lines.append(f"| 风向 | {live['winddirection']}风 |")
        lines.append(f"| 风力 | {live['windpower']} 级 |")
        lines.append("")

        lines.append("### 📅 未来预报（4 天）")
        lines.append("")
        lines.append("| 日期 | 星期 | 白天 | 白天温度 | 夜间 | 夜间温度 | 风力 |")
        lines.append("|------|------|------|----------|------|----------|------|")
        for c in casts:
            date = c["date"]
            week = WEEKDAY_MAP.get(c["week"], c["week"])
            day_w = c["dayweather"]
            day_t = c["daytemp"] + "°C"
            night_w = c["nightweather"]
            night_t = c["nighttemp"] + "°C"
            dp = c["daypower"].replace("≤", "").replace("≤3", "3")
            np = c["nightpower"].replace("≤", "").replace("≤3", "3")
            power = dp if dp == np else dp + "/" + np
            lines.append(f"| {date} | {week} | {day_w} | {day_t} | {night_w} | {night_t} | {power} 级 |")
        lines.append("")

        max_temp = max(int(c["daytemp"]) for c in casts)
        min_temp = min(int(c["nighttemp"]) for c in casts)
        max_day = max(casts, key=lambda x: int(x["daytemp"]))
        min_night = min(casts, key=lambda x: int(x["nighttemp"]))
        lines.append(f"**📊 本周期概览：最高 {max_temp}°C（{max_day['date']} {max_day['dayweather']}），最低 {min_temp}°C（{min_night['date']} {min_night['nightweather']}）**")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("_数据来源：高德开放平台（中国气象局授权）_")
    lines.append(f"_生成时间：{now}_")
    return "\n".join(lines)


WMO_CODES = {
    0: "晴", 1: "大部晴朗", 2: "局部多云", 3: "阴天",
    45: "雾", 48: "雾凇",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 81: "强阵雨", 82: "暴阵雨",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
}


def geocode_openmeteo(city_name: str, geocoding_url: str):
    params = {"name": city_name, "count": 1, "language": "zh", "format": "json"}
    resp = requests.get(geocoding_url, params=params, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results")
    if not results:
        raise ValueError(f"未找到城市: {city_name}")
    r = results[0]
    return r["latitude"], r["longitude"], r.get("country", ""), r.get("admin1", "")


def get_weather_openmeteo(lat: float, lon: float, weather_url: str):
    params = {
        "latitude": lat, "longitude": lon,
        "current": ["temperature_2m", "apparent_temperature", "relative_humidity_2m", "weather_code", "wind_speed_10m"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "weather_code", "sunrise", "sunset"],
        "timezone": "auto", "forecast_days": 4,
    }
    resp = requests.get(weather_url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def build_openmeteo_markdown(results: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"# 🌤 天气简报（Open-Meteo）", f"", f"> 更新时间：{now}", ""]
    for city, geo, data in results:
        lat, lon, country, admin = geo
        cur = data["current"]
        daily = data["daily"]
        lines.append(f"## {city}")
        lines.append("")
        lines.append(f"| 项目 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 坐标 | {lat:.2f}°N, {lon:.2f}°E ({admin}, {country}) |")
        lines.append(f"| 当前温度 | {cur['temperature_2m']}°C |")
        lines.append(f"| 体感温度 | {cur['apparent_temperature']}°C |")
        lines.append(f"| 湿度 | {cur['relative_humidity_2m']}% |")
        lines.append(f"| 风速 | {cur['wind_speed_10m']} km/h |")
        wc = cur["weather_code"]
        desc = WMO_CODES.get(wc, "未知(" + str(wc) + ")")
        lines.append(f"| 天气 | {desc} |")
        lines.append("")
        lines.append("**未来 4 天：**")
        lines.append("")
        lines.append("| 日期 | 天气 | 最低 | 最高 | 日出 | 日落 |")
        lines.append("|------|------|------|------|------|------|")
        for i, time in enumerate(daily["time"]):
            hi = daily["temperature_2m_max"][i]
            lo = daily["temperature_2m_min"][i]
            desc = WMO_CODES.get(daily["weather_code"][i], "?")
            sun_r = daily["sunrise"][i][11:16]
            sun_s = daily["sunset"][i][11:16]
            lines.append(f"| {time} | {desc} | {lo}°C | {hi}°C | {sun_r} | {sun_s} |")
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
    result_dir = os.path.join(out_dir, "..", "天气结果")
    os.makedirs(result_dir, exist_ok=True)

    print("=" * 50)
    print("  🌤  天气爬取 (按 city.txt 城市列表)")
    print("=" * 50)

    try:
        cities = load_cities()
    except FileNotFoundError:
        print("❌ 未找到 city.txt，请先在 weather 目录下创建并写入城市名")
        return

    if not cities:
        print("❌ city.txt 为空，请写入至少一个城市名")
        return

    print(f"📋 待爬取城市 ({len(cities)} 个): {', '.join(cities)}\n")

    cfg = load_api_config()

    amap_key = cfg.get("amap_key", "").strip()
    api_list = cfg.get("apis", [])

    chosen_api = None
    raw_data = {}
    md_content = ""

    # ---- 优先尝试高德 ----
    if amap_key:
        amap_cfg = next((a for a in api_list if a["name"] == "高德天气"), None)
        if amap_cfg and amap_cfg.get("status") != "fail":
            print(f"🔄 尝试 API [高德天气] ...")
            try:
                results = []
                for city in cities:
                    print(f"  🔍 查询 {city} ...")
                    d = fetch_amap(city, cfg)
                    results.append((city, d))
                amap_cfg["status"] = "ok"
                amap_cfg["reason"] = ""
                chosen_api = "高德天气"
                raw_data = {c: d for c, d in results}
                md_content = build_amap_markdown(results)
                print(f"   ✅ 高德天气成功！\n")
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)[:80]}"
                print(f"   ❌ 高德失败: {err_msg}\n")
                if amap_cfg:
                    amap_cfg["status"] = "fail"
                    amap_cfg["reason"] = err_msg

    # ---- 备选 Open-Meteo ----
    if not chosen_api:
        om_cfg = next((a for a in api_list if a["name"] == "Open-Meteo"), None)
        if om_cfg and om_cfg.get("status") != "fail":
            print(f"🔄 尝试 API [Open-Meteo] ...")
            try:
                results = []
                for city in cities:
                    print(f"  🔍 查询 {city} ...")
                    geo = geocode_openmeteo(city, om_cfg["geocoding_url"])
                    data = get_weather_openmeteo(geo[0], geo[1], om_cfg["weather_url"])
                    results.append((city, geo, data))
                om_cfg["status"] = "ok"
                om_cfg["reason"] = ""
                chosen_api = "Open-Meteo"
                raw_data = {c: {"geo": geo, "data": d} for c, geo, d in results}
                md_content = build_openmeteo_markdown(results)
                print(f"   ✅ Open-Meteo 成功！\n")
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)[:80]}"
                print(f"   ❌ Open-Meteo 失败: {err_msg}\n")
                if om_cfg:
                    om_cfg["status"] = "fail"
                    om_cfg["reason"] = err_msg

    save_api_config(cfg)

    if not chosen_api:
        print("⚠️  所有 API 都不可用，请检查配置或稍后重试")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(result_dir, f"天气简报_{ts}.md")
    save_markdown(md_path, md_content)

    raw_data["_api_used"] = chosen_api
    json_path = os.path.join(result_dir, f"天气原始数据_{ts}.json")
    save_json(json_path, raw_data)

    print(f"📊 使用 API: {chosen_api}")
    print(f"{'=' * 50}")
    print(f"  📝 Markdown 简报 → {md_path}")
    print(f"  💾 原始数据     → {json_path}")
    print(f"  🗂  API 状态记录 → {API_FILE}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()