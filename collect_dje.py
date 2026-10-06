# 대전광역시교육청 계약체결현황 수집기 — 학교 계약 (수의·입찰 모두 공개)
# 사용: python3 collect_dje.py [--keyword-file edzip_brand_keywords.txt] [--years 2023,2024,2025,2026]
# 주의: 목록의 계약명·기관명은 화면용으로 잘려 나오고 원문은 title 속성에 들어 있다.
#       (제품명이 잘린 뒷부분에 있는 경우가 많아 title을 반드시 써야 한다)
#       계약상대자만 title이 없어 상세(InfoView04.do)를 행마다 한 번 더 부른다.
import argparse, csv, html, json, os, re, time, urllib.parse, urllib.request

# 같은 시스템(InfoList04.do)을 쓰는 시도를 함께 다룬다 — 대전·충남
# (충남은 계약상대자가 목록에 이미 나와 상세를 부르지 않아도 된다)
OFFICES = {
    "대전": {"base": "https://www.dje.go.kr/clean/contract/", "list_q": "?m=0601&s=contractInfo",
             "view_q": "menuID=0601&m=0601&s=contractInfo", "targ": "대전광역시교육청",
             "out": "dje_candidates.csv", "ckpt": ".ckpt_dje.json", "vendor_col": None},
    "충남": {"base": "https://www.cne.go.kr/contract/", "list_q": "?m=050204&s=cne&pageInfo=Y",
             "view_q": "menuID=050204&m=050204&s=cne", "targ": "",
                          # 충남 목록의 계약상대자는 title 없이 잘려 나온다 — 대전과 같이 상세에서 원문을 가져온다
             "out": "충남_candidates.csv", "ckpt": ".ckpt_충남.json", "vendor_col": None},
}
OFFICE = "대전"                                   # main()에서 --office로 바꾼다
BASE = OFFICES[OFFICE]["base"]
LIST = BASE + "InfoList04.do" + OFFICES[OFFICE]["list_q"]
VIEW = BASE + "InfoView04.do"
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


class Rejected(Exception):
    """서버가 이 요청을 거부했다(400/403/409 …). 2026-09-29 확인: 409는 IP·세션이 아니라 **검색어**에 붙는다
    ('Net Class'는 어떤 IP·새 세션에서도 409, '소프트웨어'는 같은 자리에서 OK). 재시도·세션 재생성 없이 건너뛴다."""


class BudgetOut(Exception):
    """이번 실행에서 받기로 한 양을 다 썼다 — 체크포인트를 남기고 곱게 끝낸다"""


def polite():
    """요청 사이 간격 — 기계처럼 일정하면 더 눈에 띈다. 조금씩 흔든다."""
    _req_used[0] += 1
    if _req_used[0] > MAXREQ:
        raise BudgetOut(f"이번 실행 상한 {MAXREQ:,}회를 다 썼다")
    time.sleep(SPACING * _rnd.uniform(0.8, 1.4))
# ───────────────────────────────────────────────────────────────
OUT = OFFICES[OFFICE]["out"]
CKPT = OFFICES[OFFICE]["ckpt"]
FIELDS = ["회계연도", "기관명", "계약명", "계약일", "계약금액", "계약방법", "계약상대자", "키워드"]

DEFAULT_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                    "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료",
                    "챗봇", "메타버스", "코딩", "AIDT", "클래스팅", "패들렛", "캔바"]
EXCLUDE = re.compile(r"전세버스|버스 ?임차|차량 ?임차|숙박|수송|캠프|여행|급식|간식|도시락|"
                     r"청소|방역|소독|교복|졸업앨범|정수기|승강기")
RISKY = re.compile(r"\b(and|or|not|select|union|insert|update|delete|where|from|drop|exec)\b", re.I)

