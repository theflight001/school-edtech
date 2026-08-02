# 부산광역시교육청 계약정보공개(K-에듀파인 자동연계) 수집기 — 학교 수의계약
# 사용: python3 collect_pen.py [--begin 2023-01] [--end 2026-08] [--keywords 에듀테크,코스웨어]
# 제약: 공개 기준 100만원 이상, 검색 기간 최대 1개월 → 월 단위로 나눠 조회한다.
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request
from datetime import date

URL = "https://www.pen.go.kr/main/ir/selectPrvcntrInfoList.do?mi=31735"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SPACING = 1.2
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
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

def parse(html):
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
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
    ap.add_argument("--begin", default="2023-01")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m"))
    ap.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    ap.add_argument("--sweep", action="store_true",
                    help="키워드 없이 월별 전수 수집 — 제품명만 적힌 계약도 놓치지 않는다")
    a = ap.parse_args()

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
    print(f"월 {len(wins)}개 × {'전수 스윕' if a.sweep else f'키워드 {len(kws)}개'} = {len(wins)*len(kws)}조합", flush=True)
    kept = req_n = 0
    for kw in kws:
        for bdt, edt, year in wins:
            key = (kw, bdt)
            if key in done:
                continue
            page = 1
            while True:
                html = fetch(kw, bdt, edt, year, page)
                req_n += 1
                rows = parse(html)
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
                time.sleep(SPACING)
            done.add(key)
            if len(done) % 6 == 0:
                print(f"  {bdt[:7]}까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
            ckpt["done"], ckpt["seen"] = [list(d) for d in done], [list(k) for k in seen]
            with open(CKPT, "w") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            time.sleep(SPACING)
        ckpt["done"], ckpt["seen"] = [list(d) for d in done], [list(k) for k in seen]
        with open(CKPT, "w") as cf:
            json.dump(ckpt, cf, ensure_ascii=False)
        print(f"[{kw or '전수'}] 완료 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")

if __name__ == "__main__":
    main()
