# NEIS 교육정보 개방포털에서 전국 학교 기본정보를 받아 school_master.json 생성
# 사용: python3 fetch_schools.py [NEIS_KEY]  (키 없이도 동작하나, 발급 키가 있으면 인자로 전달)
import json, sys, time, urllib.request, urllib.parse

BASE = "https://open.neis.go.kr/hub/schoolInfo"
KEY = sys.argv[1] if len(sys.argv) > 1 else None
PSIZE = 1000

def fetch(page):
    params = {"Type": "json", "pIndex": page, "pSize": PSIZE}
    if KEY:
        params["KEY"] = KEY
    url = BASE + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        return json.load(res)

schools, page, total = [], 1, None
while True:
    d = fetch(page)
    if "schoolInfo" not in d:
        print(f"페이지 {page} 응답 오류: {json.dumps(d, ensure_ascii=False)[:300]}")
        break
    head, body = d["schoolInfo"][0], d["schoolInfo"][1]
    total = head["head"][0]["list_total_count"]
    rows = body["row"]
    for r in rows:
        schools.append({
            "code": r["SD_SCHUL_CODE"],
            "name": r["SCHUL_NM"],
            "level": r["SCHUL_KND_SC_NM"],          # 초등학교/중학교/고등학교/특수학교 등
            "sido": r["LCTN_SC_NM"],
            "office": r["ATPT_OFCDC_SC_NM"],
            "address": r.get("ORG_RDNMA") or "",
            "founding": r.get("FOND_SC_NM") or "",   # 공립/사립/국립
            "hsType": r.get("HS_SC_NM") or "",       # 일반고/특성화고/특목고/자율고 (고교만)
            "hsDetail": r.get("SPCLY_PURPS_HS_ORD_NM") or "",  # 특목고 계열(과학/외국어/산업수요맞춤형 등)
            "homepage": r.get("HMPG_ADRES") or "",
        })
    print(f"페이지 {page}: 누적 {len(schools)}/{total}")
    if len(schools) >= total or len(rows) < PSIZE:
        break
    page += 1
    time.sleep(0.5)

with open("school_master.json", "w", encoding="utf-8") as f:
    json.dump({"fetchedAt": "2026-07-20", "total": len(schools), "schools": schools}, f, ensure_ascii=False)

import collections
print("\n급별:", dict(collections.Counter(s["level"] for s in schools)))
print("고교 유형:", dict(collections.Counter(s["hsType"] for s in schools if s["level"] == "고등학교")))
print("school_master.json 생성 완료")
