# 서울특별시교육청 '열린 서울교육' 수의계약공개 수집기 — 학교 계약
# 사용: python3 collect_sen.py [--years 2023,2024,2025,2026]
#
# 다른 시도와 달리 계약명으로 한 번에 검색하는 화면이 없다.
# 자료가 '기관 × 기준월' 게시물(전체 25,000여 건)로 올라오고, 게시물을 열어야
# 그 달의 계약 목록이 나온다. 그래서 두 단계로 받는다.
#   1단계  목록(list0010v.do)에서 게시물 = (학교코드, NEIS코드, 기관명, 기준월)을 모은다
#   2단계  게시물마다 상세(list0010d.do)를 한 번씩 열어 계약을 전부 받는다
# 두 화면 모두 pageUnit=100이 먹혀 한 번에 100건씩 받는다(기본 10건 → 요청 수 1/10).
# 게시물 하나에 계약이 보통 20건 안팎이라 상세는 게시물당 1회면 끝난다.
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request

BASE = "https://open.sen.go.kr/fus/1/contractOpen/"
LIST = BASE + "list0010v.do"
DET = BASE + "list0010d.do"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SPACING = 0.8
OUT = "서울_candidates.csv"
CKPT = ".ckpt_서울.json"
FIELDS = ["회계연도", "기관명", "계약명", "계약일", "계약금액", "계약방법", "계약상대자", "키워드"]

# 유치원·교육지원청·직속기관을 뺀다 ('○○초등학교병설유치원'은 유치원이다)
SCHOOL_END = re.compile(r"(초등학교|중학교|고등학교|영재학교|특수학교)$")
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")

_opener = None
def opener():
    global _opener
    if _opener is None:
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _opener.addheaders = [("User-Agent", UA)]
        _opener.open(LIST + "?searchOraCode=002&searchSchoolCode=", timeout=90).read()
    return _opener

def req(url, data=None):
    for wait in [5, 20, 60, 180, None]:
        try:
            r = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Referer": LIST})
            return opener().open(r, timeout=150).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

# searchOraCode는 관할 교육지원청 코드다. 빈값으로 두면 학원·기관까지 49만 건이 섞여 나오고,
# 한 코드만 쓰면 그 지원청 관내 학교만 나온다(처음에 002=강남서초만 받아 97개교에서 멈췄다).
ORA_CODES = ["001", "002", "003", "004", "005", "006", "007", "008", "009", "010", "011"]

def list_page(page, ora, per=100):
    q = {"searchOraCode": ora, "searchSchoolCode": "", "pageIndex": str(page),
         "pageUnit": str(per), "searchCondition": "", "searchKeyword": "",
         "searchStaDate": "", "searchEndDate": ""}
    return req(LIST + "?" + urllib.parse.urlencode(q))

def posts_of(page_html):
    """게시물 = (학교코드, NEIS코드, 기관명, 기준월). 같은 행에 두 번 나와 중복을 없앤다"""
    seen, out = set(), []
    for sc, neis, name, month in re.findall(
            r"fncDetailList\('([^']*)', ?'([^']*)', ?'([^']*)', ?'(\d{6})'\)", page_html):
        k = (sc, month)
        if k in seen:
            continue
        seen.add(k)
        out.append({"sc": sc, "neis": neis, "name": html.unescape(name).strip(), "month": month})
    return out

def detail(post, per=100):
    d = {"detPageIndex": "1", "pageIndex": "1", "pageUnit": str(per),
         "school_code": post["sc"], "neis_cd": post["neis"], "stdr_month": post["month"],
         "seq": "", "searchOraCode": "002", "searchSchoolCode": ""}
    s = req(DET, urllib.parse.urlencode(d).encode())
    if "승인된 건이 없습니다" in s:
        return []
    tb = re.findall(r"<tbody>(.*?)</tbody>", s, re.S)
    if not tb:
        return []
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tb[0], re.S):
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
             for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        # 번호·구분·계약명·계약일자·계약금액·계약업체명·승인자
        if len(c) < 6 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", c[3] or ""):
            continue
        rows.append({"회계연도": c[3][:4], "기관명": post["name"], "계약명": c[2],
                     "계약일": c[3], "계약금액": c[4].replace(",", ""),
                     "계약방법": c[1], "계약상대자": c[5], "키워드": "(전수)"})
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2023,2024,2025,2026")
    ap.add_argument("--months", default="", help="기준월을 직접 지정 (예: 202601,202602)")
    ap.add_argument("--max-list-pages", type=int, default=400)
    ap.add_argument("--relist", action="store_true", help="게시물 목록을 다시 훑는다(새 달이 올라온 뒤)")
    ap.add_argument("--ora", default="", help="관할 교육지원청 코드 (기본: 11곳 전부)")
    a = ap.parse_args()

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"posts": [], "done": [], "seen": []}
    done, seen = set(ckpt["done"]), set(tuple(k) for k in ckpt["seen"])
    years = set(a.years.split(","))
    months = set(m.strip() for m in a.months.split(",") if m.strip())

    # 1단계 — 게시물 목록
    posts = ckpt.get("posts") or []
    if not posts or a.relist:
        posts = []
        for ora in (a.ora or ",".join(ORA_CODES)).split(","):
            page = 1
            while page <= a.max_list_pages:
                got = posts_of(list_page(page, ora))
                if not got:
                    break
                posts += [p for p in got if SCHOOL_END.search(p["name"])
                          and (p["month"][:4] in years if not months else p["month"] in months)]
                if page % 20 == 0:
                    print(f"  [{ora}] 목록 {page}쪽 · 학교 게시물 누적 {len(posts):,}건", flush=True)
                page += 1
                time.sleep(SPACING)
            print(f"  [{ora}] 목록 {page - 1}쪽까지 · 누적 {len(posts):,}건", flush=True)
        # 같은 게시물이 여러 쪽에 걸쳐 나오는 경우를 없앤다
        uniq, keys = [], set()
        for p in posts:
            k = (p["sc"], p["month"])
            if k not in keys:
                keys.add(k)
                uniq.append(p)
        posts = uniq
        ckpt["posts"] = posts
        with open(CKPT, "w") as cf:
            json.dump({**ckpt, "done": sorted(done), "seen": [list(k) for k in seen]},
                      cf, ensure_ascii=False)
    print(f"학교 게시물 {len(posts):,}건 (남은 것 {len(posts) - len(done):,}건)", flush=True)

    # 2단계 — 게시물별 계약 목록
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()
    kept = req_n = 0
    for i, p in enumerate(posts, 1):
        tag = f"{p['sc']}|{p['month']}"
        if tag in done:
            continue
        for r in detail(p):
            if EXCLUDE.search(r["계약명"]):
                continue
            key = (r["기관명"], r["계약명"], r["계약일"])
            if key in seen:
                continue
            seen.add(key)
            w.writerow(r)
            kept += 1
        req_n += 1
        done.add(tag)
        f.flush()
        if req_n % 50 == 0:
            ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
            with open(CKPT, "w") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            print(f"[{i}/{len(posts)}] {p['name']} {p['month']} · 누적 {kept:,}건 "
                  f"(요청 {req_n:,}회)", flush=True)
        time.sleep(SPACING)
    ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
    with open(CKPT, "w") as cf:
        json.dump(ckpt, cf, ensure_ascii=False)
    f.close()
    print(f"\n완료 — 요청 {req_n:,}회, 학교 계약 {kept:,}건 → {OUT}")

if __name__ == "__main__":
    main()