# ── 세션(쿠키)을 파일에 이어 쓴다 ──────────────────────────────────────────
# 2026-09-27~29 관찰: 같은 IP에서 세션(쿠키)을 새로 만든 직후의 요청이 409로 거부된다(확인 요청 OK →
# 19분 뒤 새 세션의 첫 요청 409). 서버나 웹방화벽이 IP당 살아 있는 세션을 하나로 보는 듯하다.
# 그래서 쿠키를 cookies.txt에 저장해 확인 요청·수집기·다음 실행이 한 세션을 이어 쓰고,
# 409가 나도 곧바로 새 세션을 만들지 않는다(req_retry 참고).
COOKIES = "cookies.txt"
_opener = None
_sess = {"t": 0.0, "n": 0}          # 세션 시작 시각·세션에서 보낸 요청 수 (로그용)
def opener(new=False):
    global _opener
    if _opener is None or new:
        import http.cookiejar
        cj = http.cookiejar.MozillaCookieJar(COOKIES)
        if not new and os.path.exists(COOKIES):
            try:
                cj.load(ignore_discard=True, ignore_expires=True)
            except Exception:
                pass
        _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _opener.addheaders = [("User-Agent", UA)]
        _opener._cj = cj
        if new or len(cj) == 0:
            _opener.open(LIST, timeout=90).read()      # 세션 쿠키 확보 — 저장된 게 없을 때만
            cj.save(ignore_discard=True, ignore_expires=True)
            print(f"  세션 새로 만듦 ({time.strftime('%H:%M:%S')})", flush=True)
        else:
            print(f"  저장된 세션 이어 씀 ({COOKIES}, 쿠키 {len(cj)}개)", flush=True)
        _sess["t"], _sess["n"] = time.time(), 0
    return _opener

_first_noted = [False]
def _note_first(body):
    """첫 성공 응답을 한 번만 저장하고 <input type="hidden"> 항목을 로그에 적는다 — 서버가 폼 토큰을
    요구해서 두 번째 요청부터 409를 내는지 보려고(맥 스튜디오 요청, 2026-09-27)"""
    if _first_noted[0] or os.path.exists("first_response.html"):
        _first_noted[0] = True
        return
    _first_noted[0] = True
    with open("first_response.html", "w", encoding="utf-8") as fh:
        fh.write(body)
    hid = re.findall(r"<input\b[^>]*type=[\"']?hidden[\"']?[^>]*>", body, re.I)
    print(f"  ▣ 첫 응답 저장 first_response.html ({len(body):,}자) · hidden input {len(hid)}개", flush=True)
    for h in hid[:40]:
        name = re.search(r"name=[\"']?([^\"'\s>]+)", h, re.I)
        val = re.search(r"value=[\"']([^\"']*)[\"']", h, re.I)
        v = val.group(1) if val else ""
        shape = f"길이 {len(v)}" + (" 숫자" if v.isdigit() else " 16진" if re.fullmatch(r"[0-9a-fA-F]+", v or "x") else " 영숫자" if v.isalnum() else "")
        print(f"     hidden name={name.group(1) if name else '?'} value={v[:24]!r}{'…' if len(v)>24 else ''} ({shape})", flush=True)
    for m_ in re.findall(r"(?i)(csrf|token|_token|X-CSRF[^\s\"'<>]*)[^\n<>]{0,80}", body)[:5]:
        print(f"     본문에 token/csrf 문구: {m_[:100]!r}", flush=True)

def req_retry(target, data=None):
    # 409면 (1) 5분 뒤 같은 세션으로, (2) 25분 더 기다려 새 세션으로, (3) 30분 더 기다려 새 세션으로 묻고, 그래도 안 되면 포기.
    # 새 세션은 앞 세션이 서버에서 사라질 시간(30분)을 두고서만 만든다.
    plan = [(300, False), (1500, True), (1800, True), (None, None)]
    for wait, renew in plan:
        try:
            r = urllib.request.Request(target, data=data,
                                       headers={"User-Agent": UA, "Referer": LIST})
            body = opener().open(r, timeout=120).read().decode("utf-8", "replace")
            _sess["n"] += 1
            try:
                opener()._cj.save(ignore_discard=True, ignore_expires=True)
            except Exception:
                pass
            _note_first(body)
            return body
        except Exception as e:
            code = getattr(e, "code", None)
            if code in (400, 403, 409, 419, 440):
                raise Rejected(f"HTTP {code}")          # 검색어 거부 — 기다려도 세션을 바꿔도 같다
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초 (세션 {(time.time()-_sess['t'])/60:.0f}분째, "
                  f"세션 요청 {_sess['n']}회)", flush=True)
            time.sleep(wait)
            if renew and code in (400, 403, 409, 419, 440):
                print("  앞 세션이 사라졌을 시간 — 세션을 새로 만든다", flush=True)
                opener(new=True)

