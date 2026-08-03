# S2B 학교장터 수의계약 공고 수집기 (전수조사용)
# 사용: python3 collect_s2b.py --begin 20230101 --end 20260722 [--keywords 에듀테크,코스웨어] [--max-pages 200]
# 원칙: 모든 요청 사이 20초 간격(위반 시 CAPTCHA 위험), 체크포인트 재개 지원
# 결과: s2b_candidates.csv (공고번호+기관명 기준 중복 제거, 증분 저장)
import argparse, csv, html, json, os, random, re, sys, time, urllib.request, urllib.parse
from datetime import date, timedelta

URL = "https://www.s2b.kr/S2BNCustomer/tcmo001.do"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SPACING = 45  # 초 최소 간격 — 절대 줄이지 말 것 (여기에 무작위 지연이 더해짐)
              # 2026-08-03: 25초로는 짧은 시간 안의 두 번째 검색이 차단돼 45초로 올림
JITTER = 25   # 0~25초 무작위 추가 — 기계적으로 일정한 간격은 안티크롤링에 감지됨
OUT = "s2b_candidates.csv"
CKPT = ".ckpt_s2b.json"
FIELDS = ["공고번호", "공고명", "기관명", "공고일", "마감일", "계약구분", "거래구분", "키워드", "조회창"]

# 나라장터와 동일 취지의 키워드 세트 (S2B는 부분일치 검색)
DEFAULT_KEYWORDS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스",
                    "구독", "플랫폼", "GPT", "어도비", "디지털교과서", "교육자료",
                    "챗봇", "메타버스", "코딩"]
# "디지털교과서"는 법 개정으로 "AI 디지털 교육자료"로 명칭 변경 — 두 표기 모두 수집해야 함
# 브랜드 스윕: 공고명이 제품명만으로 된 계약("클래스팅 이용료" 등)은 위 일반 키워드로 안 잡힘
BRAND_KEYWORDS = ["AIDT", "클래스팅", "아이스크림", "AICE", "레고", "DBpia", "카피킬러",
                  "하이러닝", "바당", "매쓰플랫", "마타수학", "밀크", "넷클래스", "아이톡톡",
                  "캔바", "패들렛", "리로스쿨", "니어팟", "퀴즈앤", "엘리스", "와콤",
                  "교보문고", "마이크로비트", "코디마스터", "루디쿤", "제미나이", "클로드"]
# 행사·캠프 등 비제품 계약은 수집 단계에서 제외 (build_data.py EXCLUDE와 동일 계열)
EXCLUDE = re.compile(r"전세버스|버스 ?임차|임대차|숙박|수송|캠프|위탁용역|위탁 ?운영|여행|차량|도시락|급식|체험학습|청소|방역|소독|경비 ?용역|인쇄")
LEVEL_END = re.compile(r"(초등학교|중학교|고등학교|영재학교)$")

_last_req = [0.0]
_opener = None

def session(renew=False):
    """S2B는 세션 쿠키(WMONID·s2bncustomer) 없이 POST하면 안티크롤링에 걸린다.
    브라우저처럼 목록 페이지를 먼저 GET해 쿠키를 받아 둔다."""
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

def post(params):
    wait = SPACING + random.uniform(0, JITTER) - (time.time() - _last_req[0])
    if wait > 0:
        time.sleep(wait)
    body = urllib.parse.urlencode({k: v.encode("euc-kr") for k, v in params.items()})
    req = urllib.request.Request(URL, data=body.encode("ascii"), headers={
        "User-Agent": UA, "Referer": URL,
        "Content-Type": "application/x-www-form-urlencoded"})
    # 새벽 점검 등 장시간 장애도 버틴다: 최대 12시간까지 점점 길게 대기하며 재시도
    backoffs = [120, 300, 600, 1800] + [3600] * 11
    for attempt, backoff in enumerate(backoffs + [None]):
        try:
            raw = session().open(req, timeout=60).read()
            _last_req[0] = time.time()
        except Exception as e:
            _last_req[0] = time.time()
            if backoff is None:
                raise
            print(f"  요청 실패({e}) → {backoff}초 대기", flush=True)
            time.sleep(backoff)
            continue
        s = raw.decode("cp949", "replace")
        if "Anti Web Crawling" in s or "보안 문자" in s:
            # 안티크롤링 차단 — 사람이 풀 CAPTCHA가 아니라 '요청이 잦다'는 신호다.
            # 브라우저로는 같은 시각에도 정상 조회되므로, 사람 개입이 아니라 속도 조절이 답이다.
            if backoff is None:
                raise RuntimeError("안티크롤링 차단 지속 — 간격을 더 늘려야 함")
            # 차단 상태에서 계속 두드리면 차단이 갱신돼 영영 안 풀린다. 충분히 쉬고 세션도 새로 받는다.
            nap = max(backoff, 1800)
            print(f"  차단 감지 → 세션 재발급 후 {nap}초 대기 (재요청이 차단을 연장하므로 길게 쉰다)", flush=True)
            try:
                session(renew=True)
            except Exception as e:
                print(f"  세션 재발급 실패({e})", flush=True)
            time.sleep(nap)
            continue
        if len(raw) < 5000 or "일시적인 장애" in s:  # S2B 에러/점검 페이지
            if backoff is None:
                raise RuntimeError("S2B 에러 페이지 12시간 지속 — 중단")
            print(f"  에러 페이지 수신 → {backoff}초 대기 후 재시도", flush=True)
            time.sleep(backoff)
            continue
        return s
    raise RuntimeError("unreachable")

