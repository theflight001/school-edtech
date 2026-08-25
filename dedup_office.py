# 나라장터 교육청 수집 중복 걷어내기 — 504로 죽었다 되살아나면 기억이 되감겨
# 같은 계약이 여러 번 적힌다(2026-08에 20만 행이 겹쳤다). 정제 전에 한 번 훑는다.
import csv, os, sys

SRC, KEY = "nara_office.csv", ("계약번호", "수요기관")
if not os.path.exists(SRC):
    sys.exit(0)
csv.field_size_limit(10 ** 7)
rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
if not rows:
    sys.exit(0)
seen, out = set(), []
for r in rows:
    k = tuple(r.get(c, "") for c in KEY)
    if k in seen:
        continue
    seen.add(k)
    out.append(r)
if len(out) != len(rows):
    with open(SRC, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(out)
print(f"{SRC}: {len(rows):,} → {len(out):,}행 (중복 {len(rows)-len(out):,} 걷어냄)")
