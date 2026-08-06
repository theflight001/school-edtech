# 에듀집 제품별 공급 회사명 수집기
# 사용: python3 collect_edzip_company.py
# 배경: 목록 API는 id·name만 주고 회사명은 상세(product/{id})의 company.name에 있다.
#       학습지원 소프트웨어 목록은 companyName이 비어 있는 행이 많지만
#       company 객체({id, name})에 이름이 들어 있다 — 이쪽을 먼저 본다.
# 결과: edzip_company.csv (제품명, 회사명, 회사ID, 출처)
import csv, json, time, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
API = "https://api.edzip.kr"
OUT = "edzip_company.csv"
SPACING = 0.15

def get(path):
    for wait in [2, 10, 30, None]:
        try:
            r = urllib.request.Request(API + path, headers={"User-Agent": UA, "Accept": "application/json"})
            return json.loads(urllib.request.urlopen(r, timeout=40).read().decode())
        except Exception as e:
            if wait is None:
                raise
            time.sleep(wait)

def items_of(d):
    x = d.get("data") if isinstance(d, dict) else d
    if isinstance(x, dict):
        x = x.get("items") or x.get("list") or x.get("data")
    return x or []

def main():
    # 1) 제품 카탈로그 전체 id
    ids, skip = [], 0
    while True:
        got = items_of(get(f"/product/search?keyword=&limit=200&skip={skip}&sortType=nameasc"))
        if not got:
            break
        ids += [(x["id"], x.get("name", "")) for x in got if x.get("id")]
        skip += 200
        print(f"  제품 목록 {len(ids)}종", flush=True)
        time.sleep(SPACING)

    # 2) 상세에서 회사명 — 여기가 목록에 없던 정보다
    rows, id2name = [], {}
    for i, (pid, pname) in enumerate(ids, 1):
        try:
            b = get(f"/product/{pid}")
            b = b.get("data") or b
            comp = b.get("company") or {}
            cname, cid = (comp.get("name") or "").strip(), comp.get("id") or b.get("companyId") or ""
            if cid and cname:
                id2name[cid] = cname
            rows.append({"제품명": b.get("name") or pname, "회사명": cname,
                         "회사ID": cid, "출처": "제품 카탈로그"})
        except Exception as e:
            print(f"  [{pname}] 상세 실패({e})", flush=True)
        if i % 200 == 0:
            print(f"  상세 {i}/{len(ids)} · 회사명 확보 {sum(1 for r in rows if r['회사명'])}", flush=True)
        time.sleep(SPACING)

    # 3) 학습지원 소프트웨어 — companyName이 비면 위에서 만든 대응표로 채운다
    skip, sw = 0, 0
    while True:
        got = items_of(get(f"/self-inspection/free?limit=200&skip={skip}"))
        if not got:
            break
        for x in got:
            comp = x.get("company") or {}          # 이름은 companyName이 아니라 여기 들어 있다
            cid = comp.get("id") or x.get("companyId") or ""
            cname = (comp.get("name") or x.get("companyName") or "").strip() or id2name.get(cid, "")
            rows.append({"제품명": x.get("productName") or "", "회사명": cname,
                         "회사ID": cid, "출처": "학습지원 소프트웨어"})
            sw += 1
        skip += 200
        print(f"  학습지원 SW {sw}종", flush=True)
        time.sleep(SPACING)

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["제품명", "회사명", "회사ID", "출처"])
        w.writeheader()
        w.writerows(rows)
    have = sum(1 for r in rows if r["회사명"])
    print(f"\n완료 — 제품 {len(rows):,}종 중 회사명 확보 {have:,}종 "
          f"({have*100//max(len(rows),1)}%) · 회사 {len({r['회사명'] for r in rows if r['회사명']}):,}곳 → {OUT}")

if __name__ == "__main__":
    main()