def search(keyword, year, page):
    d = {"realFsclY": "", "realCntrTargNO": "", "pageSize": "100",
         "instClssDiviEtc01": "N", "instClssDiviEtc02": "N", "fsclY": year,
         "instClssDivi": "5", "cntrInstNM": "", "cntrTargNO": OFFICES[OFFICE]["targ"],
         "instClssDiviEtc01CheckBox": "N", "instClssDiviEtc02CheckBox": "N",
         "estbDiv": "", "schlClssDiv": "", "cntrNM": keyword, "cntrPrtnrNM": "",
         "cntrMthdDiv": "", "searchBeginDT": "", "searchFinDT": "",
         "cntrAmt1": "", "cntrAmt2": "", "page": str(page)}
    return req_retry(LIST, urllib.parse.urlencode(d).encode())

def parse(page_html):
    """계약명·기관명은 잘린 표시 텍스트가 아니라 title 속성의 원문을 쓴다"""
    # 대전은 tbl_list 클래스를 쓰지만 충남 표에는 클래스가 없다 — 있으면 그 표만, 없으면 문서 전체를 훑는다
    m = re.search(r'<table[^>]*tbl_list.*?</table>', page_html, re.S)
    scope = m.group(0) if m else page_html
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", scope, re.S):
        tds = re.findall(r"(<td[^>]*>.*?</td>)", tr, re.S)   # title 속성까지 포함해서 잡는다
        if len(tds) < 7:
            continue
        def text(x):
            return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()
        def full(x):
            t = re.search(r'title="([^"]*)"', x)
            return html.unescape(t.group(1)).strip() if t else text(x)
        key = re.search(r"goContractView\('([^']+)','([^']+)'\)", tds[3])
        vc = OFFICES[OFFICE]["vendor_col"]
        rows.append({"회계연도": text(tds[0]), "기관명": full(tds[1]),
                     "계약방법": text(tds[2]), "계약명": full(tds[3]),
                     "계약일": text(tds[4]).replace("/", "-"),
                     "계약금액": text(tds[5]).replace(",", ""),
                     "계약상대자": full(tds[vc]) if vc is not None and len(tds) > vc else "",
                     "_key": key.groups() if key else None})
    return rows

def vendor_of(fscl_y, targ_no):
    """목록에는 계약상대자가 잘려 나와 상세에서 원문을 가져온다"""
    url = (f"{VIEW}?{OFFICES[OFFICE]['view_q']}&realFsclY={urllib.parse.quote(fscl_y)}"
           f"&realCntrTargNO={urllib.parse.quote(targ_no)}&instClssDivi=5")
    s = req_retry(url)
    m = re.search(r"<th[^>]*>\s*계약상대자\s*</th>\s*<td[^>]*>(.*?)</td>", s, re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1)))).strip()

