# S2B 학교장터 수의계약 전수 수집기 (엑셀 내보내기 방식)
# 사용: python3 collect_s2b_excel.py [--begin 2023-01] [--end 2026-08]
#
# 왜 이 방식인가:
#   목록 화면을 페이지 단위로 긁으면 요청이 1,000번을 넘어 안티크롤링에 걸리고,
#   검색어로 좁히면 그 낱말이 안 든 계약을 통째로 놓친다.
#   엑셀 내보내기(forwardName=list03Excel)는 검색어 없이 기간만 주면 그 기간 전체를
#   한 번의 요청으로 돌려준다 — 한 달에 6만 건 남짓, 요청 1회.
#   따라서 44개월치를 44번의 요청으로 빠짐없이 받을 수 있다.
#   지역(areaKind)을 지정해 받으면 그 파일의 계약은 모두 그 시도 학교 것이므로,
#   기관명만으로는 못 가리던 동명 학교(전국에 여럿인 '중앙초등학교' 등)를 특정할 수 있다.
# 결과: s2b_all.csv (학교 계약만 추림 — 유치원·교육청·직속기관 제외, 시도 열 포함)
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request
from datetime import date

URL = "https://www.s2b.kr/S2BNCustomer/tcmo001.do"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SPACING = 180        # 초 — 요청이 44번뿐이라 넉넉히 쉬어도 몇 시간이면 끝난다
OUT = "s2b_all.csv"
CKPT = ".ckpt_s2b_excel.json"
FIELDS = ["계약번호", "계약구분", "거래구분", "계약명", "기관명", "공고일", "계약일", "금액", "시도"]
AREAS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원",
         "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
SCHOOL_END = re.compile(r"(초등학교|중학교|고등학교|영재학교|특수학교|학교)$")

_opener = None
def session(renew=False):
    global _opener
    if _opener is None or renew:
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _opener.addheaders = [("User-Agent", UA),
                              ("Accept", "text/html,application/xhtml+xml"),
                              ("Accept-Language", "ko-KR,ko;q=0.9")]
        _opener.open(URL + "?forwardName=list03", timeout=60).read()
    return _opener

def fetch_window(bdt, edt, area):
    p = {"forwardName": "list03Excel", "pageNo": "1", "tender_num": "", "tender_step_code": "",
         "page_flag": "", "excelSection": "Y", "process_yn": "N", "search_yn": "Y",
         "tender_sep1": "1", "tender_name": "", "company_name_s": "", "tender_sep2": "2",
         "tender_date_start": bdt, "tender_date_end": edt,
         "tender_item": "", "estimate_kind": "", "areaKind": area}
    body = urllib.parse.urlencode({k: v.encode("euc-kr") for k, v in p.items()}).encode("ascii")
    for wait in [300, 900, 1800, 3600, None]:
        try:
            req = urllib.request.Request(URL, data=body, headers={
                "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded",
                "Referer": URL + "?forwardName=list03"})
            raw = session().open(req, timeout=600).read()
            s = raw.decode("cp949", "replace")
            if "Anti Web Crawling" in s[:3000] or "보안 문자" in s[:3000]:
                if wait is None:
                    raise RuntimeError("안티크롤링 차단 지속")
                print(f"  차단 감지 → 세션 재발급 후 {wait}초 대기", flush=True)
                session(renew=True)
                time.sleep(wait)
                continue
            return s
        except Exception as e:
            if wait is None:
                raise
            print(f"  요청 실패({e}) → {wait}초 대기", flush=True)
            time.sleep(wait)
            session(renew=True)

def rows_of(s):
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S):
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
             for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(c) < 8 or not re.fullmatch(r"\d+", c[0] or ""):
            continue                       # 머리행·빈 행 건너뛰기
        yield c

def windows(begin, end, span=3):
    """S2B는 3개월을 넘겨 조회할 수 없다 — 상한에 맞춰 묶어 요청 수를 줄인다"""
    y, m = map(int, begin.split("-")); ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        sy, sm = y, m
        for _ in range(span - 1):
            if (y, m) >= (ey, em):
                break
            m += 1
            if m > 12:
                y, m = y + 1, 1
        last = [31, 29 if (y % 4 == 0 and y % 100 != 0) or y % 400 == 0 else 28,
                31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
        out.append((f"{sy}{sm:02d}01", f"{y}{m:02d}{last}"))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", default="2023-01")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m"))
    a = ap.parse_args()

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": []}
    done = set(ckpt["done"])
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    wins = windows(a.begin, a.end)
    jobs = [(b, e, ar) for b, e in wins for ar in AREAS]
    todo = [j for j in jobs if f"{j[0]}|{j[2]}" not in done]
    print(f"조합 {len(jobs)}개(창 {len(wins)} × 시도 {len(AREAS)}) 중 남은 {len(todo)}개 "
          f"· 요청 간격 {SPACING}초", flush=True)
    kept = total = 0
    for bdt, edt, area in todo:
        s = fetch_window(bdt, edt, area)
        n_all = n_school = 0
        for c in rows_of(s):
            n_all += 1
            inst = c[5]
            if not SCHOOL_END.search(inst) or "유치원" in inst:
                continue                   # 학교 계약만 남긴다
            n_school += 1
            w.writerow({"계약번호": c[3], "계약구분": c[1], "거래구분": c[2], "계약명": c[4],
                        "기관명": inst, "공고일": c[6], "계약일": c[7],
                        "금액": (c[8] if len(c) > 8 else "").replace(",", ""), "시도": area})
        f.flush()
        total += n_all
        kept += n_school
        done.add(f"{bdt}|{area}")
        json.dump({"done": sorted(done)}, open(CKPT, "w"), ensure_ascii=False)
        print(f"[{bdt[:6]}~ {area}] 전체 {n_all:,}건 중 학교 {n_school:,}건 · 누적 {kept:,}건", flush=True)
        time.sleep(SPACING)
    f.close()
    print(f"\n완료 — 전체 {total:,}건 중 학교 계약 {kept:,}건 → {OUT}")

if __name__ == "__main__":
    main()
