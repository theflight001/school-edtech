# -*- coding: utf-8 -*-
"""sitemap.xml 생성 — 검색엔진이 학교·제품 화면을 하나씩 찾게 한다(2026-10-09 사용자 결정: 구글·네이버 검색 노출).
학교는 이름이 같은 곳이 1,070건이라 학교코드 주소(/code/…)를 쓴다. 제품은 태그 이름 주소(/tag/…).
공급 기업 주소의 열쇠(vk)는 화면 코드가 만들므로 여기서는 싣지 않는다.
쓰기: python3 gen_sitemap.py   (빌드 뒤, data.js를 읽는다. update_monthly.sh가 부른다)"""
import json, re, pathlib, datetime
from urllib.parse import quote
src = pathlib.Path("data.js").read_text(encoding="utf-8")
m = re.search(r"const DB_RAW = JSON\.parse\('([\s\S]*?)'\);", src)
d = json.loads(m.group(1).replace("\\'", "'").replace("\\\\", "\\"))
BASE = "https://school-edtech.kr"
today = datetime.date.today().isoformat()
urls = [("/", "weekly", "1.0"), ("/about", "monthly", "0.6"), ("/schools", "monthly", "0.7"), ("/products", "monthly", "0.8"),
        ("/vendors", "monthly", "0.6"), ("/records", "monthly", "0.5"), ("/map", "monthly", "0.5"), ("/contact", "yearly", "0.3")]
urls += [(f"/tag/{quote(t, safe='')}", "monthly", "0.7") for t in d["tagList"]]
urls += [(f"/code/{s['c']}", "monthly", "0.5") for s in d["schoolIndex"]]
def esc(u): return u.replace("&", "&amp;")
out = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
out += [f"<url><loc>{esc(BASE + u)}</loc><lastmod>{today}</lastmod><changefreq>{f}</changefreq><priority>{p}</priority></url>" for u, f, p in urls]
out.append("</urlset>")
pathlib.Path("sitemap.xml").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"sitemap.xml: {len(urls):,} urls (학교 {len(d['schoolIndex']):,} · 제품 {len(d['tagList']):,})")
