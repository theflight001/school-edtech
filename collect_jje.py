# 제주특별자치도교육청 수의계약내역 수집기 — 학교 계약
# 사용: python3 collect_jje.py [--years 2023,2024,2025,2026]
# 특징: 엑셀 내보내기(eduCntrlist1Excel.jje)가 열려 있어 연도별로 전체를 한 번에 받는다.
#       목록 화면을 페이지로 긁으면 10건씩이라 수천 번 요청해야 하는데, 이쪽은 연도당 1회면 된다.
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request

BASE = "https://www.jje.go.kr"
PAGE = BASE + "/index.jje?menuCd=DOM_000000105003004000"   # 계약현황(계약상대자 포함)
EXCEL = BASE + "/user/edufine/eduCntrlist2Excel.jje"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
OUT = "제주_candidates.csv"
CKPT = ".ckpt_제주.json"
FIELDS = ["회계연도", "기관명", "계약명", "계약일", "계약금액", "계약방법", "계약상대자", "키워드"]
SPACING = 10
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
        _opener.open(PAGE, timeout=90).read()          # 세션 쿠키 확보
    return _opener

def fetch_year(year):
    d = {"fscl_y": year, "inst_clss_div": "5",         # 5 = 학교
         "cntr_inst_nm": "", "cntr_nm": "", "startDate": "", "endDate": "",
         "cntr_amt": "0", "cntr_mthd_div_nm": "", "cntr_purp_objt_div_nm": ""}
    for wait in [10, 60, 180, None]:
        try:
            req = urllib.request.Request(EXCEL, data=urllib.parse.urlencode(d).encode(),
                                         headers={"Referer": PAGE, "User-Agent": UA})
            raw = opener().open(req, timeout=600).read()
            return raw.decode("euc-kr", "replace")     # 응답이 EUC-KR이다
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

def rows_of(page_html):
    """실제 열 순서: 회계년도·계약기관·계약명·계약일자·시작일·종료일·계약금액·계약상대자·계약방법·목적물
    (머리행에는 3번째가 '계약방법구분'으로 적혀 있으나 자료는 계약명이 들어 있다 — 사이트 표 정의 오류)"""
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
             for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(c) < 8 or not re.fullmatch(r"\d{4}", c[0] or ""):
            continue                                    # 머리행 건너뛰기
        yield c

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2023,2024,2025,2026")
    a = ap.parse_args()

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done, seen = set(ckpt["done"]), set(tuple(k) for k in ckpt["seen"])
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    years = [y for y in a.years.split(",") if y not in done]
    print(f"회계연도 {len(years)}개 (엑셀 내보내기 — 연도당 요청 1회)", flush=True)
    kept = 0
    for year in years:
        s = fetch_year(year)
        n = 0
        for c in rows_of(s):
            n += 1
            name = c[2]
            if EXCLUDE.search(name):
                continue
            key = (c[1], name, c[3])
            if key in seen:
                continue
            seen.add(key)
            w.writerow({"회계연도": c[0], "기관명": c[1], "계약명": name,
                        "계약일": c[3].replace(".", "-"),
                        "계약금액": c[6].replace(",", "") if len(c) > 6 else "",
                        "계약방법": c[8] if len(c) > 8 else "",
                        "계약상대자": c[7] if len(c) > 7 else "",
                        "키워드": "(전수)"})
            kept += 1
        f.flush()
        done.add(year)
        ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
        with open(CKPT, "w") as cf:
            json.dump(ckpt, cf, ensure_ascii=False)
        print(f"[{year}] 전체 {n:,}행 → 누적 {kept:,}건", flush=True)
        time.sleep(SPACING)
    f.close()
    print(f"\n완료 — 학교 계약 {kept:,}건 → {OUT}")

if __name__ == "__main__":
    main()
