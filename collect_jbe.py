# 전북특별자치도교육청 1인 수의계약현황 수집기 — 학교 계약
# 사용: python3 collect_jbe.py [--years 2023,2024,2025,2026]
# 특징: 폼이 GET 방식이다(POST로 보내면 조건이 통째로 무시된다).
#       목록의 3번째 칸에 '계약기관+계약명'이 붙어 나와 기관명을 잘라내야 한다.
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request

BASE = "https://www.jbe.go.kr"
MENU = "DOM_000001003001009000"
PAGE = f"{BASE}/index.jbe?menuCd={MENU}"
ACT = f"{BASE}/open/edufine/eduCntrlist1.jbe"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SPACING = 1.0
OUT = "전북_candidates.csv"
CKPT = ".ckpt_전북.json"
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
        _opener.open(PAGE, timeout=90).read()
    return _opener

def fetch(keyword, year, page):
    q = {"menuCd": MENU, "pageIndex": str(page), "inst_clss_div": "5",   # 5 = 학교
         "fscl_y": year, "cntr_nm": keyword, "cntr_inst_nm": "", "cntr_prtnr_nm": "",
         "startDate": "", "endDate": "", "cntr_amt": "", "estb_div": "", "cntr_mthd_div_nm": ""}
    for wait in [5, 20, 60, None]:
        try:
            return opener().open(ACT + "?" + urllib.parse.urlencode(q), timeout=180)\
                           .read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

def split_inst(merged):
    """'전북특별자치도순창교육지원청2026 순창…' → (기관명, 계약명)
    기관명은 '…청/…학교/…원'으로 끝나므로 그 지점에서 자른다."""
    m = re.match(r"^(.*?(?:교육지원청|교육청|학교|교육원|도서관|연수원|센터))(.*)$", merged)
    return (m.group(1).strip(), m.group(2).strip()) if m else ("", merged.strip())

def parse(page_html):
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
             for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(c) < 6 or not re.search(r"\d{4}-\d{2}-\d{2}", " ".join(c)):
            continue
        inst, name = split_inst(c[3])
        rows.append({"회계연도": c[1], "기관명": inst, "계약명": name, "계약일": c[4],
                     "계약금액": re.sub(r"[^\d]", "", c[5]), "계약방법": "",
                     "계약상대자": c[6] if len(c) > 6 else ""})
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
                rows = parse(fetch(q, year, page))
                req_n += 1
                if not rows:
                    break
                for r in rows:
                    # 교육지원청·직속기관이 섞여 나오므로 학교만 남긴다
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
            done.add(tag)
            ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
            with open(CKPT, "w") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            print(f"[{tag}] {page}페이지까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")

if __name__ == "__main__":
    main()
