# 경상남도교육청 계약체결현황 수집기 — 학교 계약
# 사용: python3 collect_gne.py [--keyword-file edzip_brand_keywords.txt]
# 특징: GET 방식이라 세션·토큰이 필요 없다. 계약명·기관명이 잘리지 않고 원문 그대로 나오며
#       계약상대자까지 목록에 있어 상세를 따로 부르지 않아도 된다.
#       기관 구분 필터가 없어 교육지원청·직속기관이 섞여 나오므로 교명으로 걸러낸다.
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request

BASE = "https://www.gne.go.kr/user/cntr/"
LIST = BASE + "BD_cntrInfoList.do"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SPACING = 1.0
OUT = "경남_candidates.csv"
CKPT = ".ckpt_경남.json"
FIELDS = ["회계연도", "기관명", "계약명", "계약일", "계약금액", "계약방법", "계약상대자", "키워드"]

DEFAULT_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                    "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료",
                    "챗봇", "메타버스", "코딩", "AIDT", "클래스팅", "패들렛", "캔바"]
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")
RISKY = re.compile(r"\b(and|or|not|select|union|insert|update|delete|where|from|drop|exec)\b", re.I)
SCHOOL_END = re.compile(r"(초등학교|중학교|고등학교|영재학교|특수학교)$")

_opener = None
def opener():
    global _opener
    if _opener is None:
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _opener.addheaders = [("User-Agent", UA)]
        _opener.open(LIST, timeout=90).read()
    return _opener

def fetch(keyword, year, page, per_page):
    q = {"q_fsclY": year, "q_cntrStDt": "", "q_cntrEdDt": "", "q_cntrInstNm": "",
         "q_cntrNm": keyword, "q_cntrMthdDivNm": "",
         "q_currPage": str(page), "q_rowPerPage": str(per_page)}
    url = LIST + "?" + urllib.parse.urlencode(q)
    for wait in [5, 20, 60, 180, None]:
        try:
            return opener().open(url, timeout=150).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

def vendor_of(seq):
    """목록에는 계약상대자가 없어 상세(BD_cntrInfoDetail.do)에서 '계약대상자명'을 가져온다"""
    url = BASE + "BD_cntrInfoDetail.do?cmSeqNo=" + seq
    for wait in [5, 20, 60, None]:
        try:
            d = opener().open(url, timeout=120).read().decode("utf-8", "replace")
            break
        except Exception as e:
            if wait is None:
                raise
            time.sleep(wait)
    ths = re.findall(r"<th[^>]*>(.*?)</th>", d, re.S)
    tds = re.findall(r"<td[^>]*>(.*?)</td>", d, re.S)
    clean = lambda x: html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
    for i, t in enumerate(ths):
        if clean(t) == "계약대상자명" and i < len(tds):
            return clean(tds[i])
    return ""

def parse(page_html):
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
             for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        # 글번호·계약기관·계약방법구분·계약명·계약일자(YYYYMMDD)·계약금액·(계약상대자)
        if len(c) < 6 or not re.fullmatch(r"\d{8}", c[4] or ""):
            continue
        seq = re.search(r"opCntrView\('(\d+)'\)", tr)
        rows.append({"회계연도": c[4][:4], "기관명": c[1], "계약방법": c[2], "계약명": c[3],
                     "계약일": f"{c[4][:4]}-{c[4][4:6]}-{c[4][6:]}",
                     "계약금액": c[5].replace(",", ""),
                     "_seq": seq.group(1) if seq else None})
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
    ap.add_argument("--years", default="2023,2024,2025,2026")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--no-vendor", action="store_true", help="상세 조회를 건너뛴다(빠름, 업체명 없음)")
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
    years = a.years.split(",")
    print(f"검색어 {len(kws)}종 × 회계연도 {len(years)}개 = {len(kws)*len(years)}조합", flush=True)
    kept = req_n = 0
    for kw in kws:
        q = safe_kw(kw)
        if not q:
            continue
        for year in years:
            tag = f"{kw}|{year}"
            if tag in done:
                continue
            page = 1
            while page <= a.max_pages:
                rows = parse(fetch(q, year, page, a.page_size))
                req_n += 1
                if not rows:
                    break
                for r in rows:
                    if not SCHOOL_END.search(r["기관명"]) or EXCLUDE.search(r["계약명"]):
                        continue
                    key = (r["기관명"], r["계약명"], r["계약일"])
                    if key in seen:
                        continue
                    seen.add(key)
                    vendor = ""
                    if not a.no_vendor and r["_seq"]:
                        try:
                            vendor = vendor_of(r["_seq"])
                            req_n += 1
                            time.sleep(0.3)
                        except Exception as e:
                            print(f"  상세 실패({e}) — 업체명 없이 저장", flush=True)
                    r.pop("_seq", None)
                    r["계약상대자"] = vendor
                    r["키워드"] = kw
                    w.writerow(r)
                    kept += 1
                f.flush()
                if len(rows) < a.page_size:
                    break
                page += 1
                time.sleep(SPACING)
            done.add(tag)
            ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
            with open(CKPT, "w") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            print(f"[{tag}] {page}페이지까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")

if __name__ == "__main__":
    main()
