# 서울특별시교육청 '계약공개 › 계약현황 › 에듀파인연계' 수집기
# 사용: python3 collect_sen_edufine.py [--years 2020,2021]
#
# 왜 또 만드나: 서울은 '수의계약공개'(contractOpen)로 모아 왔는데 그 화면은 2021년 12월
# 이전을 갖고 있지 않다(2015년부터 달라고 해도 건수가 한 건도 안 늘었다). 그런데 같은
# 사이트의 '계약현황 › 에듀파인연계'는 회계연도가 2014년부터 있고 2020년 학교 계약만
# 256,862건이다. 수의계약공개와 달리 입찰 계약도 함께 싣는다.
#
# 한 쪽에 10줄뿐이라 전수로 훑으면 2020년만 25,687쪽(약 18시간)이다. 그래서 계약명
# 검색칸을 쓴다. 검색어는 build_data.py의 태그 규칙에서 그대로 뽑는다 — 규칙에 없는
# 낱말은 어차피 에듀테크로 판정되지 않으므로, 전수로 훑어 태그를 다는 것과 결과가 같다.
#
# 이 화면이 주지 않는 것: 계약일자와 계약상대자. 회계연도까지만 알 수 있다.
# (상세 화면에는 있지만 수십만 건을 하나씩 열 수는 없다.)
import argparse, csv, http.cookiejar, html, json, os, re, sys, time, urllib.parse, urllib.request

URL = "https://open.sen.go.kr/fus/MI000000000000000539/cntr/list0010v.do"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
OUT, CKPT = "서울에듀파인_candidates.csv", ".ckpt_서울에듀파인.json"
FIELDS = ["계약번호", "회계연도", "기관명", "계약명", "계약금액", "진행상태",
          "계약일", "구분", "계약상대자", "키워드"]
SPACING = 0.7
SCHOOL_END = re.compile(r"(초등학교|중학교|고등학교|영재학교|특수학교)$")
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")
BASE_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                 "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료", "챗봇",
                 "메타버스", "코딩", "AIDT", "태블릿", "전자칠판", "노트북", "크롬북"]

_op = None
def opener():
    global _op
    if _op is None:
        cj = http.cookiejar.CookieJar()
        _op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _op.addheaders = [("User-Agent", UA)]
        _op.open(URL, timeout=60).read()
    return _op


def fetch(page, year, kw):
    d = {"pageIndex": str(page), "cntr_targ_no": "", "ordr_fscl_y": "", "cntr_inst_nm": "",
         "cntr_amt": "", "cntr_nm": kw, "fscl_y": year, "cntr_purp_objt_div": "",
         "inst_clss_div": "5", "cntr_mthd_div": ""}          # 5 = 학교
    for wait in [5, 20, 60, 180, None]:
        try:
            r = urllib.request.Request(URL, data=urllib.parse.urlencode(d).encode(),
                                       headers={"User-Agent": UA, "Referer": URL})
            return opener().open(r, timeout=90).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)


def parse(h):
    """목록은 계약일자·계약상대자를 안 준다. 대신 상세로 가는 계약번호가 행마다 붙어 있어
    (fncDetailView) 그것을 함께 적어 둔다 — 에듀테크로 판정된 것만 나중에 상세를 채운다."""
    tb = re.findall(r"<tbody>(.*?)</tbody>", h, re.S)
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tb[0] if tb else "", re.S):
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
             for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        no = re.search(r"fncDetailView\('([^']+)'", tr)
        if len(c) >= 4 and re.fullmatch(r"\d{4}", c[0] or ""):
            out.append({"계약번호": no.group(1) if no else "", "회계연도": c[0], "기관명": c[1],
                        "계약명": c[2], "계약금액": c[3].replace(",", ""),
                        "진행상태": c[4] if len(c) > 4 else ""})
    return out


def total_of(h):
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))
    m = re.search(r"전체\s*([\d,]+)\s*건", t)
    return int(m.group(1).replace(",", "")) if m else 0


def keywords_from_rules():
    """검색어는 판정 규칙에서 그대로 뽑는다 — 규칙에 없는 말은 어차피 에듀테크가 아니다"""
    src = open("build_data.py", encoding="utf-8").read()
    ns = {"__name__": "rules"}
    exec(compile(src[:src.index("rows = list(csv.reader(open(SRC")], "rules", "exec"), ns)
    out = set(BASE_KEYWORDS)
    for group in ("SPECIFIC_RULES", "GENERIC_RULES"):
        for _t, pat in ns.get(group, []):
            for w in re.findall(r"[가-힣A-Za-z][가-힣A-Za-z0-9]{2,}", pat):
                # 정규식 부속어와 너무 짧은 말은 뺀다 — 아무 데나 걸린다
                if w.lower() in ("re", "compile", "search", "match") or len(w) < 3:
                    continue
                out.add(w)
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2020,2021")
    ap.add_argument("--keyword-file", help="줄 단위 검색어 파일 (없으면 판정 규칙에서 뽑는다)")
    ap.add_argument("--max-pages", type=int, default=400)
    a = ap.parse_args()

    kws = ([l.strip() for l in open(a.keyword_file, encoding="utf-8") if l.strip()]
           if a.keyword_file else keywords_from_rules())
    json.dump(kws, open("sen_edufine_keywords.json", "w"), ensure_ascii=False, indent=0)
    years = [y.strip() for y in a.years.split(",") if y.strip()]

    ck = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done, seen = set(ck["done"]), set(tuple(k) for k in ck["seen"])
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    print(f"검색어 {len(kws):,}개 × 회계연도 {len(years)}개 = {len(kws)*len(years):,}조합 "
          f"(이미 본 것 {len(done):,})", flush=True)
    kept = req = 0
    for yi, year in enumerate(years):
        for i, kw in enumerate(kws, 1):
            tag = f"{year}|{kw}"
            if tag in done:
                continue
            page, total = 1, None
            while page <= a.max_pages:
                h = fetch(page, year, kw)
                req += 1
                if total is None:
                    total = total_of(h)
                    if not total:
                        break
                rows = parse(h)
                for r in rows:
                    if not SCHOOL_END.search(r["기관명"]) or EXCLUDE.search(r["계약명"]):
                        continue
                    k = (r["기관명"], r["계약명"], r["계약금액"], r["회계연도"])
                    if k in seen:
                        continue
                    seen.add(k)
                    r.update({"계약일": "", "구분": "", "계약상대자": "", "키워드": kw})
                    w.writerow(r)
                    kept += 1
                if not rows or page * 10 >= total:
                    break
                page += 1
                time.sleep(SPACING)
            f.flush()
            done.add(tag)
            if i % 20 == 0:
                json.dump({"done": sorted(done), "seen": [list(k) for k in seen]},
                          open(CKPT, "w"), ensure_ascii=False)
                print(f"  [{year}] 검색어 {i}/{len(kws)} · 누적 {kept:,}건 (요청 {req:,}회)", flush=True)
            time.sleep(SPACING)
    json.dump({"done": sorted(done), "seen": [list(k) for k in seen]},
              open(CKPT, "w"), ensure_ascii=False)
    f.close()
    print(f"\n완료 — 학교 계약 {kept:,}건 (요청 {req:,}회) → {OUT}")


if __name__ == "__main__":
    main()
