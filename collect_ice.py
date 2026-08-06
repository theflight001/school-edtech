# 시도교육청 계약정보공개 수집기 (에듀파인 연계 selectCntrInfoList 계열)
# 사용: python3 collect_ice.py [--office 인천|충북] [--keywords ...] [--out ...]
# 같은 화면을 쓰는 시도가 여럿이라 주소·sysId만 바꿔 재사용한다.
# 배경: 나라장터·S2B에 안 잡히는 소액 구매(수만~수십만 원)가 여기에 남는다.
#       K-에듀파인과 연계돼 자동 공개되며 로그인이 필요 없다.
# 결과: ice_candidates.csv (계약번호 대신 기관+계약명+계약일로 중복 판별)
import argparse, csv, html, http.cookiejar, json, os, re, sys, time, urllib.parse, urllib.request

# 시도별: (주소, sysId, mi) — mi가 없는 곳은 빈 문자열
OFFICES = {
    "인천": ("https://www.ice.go.kr/contract/ir/selectCntrInfoList.do", "contract", "11307"),
    "충북": ("https://www.cbe.go.kr/cbe/ir/selectCntrInfoList.do", "cbe", "11608"),
    # 전남은 jne.go.kr → jge.go.kr로 넘어간다. 넘어가면서 POST 본문이 사라져
    # 검색 조건이 통째로 무시되므로 최종 주소를 직접 쓴다.
    "전남": ("https://www.jge.go.kr/main/ir/selectCntrInfoList.do", "main", ""),
}
URL = OFFICES["인천"][0]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
PAGE = 100          # 한 번에 받는 행 수
SYSID = OFFICES["인천"][1]
MI = OFFICES["인천"][2]
SPACING = 1.5       # 초 — 공개 시스템이라 여유 있으나 예의상 간격을 둔다
OUT = "ice_candidates.csv"
CKPT = ".ckpt_ice.json"
FIELDS = ["회계연도", "기관명", "계약방법", "구분", "계약명", "계약일", "계약금액", "계약상대자", "키워드"]

DEFAULT_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                    "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료",
                    "챗봇", "메타버스", "코딩", "AIDT", "클래스팅", "패들렛", "캔바"]
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")

_opener = None
def opener():
    global _opener
    if _opener is None:
        cj = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _opener.addheaders = [("User-Agent", UA)]
        _opener.open(URL + (f"?mi={MI}" if MI else ""), timeout=30).read()   # 세션 쿠키 확보
    return _opener

def fetch(keyword, page):
    data = {"sysId": SYSID, "currPage": str(page), "pageIndex": str(PAGE), "cmSeqNo": "",
            "schFsclY": "ALL", "schInstClssDiv": "5",   # 5 = 학교
            "schCntrPodiv": "", "schCntrInstNm": "", "schCntrNm": keyword,
            "schStCntrDt": "", "schEdCntrDt": "", "schCntrAmt": "", "schCntrPrtnrNm": ""}
    if MI:
        data["mi"] = MI
    req = urllib.request.Request(URL, data=urllib.parse.urlencode(data).encode(),
                                 headers={"Referer": URL + (f"?mi={MI}" if MI else "")})
    for attempt, wait in enumerate([5, 20, 60, None]):
        try:
            return opener().open(req, timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

def parse(page_html):
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        if not re.search(r"\d{4}-\d{2}-\d{2}", tr):
            continue
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).replace("\xa0", " ").strip()
             for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(c) < 8:
            continue
        rows.append({"회계연도": c[1], "기관명": c[2], "계약방법": c[3], "구분": c[4],
                     "계약명": c[5], "계약일": c[6], "계약금액": c[7].replace(",", ""),
                     "계약상대자": c[8] if len(c) > 8 else ""})
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--office", default="인천", choices=list(OFFICES))
    ap.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    ap.add_argument("--keyword-file", help="검색어를 줄 단위로 담은 파일 (에듀집 제품명 등)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--max-pages", type=int, default=200)
    a = ap.parse_args()
    global URL, SYSID, MI, CKPT
    URL, SYSID, MI = OFFICES[a.office]
    if a.office != "인천":
        CKPT = f".ckpt_{a.office}.json"
        if a.out == OUT:
            a.out = f"{a.office}_candidates.csv"

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done, seen = set(ckpt["done"]), set(tuple(k) for k in ckpt["seen"])
    new_file = not os.path.exists(a.out)
    f = open(a.out, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    # 검색창이 SQL 주입 방어에 걸려 404를 내는 낱말(and/or/select 등)이 든 검색어는
    # 가장 긴 안전한 낱말 하나로 줄여서 조회한다 ("Phonics and Stuff" → "Phonics")
    RISKY = re.compile(r"\b(and|or|not|select|union|insert|update|delete|where|from|drop|exec)\b", re.I)
    def safe_kw(k):
        if not RISKY.search(k):
            return k
        toks = [t for t in re.split(r"[\s\-–—/]+", k) if t and not RISKY.fullmatch(t)]
        return max(toks, key=len) if toks else ""

    kept = req_n = 0
    kws = a.keywords.split(",")
    if a.keyword_file:
        kws = [l.strip() for l in open(a.keyword_file, encoding="utf-8") if l.strip()]
    print(f"검색어 {len(kws)}종", flush=True)
    for kw in kws:
        if kw in done:
            continue
        q = safe_kw(kw)
        if not q:
            done.add(kw)
            continue
        page = 1
        while page <= a.max_pages:
            try:
                body = fetch(q, page)
            except Exception as e:
                # 특정 검색어에서만 나는 오류로 전체 수집이 멈추지 않게 한다
                print(f"  [{kw}] 건너뜀 ({e})", flush=True)
                break
            req_n += 1
            rows = parse(body)
            if not rows:
                break
            for r in rows:
                if EXCLUDE.search(r["계약명"]):
                    continue
                key = (r["기관명"], r["계약명"], r["계약일"])
                if key in seen:
                    continue
                seen.add(key)
                r["키워드"] = kw
                w.writerow(r)
                kept += 1
            f.flush()
            if len(rows) < PAGE:
                break
            page += 1
            time.sleep(SPACING)
        done.add(kw)
        ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
        with open(CKPT, "w") as cf:
            json.dump(ckpt, cf, ensure_ascii=False)
        print(f"[{kw}] {page}페이지까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {a.out}")

if __name__ == "__main__":
    main()
