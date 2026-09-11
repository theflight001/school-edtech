# 부산·경북 계약정보공개(K-에듀파인 자동연계) 수집기 — 학교 수의계약
# 사용: python3 collect_pen.py [--office 부산|경북] [--begin 2023-01] [--end 2026-08]
# 두 시도가 같은 화면(selectPrvcntrInfoList)을 써서 주소만 바꿔 재사용한다.
# 제약: 공개 기준 100만원 이상, 검색 기간 최대 1개월 → 월 단위로 나눠 조회한다.
import argparse, csv, html, json, os, re, time, urllib.error, urllib.parse, urllib.request
from datetime import date

OFFICES = {
    "부산": ("https://www.pen.go.kr/main/ir/selectPrvcntrInfoList.do?mi=31735", "pen_candidates.csv"),
    "경북": ("https://www.gbe.kr/kedufine/ir/selectPrvcntrInfoList.do", "경북_candidates.csv"),
}
URL = OFFICES["부산"][0]
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
OUT = "pen_candidates.csv"
CKPT = ".ckpt_pen.json"
FIELDS = ["회계연도", "기관명", "계약방법", "계약명", "계약일", "계약금액", "계약상대자", "키워드"]

DEFAULT_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                    "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료",
                    "챗봇", "메타버스", "코딩", "AIDT", "클래스팅", "패들렛", "캔바"]
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")

def months(begin, end):
    y, m = map(int, begin.split("-")); ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        last = [31, 29 if (y % 4 == 0 and y % 100 != 0) or y % 400 == 0 else 28,
                31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
        out.append((f"{y}/{m:02d}/01", f"{y}/{m:02d}/{last}", y))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out

def fetch(kw, bdt, edt, year, page):
    data = {"currPage": str(page), "xssChk": "N", "maxSn": "15", "inpAmt": "1000000",
            "pageIndex": "100", "instClCd": "5",          # 5 = 학교
            "accnutYear": str(year), "inpBdt": bdt, "inpEdt": edt,
            "inpSrchCate": "srchCntrctNm", "inpSrchTxt": kw, "minSn": "0"}
    req = urllib.request.Request(URL, data=urllib.parse.urlencode(data).encode(),
                                 headers={"User-Agent": UA, "Referer": URL})
    for attempt, wait in enumerate([5, 20, 60, None]):
        try:
            return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            # 400은 서버가 그 검색어를 못 읽는 것이라 다시 물어도 같다 — 기다리지 않고 바로 넘긴다
            # (2026-09-12 경북: 특수문자 든 검색어마다 5·20·60초를 버렸다)
            if wait is None or (isinstance(e, urllib.error.HTTPError) and e.code == 400):
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
        if len(c) < 7:
            continue
        rows.append({"회계연도": c[1], "기관명": c[2], "계약방법": c[3], "계약명": c[4],
                     "계약일": c[5], "계약금액": c[6].replace(",", ""),
                     "계약상대자": c[7] if len(c) > 7 else ""})
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--office", default="부산", choices=list(OFFICES))
    ap.add_argument("--begin", default="2023-01")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m"))
    ap.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    ap.add_argument("--keyword-file", help="검색어를 줄 단위로 담은 파일 (에듀집 제품명 등)")
    ap.add_argument("--sweep", action="store_true",
                    help="키워드 없이 월별 전수 수집 — 제품명만 적힌 계약도 놓치지 않는다")
    a = ap.parse_args()
    global URL, OUT, CKPT
    URL, OUT = OFFICES[a.office]
    if a.office != "부산":
        CKPT = f".ckpt_{a.office}.json"

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done = set(tuple(d) for d in ckpt["done"])
    seen = set(tuple(k) for k in ckpt["seen"])
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    wins = months(a.begin, a.end)
    kws = [""] if a.sweep else a.keywords.split(",")
    if a.keyword_file and not a.sweep:
        # 파일을 주면 기본 검색어를 '더한다' — 덮어쓰면 '에듀테크·구독·코딩' 같은
        # 알짜가 통째로 빠진다(경기 2025년이 그렇게 얇아졌다: 에듀테크 2,927 → 423건).
        extra = [l.strip() for l in open(a.keyword_file, encoding="utf-8") if l.strip()]
        seen, merged = set(), []
        for k in kws + extra:
            if k not in seen:
                seen.add(k); merged.append(k)
        kws = merged
        print(f"검색어 {len(kws):,}종 (기본 {len(a.keywords.split(','))} + 파일 {len(extra):,})", flush=True)
    print(f"월 {len(wins)}개 × {'전수 스윕' if a.sweep else f'키워드 {len(kws)}개'} = {len(wins)*len(kws)}조합", flush=True)
    kept = req_n = 0
    for kw in kws:
        for bdt, edt, year in wins:
            key = (kw, bdt)
            if key in done:
                continue
            page = 1
            bad = False
            while True:
                try:
                    body = fetch(kw, bdt, edt, year, page)
                except BudgetOut:
                    raise
                except Exception as e:
                    # 특수문자가 든 검색어 하나에 400이 나면 그때까지 받던 것까지 통째로 멈췄다
                    # (2026-09-12 경북, 1,884회에서 끝). 그 칸만 건너뛰고 '끝냄'으로 적지 않는다.
                    print(f"  [{kw}] 건너뜀 ({e})", flush=True)
                    bad = True
                    break
                req_n += 1
                rows = parse(body)
                for r in rows:
                    if EXCLUDE.search(r["계약명"]):
                        continue
                    k = (r["기관명"], r["계약명"], r["계약일"])
                    if k in seen:
                        continue
                    seen.add(k)
                    r["키워드"] = kw or "(전수)"
                    w.writerow(r)
                    kept += 1
                f.flush()
                if len(rows) < 100:
                    break
                page += 1
                # 넓은 검색어는 수백 쪽이라 한 검색어가 끝날 때만 적으면 15분 넘게 조용해져
                # 멈춤 감시에 끊기고, 다시 걸어도 같은 자리에서 또 끊긴다(2026-09-12 경기·강원·광주)
                if page % 10 == 0:
                    print(f"  …{page}페이지째", flush=True)
                polite()
            if bad:
                continue
            done.add(key)
            if len(done) % 6 == 0:
                print(f"  {bdt[:7]}까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
            ckpt["done"], ckpt["seen"] = [list(d) for d in done], [list(k) for k in seen]
            with open(CKPT, "w") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            polite()
        ckpt["done"], ckpt["seen"] = [list(d) for d in done], [list(k) for k in seen]
        with open(CKPT, "w") as cf:
            json.dump(ckpt, cf, ensure_ascii=False)
        print(f"[{kw or '전수'}] 완료 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")

if __name__ == "__main__":
    try:
        main()
    except BudgetOut as e:
        # 상한에 걸려 멈춘다. 체크포인트가 있으니 다음 실행에서 이어 받는다.
        print(f"\n■ {e} — 여기서 멈춘다. 다음 실행에서 이어 받는다.")
