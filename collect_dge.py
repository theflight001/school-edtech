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
SPACING = 1.0
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
    for wait in [5, 20, 60, None]:
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

    kws = [l.strip() for l in open(a.keyword_file, encoding="utf-8") if l.strip()] \
        if a.keyword_file else a.keywords.split(",")
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
                time.sleep(SPACING)
            done.add((kw, y, m))
            ckpt["done"], ckpt["seen"] = [list(d) for d in done], [list(k) for k in seen]
            with open(CKPT, "w") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            time.sleep(SPACING)
        print(f"[{kw}] 완료 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")

if __name__ == "__main__":
    main()
