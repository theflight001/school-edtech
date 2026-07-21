# 기존 refined_*.csv에 계약업체명(업체명) 컬럼 소급 채우기 — 계약번호별 API 1회 호출
# 사용: NARA_KEY=<키> python3 enrich_vendors.py   (체크포인트 지원, 중단 후 재실행 가능)
import csv, glob, json, os, sys, time, urllib.request, urllib.parse

BASE = "https://apis.data.go.kr/1230000/ao/CntrctInfoService/getCntrctInfoList"
KEY = os.environ.get("NARA_KEY")
if not KEY:
    sys.exit("NARA_KEY 환경변수 필요")

def vendor_of(no, div):
    op = "Thng" if div == "물품" else "Servc"
    params = {"serviceKey": KEY, "inqryDiv": 2, "untyCntrctNo": no,
              "numOfRows": 3, "pageNo": 1, "type": "json"}
    url = f"{BASE}{op}?" + urllib.parse.urlencode(params)
    backoff = [10, 30, 60, 120]
    for attempt in range(len(backoff) + 1):
        try:
            with urllib.request.urlopen(url, timeout=30) as res:
                d = json.load(res)
            items = d["response"]["body"].get("items") or []
            if not items:
                return ""
            parts = (items[0].get("corpList") or "").strip("[]").split("^")
            return parts[3] if len(parts) > 3 else ""
        except Exception:
            if attempt == len(backoff):
                return ""
            time.sleep(backoff[attempt])

for path in sorted(glob.glob("refined_*.csv")):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if not rows or "업체명" in rows[0]:
        print(f"[skip] {path}")
        continue
    print(f"[처리] {path}: {len(rows)}건")
    for i, r in enumerate(rows):
        r["업체명"] = vendor_of(r["계약번호"], r.get("구분", "물품"))
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(rows)}", flush=True)
        time.sleep(1.2)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[완료] {path}")
print("전체 완료 — python3 build_data.py 로 재빌드할 것")
