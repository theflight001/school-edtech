# 강원특별자치도교육청 수의계약공개 수집기 — 학교 계약
# 사용: python3 collect_gwe.py [--keyword-file edzip_brand_keywords.txt]
# 한계: 목록에 계약기관·계약번호·계약명·계약일자만 있고 금액·업체가 없다.
#       (다른 시도와 달리 상세 화면도 열려 있지 않아 금액은 채우지 못한다)
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request

BASE = "https://www.gwe.go.kr/open/keris/jaai001f.do"
KEY = "bTIzMDUzMTA3NzUwNTg="
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SPACING = 1.0
OUT = "강원_candidates.csv"
CKPT = ".ckpt_강원.json"
FIELDS = ["기관명", "계약번호", "계약명", "계약일", "계약금액", "계약상대자", "키워드"]

DEFAULT_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                    "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료",
                    "챗봇", "메타버스", "코딩", "AIDT", "클래스팅", "패들렛", "캔바"]
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")
RISKY = re.compile(r"\b(and|or|not|select|union|insert|update|delete|where|from|drop|exec)\b", re.I)
SCHOOL_END = re.compile(r"(초등학교|중학교|고등학교|영재학교|특수학교)$")

def get(url):
    for wait in [5, 20, 60, 180, None]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=120).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

def search(keyword, page):
    q = {"key": KEY, "menuSn": KEY, "pageIndex": str(page), "sc": "CNTRCT_NM", "sw": keyword}
    return get(BASE + "?" + urllib.parse.urlencode(q))

def parse(page_html):
    """번호·계약기관·계약번호·계약명·계약일자 순"""
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
             for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(c) < 5 or not re.search(r"\d{4}-\d{2}-\d{2}", c[4]):
            continue
        rows.append({"기관명": c[1], "계약번호": c[2], "계약명": c[3], "계약일": c[4],
                     "계약금액": "", "계약상대자": ""})
    return rows

def safe_kw(k):
    if not RISKY.search(k):
        return k
    toks = [t for t in re.split(r"[\s\-–—/]+", k) if t and not RISKY.fullmatch(t)]
    return max(toks, key=len) if toks else ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    ap.add_argument("--keyword-file")
    ap.add_argument("--max-pages", type=int, default=300)
    a = ap.parse_args()

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done, seen = set(ckpt["done"]), set(tuple(k) for k in ckpt["seen"])
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    kws = [l.strip() for l in open(a.keyword_file, encoding="utf-8") if l.strip()] \
        if a.keyword_file else a.keywords.split(",")
    print(f"검색어 {len(kws)}종", flush=True)
    kept = req_n = 0
    for kw in kws:
        if kw in done:
            continue
        q = safe_kw(kw)
        if not q:
            done.add(kw)
            continue
        page = 1
        while page <= a.max_pages:
            rows = parse(search(q, page))
            req_n += 1
            if not rows:
                break
            for r in rows:
                # 교육청·직속기관이 섞여 나오므로 학교만 남긴다
                if not SCHOOL_END.search(r["기관명"]) or EXCLUDE.search(r["계약명"]):
                    continue
                key = (r["기관명"], r["계약명"], r["계약일"])
                if key in seen:
                    continue
                seen.add(key)
                r["키워드"] = kw
                w.writerow(r)
                kept += 1
            f.flush()
            if len(rows) < 10:
                break
            page += 1
            time.sleep(SPACING)
        done.add(kw)
        ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
        with open(CKPT, "w") as cf:
            json.dump(ckpt, cf, ensure_ascii=False)
        print(f"[{kw}] {page}페이지까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")

if __name__ == "__main__":
    main()
