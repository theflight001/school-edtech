# 대구광역시교육청 수의계약내역공개 수집기 — 학교 소액 계약
# 사용: python3 collect_dge.py [--begin 2023-01] [--end 2026-08] [--keyword-file ...]
# 제약: 목록에 계약명·기관·계약일만 나오고 금액·업체는 상세 페이지에 있다 → 행마다 상세를 1회 더 부른다.
#       조회는 '연+월' 단위이고 한 페이지 최대 50건. instClssDiv=5가 학교.
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request
from datetime import date

BASE = "https://www.dge.go.kr/main/ir/"
LIST = BASE + "selectPrvcntrList.do"
VIEW = BASE + "selectPrvcntrView.do"
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
OUT = "dge_candidates.csv"
CKPT = ".ckpt_dge.json"
FIELDS = ["기관명", "계약명", "계약일", "계약금액", "계약상대자", "키워드"]

DEFAULT_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                    "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료",
                    "챗봇", "메타버스", "코딩", "AIDT", "클래스팅", "패들렛", "캔바"]
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")
# 인천과 같은 SQL 주입 방어에 걸리는 낱말은 미리 빼 둔다
RISKY = re.compile(r"\b(and|or|not|select|union|insert|update|delete|where|from|drop|exec)\b", re.I)

_opener = None
def opener():
    global _opener
    if _opener is None:
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _opener.addheaders = [("User-Agent", UA)]
        _opener.open("https://www.dge.go.kr/main/main.do", timeout=30).read()
        _opener.open(LIST + "?mi=5310", timeout=30).read()      # 세션 쿠키 확보
    return _opener

def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"Referer": LIST + "?mi=5310"})
    for wait in [30, 120, 300, None]:
        try:
            return opener().open(req, timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

def form(**kw):
    d = {"sysId": "main", "mi": "5310", "cntrTargNo": "", "cmSeqNo": "", "currPage": "1",
         "instClssDiv": "5", "cntrInstCd": "", "srchY": "", "srchM": "",
         "pageIndex": "50", "searchType": "sj", "inpSrchwrd": ""}
    d.update(kw)
    return d

def parse_list(page_html):
    """(계약명, 기관명, 계약일, cntrTargNo, cmSeqNo) 목록"""
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        m = re.search(r"selectDetailView\('([^']+)','([^']+)'\)", tr)
        if not m:
            continue
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
             for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        c = [re.sub(r"^(번호|제목|기관명|계약일자)", "", x).strip() for x in c]
        if len(c) < 4:
            continue
        out.append((c[1], c[2], c[3].replace(".", "-"), m.group(1), m.group(2)))
    return out

def parse_view(page_html):
    """상세 표에서 계약금액·업체명을 뽑는다 (계약대상자 행의 첫 칸이 업체명)"""
    amt, vendor = "", ""
    m = re.search(r"계약대상자.*?</tr>\s*<tr>(.*?)</tr>", page_html, re.S)
    if m:
        tds = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
               for x in re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), re.S)]
        if tds:
            vendor = tds[0]
    # 계약개요 행: 계약일자·계약기간·추정금액·계약금액·계약율 순서라 네 번째 칸이 계약금액
    m = re.search(r"<tr>\s*<td class=\"ac\">\d{4}\.\d{2}\.\d{2}</td>(.*?)</tr>", page_html, re.S)
    if m:
        tds = [re.sub(r"<[^>]+>", "", x).replace(",", "").strip()
               for x in re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), re.S)]
        nums = [t for t in tds if t.isdigit()]
        if len(nums) >= 2:
            amt = nums[1]
        elif nums:
            amt = nums[0]
    return amt, vendor

def months(begin, end):
    y, m = map(int, begin.split("-")); ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append((str(y), f"{m:02d}"))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out

def safe_kw(k):
    if not RISKY.search(k):
        return k
    toks = [t for t in re.split(r"[\s\-–—/]+", k) if t and not RISKY.fullmatch(t)]
    return max(toks, key=len) if toks else ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", default="2023-01")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m"))
    ap.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    ap.add_argument("--keyword-file", help="검색어를 줄 단위로 담은 파일 (에듀집 제품명 등)")
    a = ap.parse_args()

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done = set(tuple(d) for d in ckpt["done"])
    seen = set(tuple(k) for k in ckpt["seen"])
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
    wins = months(a.begin, a.end)
    print(f"검색어 {len(kws)}종 × 월 {len(wins)}개 = {len(kws)*len(wins)}조합", flush=True)
    kept = req_n = 0
    for kw in kws:
        q = safe_kw(kw)
        if not q:
            continue
        for y, m in wins:
            if (kw, y, m) in done:
                continue
            page = 1
            while True:
                body = post(LIST, form(currPage=str(page), srchY=y, srchM=m, inpSrchwrd=q))
                req_n += 1
                rows = parse_list(body)
                for name, inst, dt, targ, seq in rows:
                    if EXCLUDE.search(name):
                        continue
                    key = (inst, name, dt)
                    if key in seen:
                        continue
                    seen.add(key)
                    amt, vendor = "", ""
                    try:
                        amt, vendor = parse_view(post(VIEW, form(cntrTargNo=targ, cmSeqNo=seq,
                                                                srchY=y, srchM=m)))
                        req_n += 1
                        time.sleep(0.4)
                    except Exception as e:
                        print(f"  상세 실패({e}) — 금액·업체 없이 저장", flush=True)
                    w.writerow({"기관명": inst, "계약명": name, "계약일": dt,
                                "계약금액": amt, "계약상대자": vendor, "키워드": kw})
                    kept += 1
                f.flush()
                if len(rows) < 50:
                    break
                page += 1
                polite()
            done.add((kw, y, m))
            ckpt["done"], ckpt["seen"] = [list(d) for d in done], [list(k) for k in seen]
            with open(CKPT, "w") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            polite()
        print(f"[{kw}] 완료 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")

if __name__ == "__main__":
    try:
        main()
    except BudgetOut as e:
        # 상한에 걸려 멈춘다. 체크포인트가 있으니 다음 실행에서 이어 받는다.
        print(f"\n■ {e} — 여기서 멈춘다. 다음 실행에서 이어 받는다.")
