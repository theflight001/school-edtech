# 나라장터 계약정보 수집 배치 (파일럿)
# 사용: NARA_KEY=<인증키> python3 collect_nara.py --begin 20260620 --end 20260720 [--ops Thng,Servc]
# 결과: candidates_<begin>_<end>.csv — 학교 에듀테크 계약 후보 (검증 전 원자료)
import csv, json, os, re, sys, time, urllib.request, urllib.parse, argparse, collections

BASE = "https://apis.data.go.kr/1230000/ao/CntrctInfoService/getCntrctInfoList"
KEY = os.environ.get("NARA_KEY")
if not KEY:
    sys.exit("NARA_KEY 환경변수에 인증키를 넣어 실행할 것 (코드에 하드코딩 금지)")

# 핸드오프 문서의 계약명 키워드 정규식(확장판)
KEYWORD = re.compile(
    r"AI|인공지능|에듀테크|구독|소프트웨어|라이선스|라이센스|코스웨어|플랫폼|GPT|Adobe|어도비"
    r"|디지털교과서|AIDT|Claude|클로드|Gemini|제미나이|챗봇|메타버스|코딩|SW|S/W", re.I)
# 행사·캠프 용역, 비제품 계약은 수집 단계에서 제외
EXCLUDE = re.compile(r"전세버스|임대차|숙박|수송|캠프|위탁용역|위탁 ?운영|여행")
SCHOOL_PAT = re.compile(r"(초등학교|중학교|고등학교|영재학교|학교)$")
LEVEL_END = re.compile(r"(초등학교|중학교|고등학교|영재학교)$")
SIDO_HINT = [("서울", "서울"), ("부산", "부산"), ("대구", "대구"), ("인천", "인천"),
             ("광주", "광주"), ("대전", "대전"), ("울산", "울산"), ("세종", "세종"),
             ("경기", "경기"), ("강원", "강원"), ("충청북", "충청북"), ("충북", "충청북"),
             ("충청남", "충청남"), ("충남", "충청남"), ("전라북", "전라북"), ("전북", "전라북|전북"),
             ("전라남", "전라남"), ("전남", "전라남"), ("경상북", "경상북"), ("경북", "경상북"),
             ("경상남", "경상남"), ("경남", "경상남"), ("제주", "제주")]

master = json.load(open("school_master.json", encoding="utf-8"))["schools"]
master_by_name = collections.defaultdict(list)
for s in master:
    master_by_name[s["name"]].append(s)

def fetch(op, begin, end, page):
    params = {"serviceKey": KEY, "inqryDiv": 1, "inqryBgnDt": begin + "0000",
              "inqryEndDt": end + "2359", "numOfRows": 999, "pageNo": page, "type": "json"}
    url = f"{BASE}{op}?" + urllib.parse.urlencode(params)
    backoff = [10, 30, 60, 120, 240]
    for attempt in range(len(backoff) + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as res:
                d = json.load(res)
            body = d["response"]["body"]
            return body.get("items") or [], int(body.get("totalCount", 0))
        except urllib.error.HTTPError as e:
            if attempt == len(backoff):
                raise
            wait = backoff[attempt] if e.code == 429 else 10
            print(f"  HTTP {e.code} → {wait}초 대기 후 재시도")
            time.sleep(wait)
        except Exception:
            if attempt == len(backoff):
                raise
            time.sleep(10)

def demand_orgs(item):
    # dminsttList: "[1^코드^기관명^유형^부서^담당^]" 반복 — 기관명만 추출
    raw = item.get("dminsttList") or ""
    names = re.findall(r"\^([^^\[\]]*(?:학교|학교장))\^", raw)
    if not names and "학교" in (item.get("cntrctInsttNm") or ""):
        names = [item["cntrctInsttNm"]]
    return names

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--ops", default="Thng,Servc")
    a = ap.parse_args()

    out = f"candidates_{a.begin}_{a.end}.csv"
    ckpt_path = f".ckpt_{a.begin}_{a.end}.json"
    ckpt = json.load(open(ckpt_path)) if os.path.exists(ckpt_path) else {"done_pages": {}, "rows": [], "seen": []}
    rows_out = ckpt["rows"]
    seen = set(tuple(k) for k in ckpt["seen"])
    calls = 0
    for op in a.ops.split(","):
        page, total = ckpt["done_pages"].get(op, 0) + 1, None
        while True:
            items, total = fetch(op, a.begin, a.end, page)
            calls += 1
            for it in items:
                name = it.get("cntrctNm") or ""
                orgs = demand_orgs(it)
                school_orgs = [o for o in orgs if SCHOOL_PAT.search(o)]
                if not school_orgs or not KEYWORD.search(name) or EXCLUDE.search(name):
                    continue
                for org in school_orgs:
                    org_clean = org.strip()
                    tokens = org_clean.split()
                    school = tokens[-1]
                    # 관할기관 접두어("경기도교육청 ○○고") 제거 후 초·중·고·영재만, 대학 제외
                    if "대학" in school or not LEVEL_END.search(school):
                        continue
                    key = (it.get("untyCntrctNo"), school)
                    if key in seen:
                        continue
                    seen.add(key)
                    cands = master_by_name.get(school, [])
                    mm = cands[0] if len(cands) == 1 else None
                    if not mm and len(cands) > 1:
                        hint = " ".join(tokens[:-1])
                        for kw, pat in SIDO_HINT:
                            if kw in hint:
                                f = [c for c in cands if re.match(pat, c["sido"])]
                                if len(f) == 1:
                                    mm = f[0]
                                break
                    rows_out.append({
                        "계약번호": it.get("untyCntrctNo"), "구분": it.get("bsnsDivNm"),
                        "계약명": name, "계약일": it.get("cntrctDate"),
                        "금액": it.get("thtmCntrctAmt"), "수요기관": org_clean, "학교명": school,
                        "학교코드": mm["code"] if mm else "",
                        "급별": mm["level"] if mm else "",
                        "시도": mm["sido"] if mm else "",
                        "상세URL": it.get("cntrctDtlInfoUrl") or "",
                    })
            done = page * 999
            print(f"  {op} p{page}: 전체 {total}건 중 {min(done, total)}건 훑음, 후보 누적 {len(rows_out)}", flush=True)
            ckpt["done_pages"][op] = page
            ckpt["rows"] = rows_out
            ckpt["seen"] = [list(k) for k in seen]
            with open(ckpt_path, "w") as f:
                json.dump(ckpt, f, ensure_ascii=False)
            if done >= total:
                break
            page += 1
            time.sleep(1.5)

    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()) if rows_out else ["계약번호"])
        w.writeheader()
        w.writerows(rows_out)

    lv = collections.Counter(r["급별"] or "미매칭" for r in rows_out)
    print(f"\nAPI 호출 {calls}회, 후보 {len(rows_out)}건 → {out}")
    print("급별 분포:", dict(lv))
    if os.path.exists(ckpt_path):
        os.remove(ckpt_path)

if __name__ == "__main__":
    main()
