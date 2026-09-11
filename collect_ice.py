# 시도교육청 계약정보공개 수집기 (에듀파인 연계 selectCntrInfoList 계열)
# 사용: python3 collect_ice.py [--office 인천|충북] [--keywords ...] [--out ...]
# 같은 화면을 쓰는 시도가 여럿이라 주소·sysId만 바꿔 재사용한다.
# 배경: 나라장터·S2B에 안 잡히는 소액 구매(수만~수십만 원)가 여기에 남는다.
#       K-에듀파인과 연계돼 자동 공개되며 로그인이 필요 없다.
# 결과: ice_candidates.csv (계약번호 대신 기관+계약명+계약일로 중복 판별)
import signal, argparse, csv, html, http.cookiejar, json, os, re, sys, time, urllib.parse, urllib.request

# 시도별: (주소, sysId, mi) — mi가 없는 곳은 빈 문자열
OFFICES = {
    "인천": ("https://www.ice.go.kr/contract/ir/selectCntrInfoList.do", "contract", "11307"),
    "충북": ("https://www.cbe.go.kr/cbe/ir/selectCntrInfoList.do", "cbe", "11608"),
    # 전남은 jne.go.kr → jge.go.kr로 넘어간다. 넘어가면서 POST 본문이 사라져
    # 검색 조건이 통째로 무시되므로 최종 주소를 직접 쓴다.
    "전남": ("https://www.jge.go.kr/main/ir/selectCntrInfoList.do", "main", ""),
    # 경기는 학교 조회 시 계약일자 시작·종료가 필수이고 한 번에 6개월까지만 된다
    # ("대용량 건수로 인하여 6개월 단위로 검색이 가능합니다"). 날짜는 20250101 형식이라야
    # 인식되고, 하이픈(2025-01-01)으로 보내면 조건이 통째로 무시돼 504가 난다.
    # --half 옵션으로 반년씩 나눠 조회한다.
    "경기": ("https://www.goe.go.kr/goe/ir/selectCntrInfoList.do", "goe", ""),
    "세종": ("https://www.sje.go.kr/sje/ir/selectCntrInfoList.do", "sje", ""),
}
URL = OFFICES["인천"][0]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
PAGE = 100          # 한 번에 받는 행 수 (경기는 서버가 10으로 고정해 --page-size로 낮춘다)
SYSID = OFFICES["인천"][1]
MI = OFFICES["인천"][2]
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

class Deadline(Exception):
    pass

def _deadline(sig, frm):
    raise Deadline("응답이 90초 넘게 끝나지 않음")

signal.signal(signal.SIGALRM, _deadline)

def fetch(keyword, page, year="ALL", st="", ed=""):
    data = {"sysId": SYSID, "currPage": str(page), "pageIndex": str(PAGE), "cmSeqNo": "",
            "schFsclY": year, "schInstClssDiv": "5",   # 5 = 학교
            "schCntrPodiv": "", "schCntrInstNm": "", "schCntrNm": keyword,
            "schStCntrDt": st, "schEdCntrDt": ed, "schCntrAmt": "", "schCntrPrtnrNm": ""}
    if MI:
        data["mi"] = MI
    req = urllib.request.Request(URL, data=urllib.parse.urlencode(data).encode(),
                                 headers={"Referer": URL + (f"?mi={MI}" if MI else "")})
    for attempt, wait in enumerate([5, 20, 60, None]):
        # 한 요청에 90초 넘게 걸리면 끊는다. timeout=60은 바이트 사이 간격만 재서, 경기 서버가 넓은
        # 검색어(에듀테크 등)에 연결을 연 채 답을 안 주면 몇십 분씩 붙잡혔다(2026-09-12).
        # 끝내 못 받은 칸은 '끝냄'으로 적지 않으므로 다음 실행에서 다시 받는다.
        signal.alarm(90)
        try:
            return opener().open(req, timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)
        finally:
            signal.alarm(0)

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
    ap.add_argument("--years", default="ALL",
                    help="회계연도를 쉼표로 (경기처럼 연도 없이 조회하면 시간 초과되는 곳에서 필요)")
    ap.add_argument("--page-size", type=int, default=0,
                    help="한 페이지 행 수 — 경기처럼 서버가 크기를 무시하는 곳은 10으로")
    ap.add_argument("--half", action="store_true",
                    help="반년(6개월) 단위로 나눠 조회 — 경기처럼 기간 제한이 있는 곳")
    a = ap.parse_args()
    global URL, SYSID, MI, CKPT, PAGE
    URL, SYSID, MI = OFFICES[a.office]
    if a.page_size:
        PAGE = a.page_size
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
    failed = set()                 # 오류로 못 받은 칸 — 완료로 적지 않는다
    kws = a.keywords.split(",")
    if a.keyword_file:
        # 파일을 주면 기본 검색어를 '더한다' — 덮어쓰면 '에듀테크·구독·코딩' 같은
        # 알짜가 통째로 빠진다(경기 2025년이 그렇게 얇아졌다: 에듀테크 2,927 → 423건).
        extra = [l.strip() for l in open(a.keyword_file, encoding="utf-8") if l.strip()]
        kws = list(dict.fromkeys(kws + extra))
    print(f"검색어 {len(kws)}종", flush=True)
    years = a.years.split(",")
    for kw in kws:
      q = safe_kw(kw)
      if not q:
          continue
      spans = [("", "")]
      if a.half:
          spans = [("0101", "0630"), ("0701", "1231")]
      for year in years:
       for si, (s1, s2) in enumerate(spans):
        st = f"{year}{s1}" if s1 else ""
        ed = f"{year}{s2}" if s2 else ""
        tag = kw if year == "ALL" else f"{kw}|{year}" + (f"|{si}" if s1 else "")
        if tag in done:
            continue
        page = 1
        while page <= a.max_pages:
            try:
                body = fetch(q, page, year, st, ed)
            except Exception as e:
                # 특정 검색어에서만 나는 오류로 전체 수집이 멈추지 않게 한다.
                # 다만 실패를 '완료'로 적으면 안 된다 — 다음 실행에서 영영 다시 안 본다.
                # (경기 2025년이 그렇게 묻혔다: 38칸이 완료로 찍혔는데 자료는 없었다)
                print(f"  [{kw}] 건너뜀 ({e})", flush=True)
                failed.add(tag)
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
            # 넓은 검색어는 수백 쪽이라 한 검색어가 끝날 때만 적으면 15분 넘게 조용해져
            # 멈춤 감시에 끊기고, 다시 걸어도 같은 자리에서 또 끊긴다(2026-09-12 경기·강원·광주)
            if page % 10 == 0:
                print(f"  …{page}페이지째", flush=True)
            polite()
        if tag not in failed:
            done.add(tag)
        ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
        with open(CKPT, "w") as cf:
            json.dump(ckpt, cf, ensure_ascii=False)
        print(f"[{tag}] {page}페이지까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {a.out}")
    if failed:
        print(f"   ※ 오류로 못 받은 칸 {len(failed):,}개 — 다음 실행에서 다시 받는다")

if __name__ == "__main__":
    try:
        main()
    except BudgetOut as e:
        # 상한에 걸려 멈춘다. 체크포인트가 있으니 다음 실행에서 이어 받는다.
        print(f"\n■ {e} — 여기서 멈춘다. 다음 실행에서 이어 받는다.")