def search_params(kw, begin, end, page):
    return {"forwardName": "list01", "pageNo": str(page), "orderBy": "",
            "estimateCode": "", "tender_step_code": "", "page_flag": "",
            "process_yn": "N", "search_yn": "Y",
            "tender_sep1": "1", "tender_name": kw, "company_name_s": "",
            "tender_sep2": "1", "tender_date_start": begin, "tender_date_end": end,
            "tender_item": "", "estimate_kind": "", "areaKind": "전국"}

def parse_rows(s):
    rows = []
    for m in re.finditer(r"f_detail\('(\d{15})','(\d)'\)\s*;?\s*\"[^>]*>(.*?)</a>", s, re.S):
        no, kind = m.group(1), m.group(2)
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(3))).replace("&nbsp;", " ").strip()
        seg = s[m.end():m.end() + 2000]
        tds = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c))).replace("\xa0", " ").strip()
               for c in re.findall(r"<td[^>]*>(.*?)</td>", seg, re.S)]
        # [상태, 거래구분, 기관명, 공고일, 마감일, ...]
        if len(tds) >= 5:
            rows.append({"공고번호": no, "공고명": title, "거래구분": tds[1],
                         "기관명": tds[2], "공고일": tds[3], "마감일": tds[4],
                         "계약구분": "1인수의" if kind == "1" else "2인수의"})
    last = max([int(n) for n in re.findall(r"goList\((\d+)\)", s)] + [1])
    return rows, last

def windows(begin, end):
    b = date(int(begin[:4]), int(begin[4:6]), int(begin[6:]))
    e = date(int(end[:4]), int(end[4:6]), int(end[6:]))
    out = []
    while b <= e:
        nxt = min(b + timedelta(days=89), e)  # 3개월 제한 준수
        out.append((b.strftime("%Y%m%d"), nxt.strftime("%Y%m%d")))
        b = nxt + timedelta(days=1)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    ap.add_argument("--max-pages", type=int, default=200)
    a = ap.parse_args()

    kws = a.keywords.split(",")
    wins = windows(a.begin, a.end)
    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done = set(tuple(d) for d in ckpt["done"])
    seen = set(tuple(k) for k in ckpt["seen"])
    new_file = not os.path.exists(OUT)
    fout = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(fout, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    total_req = 0
    kept = 0
    print(f"창 {len(wins)}개 × 키워드 {len(kws)}개 — 요청 간격 {SPACING}초", flush=True)
    for kw in kws:
        for wb, we in wins:
            key = (kw, wb)
            if key in done:
                continue
            page, last = 1, 1
            while page <= min(last, a.max_pages):
                s = post(search_params(kw, wb, we, page))
                total_req += 1
                rows, last = parse_rows(s)
                for r in rows:
                    org = r["기관명"]
                    school = org.split()[-1] if org else ""
                    if "대학" in school or not LEVEL_END.search(school):
                        continue
                    if EXCLUDE.search(r["공고명"]):
                        continue
                    k = (r["공고번호"], school)
                    if k in seen:
                        continue
                    seen.add(k)
                    r["키워드"] = kw
                    r["조회창"] = f"{wb}~{we}"
                    w.writerow(r)
                    kept += 1
                fout.flush()
                if not rows:
                    break
                page += 1
            done.add(key)
            ckpt["done"] = [list(d) for d in done]
            ckpt["seen"] = [list(k) for k in seen]
            with open(CKPT, "w") as f:
                json.dump(ckpt, f, ensure_ascii=False)
            print(f"[{kw}] {wb}~{we}: {last}페이지, 누적 수집 {kept}건 (요청 {total_req}회)", flush=True)
    fout.close()
    print(f"\n완료 — 요청 {total_req}회, 학교 공고 {kept}건 → {OUT}")

if __name__ == "__main__":
    main()