def safe_kw(k):
    if not RISKY.search(k):
        return k
    toks = [t for t in re.split(r"[\s\-–—/]+", k) if t and not RISKY.fullmatch(t)]
    return max(toks, key=len) if toks else ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--office", default="대전", choices=list(OFFICES))
    ap.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    ap.add_argument("--keyword-file")
    ap.add_argument("--years", default="2023,2024,2025,2026")
    ap.add_argument("--max-pages", type=int, default=300)
    ap.add_argument("--no-vendor", action="store_true", help="상세 조회를 건너뛴다(빠름, 업체명 없음)")
    a = ap.parse_args()
    global OFFICE, BASE, LIST, VIEW, OUT, CKPT
    OFFICE = a.office
    BASE = OFFICES[OFFICE]["base"]
    LIST = BASE + "InfoList04.do" + OFFICES[OFFICE]["list_q"]
    VIEW = BASE + "InfoView04.do"
    OUT, CKPT = OFFICES[OFFICE]["out"], OFFICES[OFFICE]["ckpt"]
    print(f"[{OFFICE}] {LIST}", flush=True)

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done, seen = set(ckpt["done"]), set(tuple(k) for k in ckpt["seen"])
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
    years = a.years.split(",")
    print(f"검색어 {len(kws)}종 × 회계연도 {len(years)}개 = {len(kws)*len(years)}조합", flush=True)
    kept = req_n = 0
    rejected = []                  # 서버가 거부한 검색어 — 완료로 적지 않고 파일에 남긴다
    for kw in kws:
        q = safe_kw(kw)
        if not q:
            continue
        for year in years:
            tag = f"{kw}|{year}"
            if tag in done:
                continue
            if kw in rejected:
                continue           # 한 연도에서 거부됐으면 나머지 연도도 보내지 않는다
            page = 1
            while page <= a.max_pages:
                try:
                    rows = parse(search(q, year, page))
                except Rejected as e:
                    rejected.append(kw)
                    with open("rejected_keywords.txt", "a", encoding="utf-8") as rf:
                        rf.write(f"{time.strftime('%F %T')}\t{kw}\t{year}\t{e}\n")
                    print(f"  [{kw} {year}] 거부됨({e}) — 이 검색어는 건너뜀 (rejected_keywords.txt)", flush=True)
                    polite()       # 거부도 요청 하나다 — 다음 검색어로 곧바로 넘어가지 않고 같은 간격을 둔다
                    break
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
                    vendor = r.pop("계약상대자", "") or ""
                    if not vendor and not a.no_vendor and r["_key"]:
                        try:
                            polite()                       # 상세도 한 요청이다 — 0.3초가 아니라 같은 간격으로(2026-09-27)
                            vendor = vendor_of(*r["_key"])
                            req_n += 1
                        except Exception as e:
                            print(f"  상세 실패({e}) — 업체명 없이 저장", flush=True)
                    r.pop("_key", None)
                    r["계약상대자"] = vendor
                    r["키워드"] = kw
                    w.writerow(r)
                    kept += 1
                f.flush()
                if len(rows) < 10:
                    break
                page += 1
                # 넓은 검색어는 수백 쪽이라 한 검색어가 끝날 때만 적으면 15분 넘게 조용해져
                # 멈춤 감시에 끊기고, 다시 걸어도 같은 자리에서 또 끊긴다(2026-09-12 경기·강원·광주)
                if page % 10 == 0:
                    print(f"  …{page}페이지째", flush=True)
                polite()
            if kw in rejected:
                continue           # 거부된 칸은 완료로 적지 않는다(체크포인트도 그대로)
            done.add(tag)
            ckpt["done"], ckpt["seen"] = sorted(done), [list(k) for k in seen]
            with open(CKPT + ".tmp", "w") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            os.replace(CKPT + ".tmp", CKPT)
            print(f"[{kw} {year}] {page}페이지까지 · 누적 {kept}건 (요청 {req_n}회)", flush=True)
            # 검색어(칸) 하나를 끝낼 때도 쉰다 — 쪽을 넘길 때만 쉬면 한 쪽짜리 검색어가 이어질 때 요청이 2~6초 간격으로 나간다(2026-09-21)
            polite()
    f.close()
    print(f"\n완료 — 요청 {req_n}회, 학교 계약 {kept}건 → {OUT}")
    if rejected:
        print(f"   ※ 서버가 거부한 검색어 {len(rejected)}종 (rejected_keywords.txt) — 완료로 적지 않았다: {', '.join(rejected[:20])}{' …' if len(rejected)>20 else ''}")

if __name__ == "__main__":
    try:
        main()
    except BudgetOut as e:
        # 상한에 걸려 멈춘다. 체크포인트가 있으니 다음 실행에서 이어 받는다.
        print(f"\n■ {e} — 여기서 멈춘다. 다음 실행에서 이어 받는다.")
