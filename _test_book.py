import requests, sys
from urllib.parse import quote
sys.stdout.reconfigure(encoding="utf-8")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
r = requests.get(f"https://book.douban.com/tag/{quote('自我提升')}?start=0&type=T", headers=UA, timeout=10)
print(f"status={r.status_code} len={len(r.text)}")

with open("_tag_sample.html", "w", encoding="utf-8") as f:
    f.write(r.text)

idx = r.text.find("class=\"subject-item\"")
print(f"subject-item idx={idx}")
if idx < 0:
    for kw in ["class=\"item\"", "class=\"subject\"", "class=\"pl2\"", "class=\"info\""]:
        idx2 = r.text.find(kw)
        print(f"  {kw} idx={idx2}")
else:
    print(r.text[idx:idx+800])