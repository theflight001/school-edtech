# S2B 학교장터 입찰(경쟁입찰) 계약·낙찰 수집기
# 사용: python3 collect_s2b_bid.py [--begin 2020-01] [--end 2026-09] [--span 3]
#
# 왜 따로 받나: collect_s2b_excel.py는 수의계약(tcmo001.do)만 받는다. 전자칠판 대량 도입처럼
#   금액이 큰 계약은 입찰로 나가 통째로 빠져 있었다(2026-08-02 지시: 입찰도 자동으로 받을 것).
# 어디서 받나: stmo001.do — list04 '입찰 계약 내역'(계약업체·계약일·금액), list03 '낙찰 결과'(낙찰자·낙찰일·낙찰금액).
#   공고 현황(stmb001.do)은 로그인이 필요해 못 받는다. 개찰 결과(list02)는 낙찰 전이라 받지 않는다.
# 어떻게 받나: 검색 폼을 GET으로 부른다(POST도 되지만 GET이 단순하다). 1년 창은 서버가 '일시적인 장애'
#   페이지를 내므로 분기(3개월) 창으로 자른다. 입찰 계약은 분기에 몇 건 수준이라 창마다 1쪽이 보통이다.
# 예의: 요청 간격 25초±15초, 한 번 실행에 400회 상한. 차단·장애 페이지면 세션을 새로 열고 오래 쉰다.
# 결과: s2b_bid_all.csv — s2b_all.csv와 같은 열이라 refine_s2b.py에 그대로 넣는다.
#   계약구분 = '입찰(계약)' 또는 '입찰(낙찰)'. 같은 공고번호에 계약이 있으면 낙찰 줄은 싣지 않는다.
#   시도 칸은 비워 둔다(전국으로 받는다) — refine_s2b가 학교 이름으로 잇고, 동명 학교는 미특정으로 남긴다.
import argparse, csv, html, http.cookiejar, json, os, random, re, sys, time, urllib.parse, urllib.request
from datetime import date

URL = "https://www.s2b.kr/S2BNCustomer/stmo001.do"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
OUT = "s2b_bid_all.csv"
CKPT = ".ckpt_s2b_bid.json"
FIELDS = ["계약번호", "계약구분", "거래구분", "계약명", "기관명", "공고일", "계약일", "금액", "시도", "업체명"]
SPACING = float(os.environ.get("EDTECH_SPACING", "25"))
MAXREQ = int(os.environ.get("EDTECH_MAXREQ", "400"))
STAGES = {"list04": "입찰(계약)", "list03": "입찰(낙찰)"}
_req = [0]


class BudgetOut(Exception):
    pass


_opener = None
def session(renew=False):
    global _opener
    if _opener is None or renew:
        cj = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _opener.addheaders = [("User-Agent", UA), ("Accept", "text/html,application/xhtml+xml"),
                              ("Accept-Language", "ko-KR,ko;q=0.9")]
        _opener.open(URL + "?forwardName=list04", timeout=60).read()
    return _opener


def polite():
    _req[0] += 1
    if _req[0] > MAXREQ:
        raise BudgetOut(f"이번 실행 상한 {MAXREQ}회를 다 썼다")
    time.sleep(SPACING + random.uniform(-SPACING * 0.4, SPACING * 0.6))


def fetch(listname, bdt, edt, page):
    p = {"forwardName": listname, "pageNo": str(page), "tender_num": "", "tender_step_code": "", "page_flag": "",
         "tender_sep1": "1", "tender_name": "", "company_name_s": "", "tender_sep2": "1",
         "tender_date_start": bdt, "tender_date_end": edt, "tender_item": "", "city": ""}
    q = urllib.parse.urlencode({k: v.encode("euc-kr") for k, v in p.items()})
    for wait in [300, 900, 1800, None]:
        polite()
        try:
            req = urllib.request.Request(URL + "?" + q, headers={"Referer": URL + "?forwardName=" + listname})
            s = session().open(req, timeout=120).read().decode("cp949", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  요청 실패({e}) → {wait}초 뒤 다시", flush=True)
            time.sleep(wait)
            continue
        if "Anti Web Crawling" in s[:3000] or "보안 문자" in s[:3000] or "일시적인 장애" in s[:4000]:
            if wait is None:
                raise RuntimeError("차단·장애 페이지가 이어진다")
            print(f"  차단·장애 페이지 → 세션 재발급 후 {wait}초 대기", flush=True)
            session(renew=True)
            time.sleep(wait)
            continue
        return s
    return ""


def cell(x):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).replace("\xa0", " ").strip()


