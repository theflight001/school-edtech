# 나라장터 학교 계약 전수 수집 (키워드 필터 없음) — 제품 단위 전수조사용 코퍼스
# 사용: NARA_KEY=<인증키> python3 collect_nara_full.py [--begin 20230101] [--end 20260731]
# 기존 collect_nara.py와 차이: 에듀테크 키워드로 거르지 않고, 수요기관이 학교인 계약을 전부 보존한다.
#   → 이후 에듀집 제품 사전(2,490종)을 로컬에서 대조해 제품별 활용 현황을 산출한다.
# 결과: nara_full_<begin>_<end>.csv (창별 파일), 체크포인트로 중단 후 재개 가능
import argparse, csv, json, os, re, sys, time, urllib.request, urllib.parse, collections
from datetime import date, timedelta

BASE = "https://apis.data.go.kr/1230000/ao/CntrctInfoService/getCntrctInfoList"
KEY = os.environ.get("NARA_KEY")
if not KEY:
    sys.exit("NARA_KEY 환경변수에 인증키를 넣어 실행할 것 (코드에 하드코딩 금지)")

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
    # serviceKey는 인코딩하지 않는다 — urlencode를 거치면 이중 인코딩돼

    # "등록되지 않은 서비스키"(403)로 거부된다

    params = {"inqryDiv": 1, "inqryBgnDt": begin + "0000",
              "inqryEndDt": end + "2359", "numOfRows": 999, "pageNo": page, "type": "json"}
    url = f"{BASE}{op}?serviceKey={KEY}&" + urllib.parse.urlencode(params)
    backoff = [10, 30, 60, 120, 240, 480]
    for attempt in range(len(backoff) + 1):
        try:
            with urllib.request.urlopen(url, timeout=90) as res:
                d = json.load(res)
            body = d["response"]["body"]
            return body.get("items") or [], int(body.get("totalCount", 0))
        except Exception as e:
            if attempt == len(backoff):
                raise
            print(f"    재시도({e}) → {backoff[attempt]}초", flush=True)
            time.sleep(backoff[attempt])

def demand_orgs(item):
    raw = item.get("dminsttList") or ""
    names = re.findall(r"\^([^^\[\]]*(?:학교|학교장))\^", raw)
    if not names and "학교" in (item.get("cntrctInsttNm") or ""):
        names = [item["cntrctInsttNm"]]
    return names

def windows(begin, end):
    b = date(int(begin[:4]), int(begin[4:6]), int(begin[6:]))
    e = date(int(end[:4]), int(end[4:6]), int(end[6:]))
    out = []
    while b <= e:
        nxt = min(b + timedelta(days=89), e)
        out.append((b.strftime("%Y%m%d"), nxt.strftime("%Y%m%d")))
        b = nxt + timedelta(days=1)
    return out

FIELDS = ["계약번호", "구분", "계약명", "계약일", "금액", "수요기관", "학교명",
          "업체명", "학교코드", "급별", "시도", "상세URL"]

def run_window(begin, end):
    out = f"nara_full_{begin}_{end}.csv"
    ckpt_path = f".ckpt_full_{begin}_{end}.json"
    if os.path.exists(out) and not os.path.exists(ckpt_path):
        print(f"[skip] {out} 완료됨")
        return 0
    ckpt = json.load(open(ckpt_path)) if os.path.exists(ckpt_path) else {"pages": {}, "rows": [], "seen": []}
    rows, seen = ckpt["rows"], set(tuple(k) for k in ckpt["seen"])
    calls = 0
    for op, div in (("Thng", "물품"), ("Servc", "용역")):
        page = ckpt["pages"].get(op, 0) + 1
        while True:
            items, total = fetch(op, begin, end, page)
            calls += 1
            for it in items:
                orgs = [o for o in demand_orgs(it) if SCHOOL_PAT.search(o)]
                if not orgs:
                    continue
                corp_parts = (it.get("corpList") or "").strip("[]").split("^")
                corp = corp_parts[3] if len(corp_parts) > 3 else ""
                for org in orgs:
                    org_clean = org.strip()
                    tokens = org_clean.split()
                    school = tokens[-1]
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
                    rows.append({
                        "계약번호": it.get("untyCntrctNo"), "구분": it.get("bsnsDivNm") or div,
                        "계약명": it.get("cntrctNm") or "", "계약일": it.get("cntrctDate"),
                        "금액": it.get("thtmCntrctAmt"), "수요기관": org_clean, "학교명": school,
                        "업체명": corp,
                        "학교코드": mm["code"] if mm else "", "급별": mm["level"] if mm else "",
                        "시도": mm["sido"] if mm else "",
                        "상세URL": it.get("cntrctDtlInfoUrl") or "",
                    })
            done = page * 999
            if page % 20 == 0 or done >= total:
                print(f"  {begin}~{end} {op} p{page}: 전체 {total}건 중 {min(done,total)}건 훑음, 학교계약 {len(rows)}", flush=True)
            ckpt["pages"][op] = page
            ckpt["rows"], ckpt["seen"] = rows, [list(k) for k in seen]
            if page % 10 == 0:
                with open(ckpt_path, "w") as f:
                    json.dump(ckpt, f, ensure_ascii=False)
            if done >= total:
                break
            page += 1
            time.sleep(1.2)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    if os.path.exists(ckpt_path):
        os.remove(ckpt_path)
    print(f"[완료] {out}: 학교 계약 {len(rows)}건 (API {calls}회)", flush=True)
    return calls

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", default="20230101")
    ap.add_argument("--end", default=date.today().strftime("%Y%m%d"))
    a = ap.parse_args()
    wins = windows(a.begin, a.end)
    print(f"전수 수집 창 {len(wins)}개 ({a.begin}~{a.end})", flush=True)
    total_calls = 0
    for b, e in wins:
        total_calls += run_window(b, e)
    print(f"\n전체 완료 — API 호출 {total_calls}회")

if __name__ == "__main__":
    main()
