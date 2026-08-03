# 대전광역시교육청 계약체결현황 수집기 — 학교 계약 (수의·입찰 모두 공개)
# 사용: python3 collect_dje.py [--keyword-file edzip_brand_keywords.txt] [--years 2023,2024,2025,2026]
# 주의: 목록의 계약명·기관명은 화면용으로 잘려 나오고 원문은 title 속성에 들어 있다.
#       (제품명이 잘린 뒷부분에 있는 경우가 많아 title을 반드시 써야 한다)
#       계약상대자만 title이 없어 상세(InfoView04.do)를 행마다 한 번 더 부른다.
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request

BASE = "https://www.dje.go.kr/clean/contract/"
LIST = BASE + "InfoList04.do?m=0601&s=contractInfo"
VIEW = BASE + "InfoView04.do"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SPACING = 1.0
OUT = "dje_candidates.csv"
CKPT = ".ckpt_dje.json"
FIELDS = ["회계연도", "기관명", "계약명", "계약일", "계약금액", "계약방법", "계약상대자", "키워드"]

DEFAULT_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                    "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료",
                    "챗봇", "메타버스", "코딩", "AIDT", "클래스팅", "패들렛", "캔바"]
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")
RISKY = re.compile(r"\b(and|or|not|select|union|insert|update|delete|where|from|drop|exec)\b", re.I)

_opener = None
def opener():
    global _opener
    if _opener is None:
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _opener.addheaders = [("User-Agent", UA)]
        _opener.open(LIST, timeout=90).read()          # 세션 쿠키 확보
    return _opener

def req_retry(target, data=None):
    for wait in [5, 20, 60, 180, None]:
        try:
            r = urllib.request.Request(target, data=data,
                                       headers={"User-Agent": UA, "Referer": LIST})
            return opener().open(r, timeout=120).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

def search(keyword, year, page):
    d = {"realFsclY": "", "realCntrTargNO": "", "pageSize": "100",
         "instClssDiviEtc01": "N", "instClssDiviEtc02": "N", "fsclY": year,
         "instClssDivi": "5", "cntrInstNM": "", "cntrTargNO": "대전광역시교육청",
         "instClssDiviEtc01CheckBox": "N", "instClssDiviEtc02CheckBox": "N",
         "estbDiv": "", "schlClssDiv": "", "cntrNM": keyword, "cntrPrtnrNM": "",
         "cntrMthdDiv": "", "searchBeginDT": "", "searchFinDT": "",
         "cntrAmt1": "", "cntrAmt2": "", "page": str(page)}
    return req_retry(LIST, urllib.parse.urlencode(d).encode())

def parse(page_html):
    """계약명·기관명은 잘린 표시 텍스트가 아니라 title 속성의 원문을 쓴다"""
    m = re.search(r'<table[^>]*tbl_list.*?</table>', page_html, re.S)
    if not m:
        return []
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), re.S):
        tds = re.findall(r"(<td[^>]*>.*?</td>)", tr, re.S)   # title 속성까지 포함해서 잡는다
        if len(tds) < 7:
            continue
        def text(x):
            return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
        def full(x):
            t = re.search(r'title="([^"]*)"', x)
            return html.unescape(t.group(1)).strip() if t else text(x)
        key = re.search(r"goContractView\('([^']+)','([^']+)'\)", tds[3])
        rows.append({"회계연도": text(tds[0]), "기관명": full(tds[1]),
                     "계약방법": text(tds[2]), "계약명": full(tds[3]),
                     "계약일": text(tds[4]).replace("/", "-"),
                     "계약금액": text(tds[5]).replace(",", ""),
                     "_key": key.groups() if key else None})
    return rows

def vendor_of(fscl_y, targ_no):
    """목록에는 계약상대자가 잘려 나와 상세에서 원문을 가져온다"""
    url = f"{VIEW}?menuID=0601&realFsclY={urllib.parse.quote(fscl_y)}" \
          f"&realCntrTargNO={urllib.parse.quote(targ_no)}&instClssDivi=5&m=0601&s=contractInfo"
    s = req_retry(url)
    m = re.search(r"<th[^>]*>\s*계약상대자\s*</th>\s*<td[^>]*>(.*?)</td>", s, re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1)))).strip()

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
    ap.add_argument("--max-pages", type=int, default=300)
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
                rows = parse(search(q, year, page))
                req_n += 1
                if not rows:
                    break
                for r in rows:
                    if EXCLUDE.search(r["계약명"]):
                        continue
                    key = (r["기관명"], r["계약명"], r["계약일"])
                    if key in seen:
                        continue
                    seen.add(key)
                    vendor = ""
                    if not a.no_vendor and r["_key"]:
                        try:
                            vendor = vendor_of(*r["_key"])
                            req_n += 1
                            time.sleep(0.3)
                        except Exception as e:
                            print(f"  상세 실패({e}) — 업체명 없이 저장", flush=True)
                    r.pop("_key", None)
                    r["계약상대자"] = vendor
                    r["키워드"] = kw
                    w.writerow(r)
                    kept += 1
                f.flush()
                if len(rows) < 10:
                    break
                page += 1
                time.sleep(SPACING)
            done.add(tag)
            ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
            with open(CKPT, "w") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            print(f"[{kw} {year}] {page}페이지까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")

if __name__ == "__main__":
    main()