def parse(s):
    """한 기록이 <tr> 둘로 나뉜다(rowspan). 첫 줄: NO·공고번호·분류·공고명·업체, 둘째 줄: 기관명·공고일·계약(낙찰)일·금액"""
    out = []
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S)
    for i, tr in enumerate(trs):
        m = re.search(r"f_detail\('([^']+)'\)", tr)
        if not m or i + 1 >= len(trs):
            continue
        a = [cell(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        b = [cell(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", trs[i + 1], re.S)]
        if len(a) < 5 or len(b) < 4:
            continue
        out.append({"공고번호": m.group(1), "거래구분": a[2], "계약명": a[3], "업체명": a[4],
                    "기관명": b[0], "공고일": b[1][:10], "계약일": b[2][:10],
                    "금액": b[3].replace(",", "").replace(" ", "")})
    pages = sorted({int(x) for x in re.findall(r"goList\('?(\d+)'?\)", s)})
    return out, pages


def windows(begin, end, span):
    y, m = map(int, begin.split("-")); ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        y2, m2 = y, m + span - 1
        while m2 > 12:
            y2, m2 = y2 + 1, m2 - 12
        if (y2, m2) > (ey, em):
            y2, m2 = ey, em
        last = [31, 29 if y2 % 4 == 0 and (y2 % 100 != 0 or y2 % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m2 - 1]
        out.append((f"{y}{m:02d}01", f"{y2}{m2:02d}{last:02d}"))
        y, m = y2, m2 + 1
        if m > 12:
            y, m = y + 1, 1
    return out


def save_all(rows):
    """공고번호별로 계약 줄을 우선하고, 계약이 없는 공고만 낙찰 줄을 싣는다. 파일은 통째로 다시 쓴다(양이 적다)."""
    best = {}
    for r in rows.values():
        k = r["계약번호"]
        if k not in best or r["계약구분"] == "입찰(계약)":
            best[k] = r
    with open(OUT + ".tmp", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(best.values(), key=lambda x: (x["계약일"], x["계약번호"])):
            w.writerow(r)
    os.replace(OUT + ".tmp", OUT)
    return len(best)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", default="2020-01")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m"))
    ap.add_argument("--span", type=int, default=3)
    ap.add_argument("--lists", default="list04,list03")
    a = ap.parse_args()
    ckpt = json.load(open(CKPT, encoding="utf-8")) if os.path.exists(CKPT) else {"done": [], "rows": {}}
    done = set(ckpt["done"])
    rows = ckpt.get("rows", {})               # "공고번호|단계" → 행
    for k, r in rows.items():                 # 첫 판(2026-09-15)은 계약번호 칸을 비워 저장했다 — 열쇠에서 되살린다
        r["계약번호"] = r.get("계약번호") or k.split("|")[0]
    wins = windows(a.begin, a.end, a.span)
    todo = [(l, b, e) for l in a.lists.split(",") for b, e in wins if f"{l}|{b}|{e}" not in done]
    print(f"창 {len(wins)}개 × 목록 {len(a.lists.split(','))} = {len(wins) * len(a.lists.split(','))}조합, 남은 {len(todo)}개 · 간격 {SPACING}초 · 상한 {MAXREQ}회", flush=True)
    try:
        for l, b, e in todo:
            page, got = 1, 0
            while True:
                s = fetch(l, b, e, page)
                recs, pages = parse(s)
                for r in recs:
                    r["계약번호"], r["계약구분"], r["시도"] = r["공고번호"], STAGES[l], ""
                    rows[f"{r['공고번호']}|{STAGES[l]}"] = {k: r.get(k, "") for k in FIELDS}
                got += len(recs)
                if page >= (max(pages) if pages else 1):
                    break
                page += 1
            done.add(f"{l}|{b}|{e}")
            ckpt["done"], ckpt["rows"] = sorted(done), rows
            with open(CKPT + ".tmp", "w", encoding="utf-8") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            os.replace(CKPT + ".tmp", CKPT)
            n = save_all(rows)
            print(f"[{STAGES[l]} {b}~{e}] {got}건 (쪽 {page}) · 누적 공고 {n}건 (요청 {_req[0]}회)", flush=True)
    except BudgetOut as e:
        print(f"멈춤: {e} — 체크포인트로 이어 받는다", flush=True)
        sys.exit(0)
    print(f"끝 · 공고 {save_all(rows)}건 → {OUT}", flush=True)


if __name__ == "__main__":
    main()
