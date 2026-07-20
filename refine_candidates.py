# 수집된 후보 CSV의 수요기관명을 정제해 NEIS 학교코드 재매칭 + 초·중·고·영재학교만 남김
# 사용: python3 refine_candidates.py candidates_20260620_20260720.csv
import csv, json, re, sys, collections

SIDO_HINT = [("서울", "서울"), ("부산", "부산"), ("대구", "대구"), ("인천", "인천"),
             ("광주", "광주"), ("대전", "대전"), ("울산", "울산"), ("세종", "세종"),
             ("경기", "경기"), ("강원", "강원"), ("충청북", "충청북"), ("충북", "충청북"),
             ("충청남", "충청남"), ("충남", "충청남"), ("전라북", "전라북"), ("전북", "전라북|전북"),
             ("전라남", "전라남"), ("전남", "전라남"), ("경상북", "경상북"), ("경북", "경상북"),
             ("경상남", "경상남"), ("경남", "경상남"), ("제주", "제주")]
LEVEL_END = re.compile(r"(초등학교|중학교|고등학교|영재학교)$")

master = json.load(open("school_master.json", encoding="utf-8"))["schools"]
by_name = collections.defaultdict(list)
for s in master:
    by_name[s["name"]].append(s)

def match(org):
    tokens = org.split()
    clean = tokens[-1]
    if "대학" in clean or not LEVEL_END.search(clean):
        return None, None
    cands = by_name.get(clean, [])
    if len(cands) == 1:
        return clean, cands[0]
    hint = " ".join(tokens[:-1])
    for kw, pat in SIDO_HINT:
        if kw in hint:
            f = [c for c in cands if re.match(pat, c["sido"])]
            if len(f) == 1:
                return clean, f[0]
            break
    return clean, None  # 학교이긴 하나 코드 미확정

src = sys.argv[1]
rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
kept, dropped = [], 0
for r in rows:
    clean, m = match(r["수요기관"])
    if clean is None:
        dropped += 1
        continue
    r["학교명"] = clean
    r["학교코드"] = m["code"] if m else ""
    r["급별"] = m["level"] if m else ""
    r["시도"] = m["sido"] if m else ""
    kept.append(r)

out = src.replace("candidates", "refined")
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(kept[0].keys()))
    w.writeheader()
    w.writerows(kept)

lv = collections.Counter(r["급별"] or "코드미확정" for r in kept)
schools = len({r["학교명"] for r in kept})
print(f"원본 {len(rows)}건 → 초·중·고·영재 {len(kept)}건 (대학·특수 등 제외 {dropped}건), 학교 {schools}개교 → {out}")
print("급별:", dict(lv.most_common()))
top = collections.Counter(r["학교명"] for r in kept)
print("계약 많은 학교:", top.most_common(8))
