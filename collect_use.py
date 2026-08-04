# 울산광역시교육청 수의계약공개방(에듀파인 자동연계) 수집기 — 학교 계약
# 사용: python3 collect_use.py [--keyword-file edzip_brand_keywords.txt]
# 특징: GET 방식이라 세션·토큰이 필요 없고, 한 페이지에 100건까지 받을 수 있다.
#       계약명이 잘리지 않고 원문 그대로 나온다. 다만 목록에 금액이 없어
#       상세(BD_selectJaai001f.do)를 행마다 한 번 더 불러 계약금액을 가져온다.
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request

BASE = "https://use.go.kr/user/edufine/"
LIST = BASE + "BD_selectJaai001fList.do"
VIEW = BASE + "BD_selectJaai001f.do"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SPACING = 1.0
OUT = "use_candidates.csv"
CKPT = ".ckpt_use.json"
FIELDS = ["기관명", "계약명", "계약일", "계약금액", "계약상대자", "키워드"]

DEFAULT_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                    "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료",
                    "챗봇", "메타버스", "코딩", "AIDT", "클래스팅", "패들렛", "캔바"]
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")
RISKY = re.compile(r"\b(and|or|not|select|union|insert|update|delete|where|from|drop|exec)\b", re.I)

def get(url):
    for wait in [5, 20, 60, 180, None]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": LIST})
            return urllib.request.urlopen(req, timeout=120).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

def search(keyword, page):
    q = {"q_rowPerPage": "100", "q_currPage": str(page), "q_sortName": "", "q_sortOrder": "",
         "q_instClCd": "5", "q_searchType": "sch001", "q_searchVal": keyword}   # 5 = 학교
    return get(LIST + "?" + urllib.parse.urlencode(q))

def parse(page_html):
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        tds = re.findall(r"(<td[^>]*>.*?</td>)", tr, re.S)
        if len(tds) < 6:
            continue
        def text(x):
            return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
        if not re.search(r"\d{4}-\d{2}-\d{2}", text(tds[5])):
            continue
        seq = re.search(r"q_ifEsbSeqNo=(\d+)[^\"']*q_ifIsSidoCd=([A-Z0-9]+)", tds[2])
        rows.append({"기관명": text(tds[4]), "계약명": text(tds[2]),
                     "계약일": text(tds[5]), "계약상대자": text(tds[3]),
                     "_seq": seq.groups() if seq else None})
    return rows

def amount_of(seq_no, sido_cd):
    """목록에 금액이 없어 상세에서 계약금액을 가져온다"""
    s = get(f"{VIEW}?q_ifEsbSeqNo={seq_no}&q_ifIsSidoCd={sido_cd}&q_instClCd=5")
    m = re.search(r"계약금액\s*</th>\s*<td[^>]*>(.*?)</td>", s, re.S)
    if not m:
        txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)))
        m2 = re.search(r"계약금액\s+([\d,]+)", txt)
        return m2.group(1).replace(",", "") if m2 else ""
    return re.sub(r"[^\d]", "", m.group(1))

def safe_kw(k):
    if not RISKY.search(k):
        return k
    toks = [t for t in re.split(r"[\s\-–—/]+", k) if t and not RISKY.fullmatch(t)]
    return max(toks, key=len) if toks else ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    ap.add_argument("--keyword-file")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--no-amount", action="store_true", help="상세 조회를 건너뛴다(빠름, 금액 없음)")
    a = ap.parse_args()

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done, seen = set(ckpt["done"]), set(tuple(k) for k in ckpt["seen"])
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    kws = [l.strip() for l in open(a.keyword_file, encoding="utf-8") if l.strip()] \
        if a.keyword_file else a.keywords.split(",")
    print(f"검색어 {len(kws)}종", flush=True)
    kept = req_n = 0
    for kw in kws:
        if kw in done:
            continue
        q = safe_kw(kw)
        if not q:
            done.add(kw)
            continue
        page = 1
        while page <= a.max_pages:
            rows = parse(search(q, page))
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
                amt = ""
                if not a.no_amount and r["_seq"]:
                    try:
                        amt = amount_of(*r["_seq"])
                        req_n += 1
                        time.sleep(0.3)
                    except Exception as e:
                        print(f"  상세 실패({e}) — 금액 없이 저장", flush=True)
                r.pop("_seq", None)
                r["계약금액"] = amt
                r["키워드"] = kw
                w.writerow(r)
                kept += 1
            f.flush()
            if len(rows) < 100:
                break
            page += 1
            time.sleep(SPACING)
        done.add(kw)
        ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
        with open(CKPT, "w") as cf:
            json.dump(ckpt, cf, ensure_ascii=False)
        print(f"[{kw}] {page}페이지까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")

if __name__ == "__main__":
    main()
