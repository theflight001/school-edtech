# 광주광역시교육청 수의계약공개(K-에듀파인 연계) 수집기 — 학교 계약
# 사용: python3 collect_gen.py [--keyword-file edzip_brand_keywords.txt]
# 특징: 목록에 계약기관·계약명·금액·계약일이 모두 나와 상세 조회가 필요 없다.
#       school_add=1 이 학교, 한 페이지 10건 고정. 요청마다 CSRFToken이 필요하다.
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request

BASE = "https://www.gen.go.kr/opengen/kedu/index.php"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
# ── 예의 있게 받기 ─────────────────────────────────────────────
# 2026-09 전남교육청이 우리 IP를 막았다. 초당 한 번씩 몇 시간을 두드리고, 타임아웃이
# 나도 재시도를 이어 갔다 — 웹방화벽이 보기에 크롤링 봇 그 자체다.
# 간격을 열 배로 늘리고, 재시도는 세 번에서 멈추고, 한 번 실행에 받는 양에 상한을 둔다.
# 환경변수로 조절한다: EDTECH_SPACING(초) · EDTECH_MAXREQ(요청 상한)
import random as _rnd
SPACING = float(os.environ.get("EDTECH_SPACING", "10"))
MAXREQ = int(os.environ.get("EDTECH_MAXREQ", "1200"))
_req_used = [0]


class BudgetOut(Exception):
    """이번 실행에서 받기로 한 양을 다 썼다 — 체크포인트를 남기고 곱게 끝낸다"""


def polite():
    """요청 사이 간격 — 기계처럼 일정하면 더 눈에 띈다. 조금씩 흔든다."""
    _req_used[0] += 1
    if _req_used[0] > MAXREQ:
        raise BudgetOut(f"이번 실행 상한 {MAXREQ:,}회를 다 썼다")
    time.sleep(SPACING * _rnd.uniform(0.8, 1.4))
# ───────────────────────────────────────────────────────────────
OUT = "gen_candidates.csv"
CKPT = ".ckpt_gen.json"
FIELDS = ["회계연도", "기관명", "계약명", "계약일", "계약금액", "계약방법", "키워드"]

DEFAULT_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                    "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료",
                    "챗봇", "메타버스", "코딩", "AIDT", "클래스팅", "패들렛", "캔바"]
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")
RISKY = re.compile(r"\b(and|or|not|select|union|insert|update|delete|where|from|drop|exec)\b", re.I)

_opener = None
_token = None

def session(renew=False):
    """CSRFToken은 페이지를 열어야 얻을 수 있고, 세션 쿠키와 짝을 이룬다."""
    global _opener, _token
    if _opener is None or renew:
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _opener.addheaders = [("User-Agent", UA)]
        b = _opener.open(BASE + "?mode=jaai001f_list&page=1&school_add=1", timeout=120)
        b = b.read().decode("utf-8", "replace")
        m = re.search(r'name="CSRFToken"[^>]*value="([^"]+)"', b)
        if not m:
            raise RuntimeError("CSRFToken을 찾지 못했습니다 — 페이지 구조가 바뀐 듯합니다")
        _token = m.group(1)
    return _opener, _token

def fetch(keyword, page, year=""):
    for wait in [30, 120, 300, None]:
        try:
            op, tok = session()
            d = {"CSRFToken": tok, "mode": "jaai001f_list", "ordr_list": "", "school_add": "1",
                 "sdate": "", "edate": "", "cntr_amt_sc": "", "totsearch": keyword,
                 "page": str(page), "DateYear": year}   # 연도를 안 주면 올해분만 나온다
            req = urllib.request.Request(BASE, data=urllib.parse.urlencode(d).encode(),
                                         headers={"Referer": BASE + "?mode=jaai001f_list",
                                                  "User-Agent": UA})
            return op.open(req, timeout=120).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)
            session(renew=True)          # 토큰 만료일 수 있으므로 새로 받는다

def parse(page_html):
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
             for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(c) < 7:
            continue
        # 연번, 회계년도, 계약기관, 계약명, 수의계약종류명, 계약금액, 계약일자
        rows.append({"회계연도": c[1], "기관명": c[2], "계약명": c[3],
                     "계약일": c[6].replace("/", "-"), "계약금액": c[5].replace(",", ""),
                     "계약방법": c[4]})
    return rows

def safe_kw(k):
    if not RISKY.search(k):
        return k
    toks = [t for t in re.split(r"[\s\-–—/]+", k) if t and not RISKY.fullmatch(t)]
    return max(toks, key=len) if toks else ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    ap.add_argument("--keyword-file", help="검색어를 줄 단위로 담은 파일 (에듀집 제품명 등)")
    ap.add_argument("--max-pages", type=int, default=300)
    ap.add_argument("--years", default="2023,2024,2025,2026",
                    help="회계연도 목록 — 지정하지 않으면 조회가 올해분으로 한정된다")
    a = ap.parse_args()

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done, seen = set(ckpt["done"]), set(tuple(k) for k in ckpt["seen"])
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    # 파일을 주면 기본 검색어에 '더한다' — 덮어쓰면 '에듀테크·구독·코딩' 같은 알짜가
    # 통째로 빠진다(경기 2025년이 그렇게 얇아졌다: 에듀테크 2,927 → 423건).
    kws = a.keywords.split(",")
    if a.keyword_file:
        kws += [l.strip() for l in open(a.keyword_file, encoding="utf-8") if l.strip()]
    kws = list(dict.fromkeys(k for k in kws if k))
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
            rows = parse(fetch(q, page, year))
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
                r["키워드"] = kw
                w.writerow(r)
                kept += 1
            f.flush()
            if len(rows) < 10:
                break
            page += 1
            # 넓은 검색어는 수백 쪽이라 한 검색어가 끝날 때만 적으면 15분 넘게 조용해져
            # 멈춤 감시에 끊기고, 다시 걸어도 같은 자리에서 또 끊긴다(2026-09-12 경기·강원·광주)
            if page % 10 == 0:
                print(f"  …{page}페이지째", flush=True)
            polite()
        done.add(tag)
        ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
        with open(CKPT, "w") as cf:
            json.dump(ckpt, cf, ensure_ascii=False)
        print(f"[{kw} {year}] {page}페이지까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")

if __name__ == "__main__":
    try:
        main()
    except BudgetOut as e:
        # 상한에 걸려 멈춘다. 체크포인트가 있으니 다음 실행에서 이어 받는다.
        print(f"\n■ {e} — 여기서 멈춘다. 다음 실행에서 이어 받는다.")
