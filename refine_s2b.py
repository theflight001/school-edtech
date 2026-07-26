# S2B 수집 원자료(s2b_candidates.csv) → 학교 매칭 정제(s2b_refined.csv)
# 기관명은 학교명 단독(지역 정보 없음) — 전국 유일 이름만 코드 매칭, 동명 학교는 미매칭으로 남김
import csv, json, collections, os, sys

master = json.load(open("school_master.json", encoding="utf-8"))["schools"]
by_name = collections.defaultdict(list)
for s in master:
    by_name[s["name"]].append(s)

# build_data.py와 동일한 개명 학교 대응 (옛 이름 공고 → 현재 학교)
import ast, re
src = open("build_data.py", encoding="utf-8").read()
m = re.search(r"ALIAS = (\{.*?\n\})", src, re.S)
ALIAS = ast.literal_eval(m.group(1)) if m else {}

def expand_abbrev(name):
    # 사대부고/사대부설 등 관용 약칭 → NEIS 정식 명칭
    name = name.replace("사대부설", "사범대학부설")
    for a, b in [("사대부고", "사범대학부설고등학교"), ("사대부중", "사범대학부설중학교"),
                 ("사대부초", "사범대학부설초등학교")]:
        if name.endswith(a):
            name = name[:-len(a)] + b
    return name

def reverse_suffix_match(name):
    # S2B가 지역 접두어를 뺀 경우: "해송고등학교" → 마스터 "인천해송고등학교" (전국 유일할 때만)
    hits = [c for mname, cands in by_name.items() if mname.endswith(name) and mname != name
            for c in cands]
    return hits[0] if len(hits) == 1 else None

def suffix_match(name):
    # "삼척장원초등학교" → 접두어(삼척) + 마스터 학교명(장원초등학교), 접두어가 주소·시도에 있어야 인정
    hits = []
    for mname, cands in by_name.items():
        if name.endswith(mname) and name != mname and len(mname) >= 5:
            prefix = name[:-len(mname)]
            for c in cands:
                if prefix and prefix in (c["sido"] + c["office"] + c["address"]):
                    hits.append(c)
    return hits[0] if len(hits) == 1 else None

rows = list(csv.DictReader(open("s2b_candidates.csv", encoding="utf-8-sig")))
out, matched, ambiguous, unknown = [], 0, 0, 0
for r in rows:
    org = r["기관명"].strip()
    name = expand_abbrev(ALIAS.get(org, org).replace(" ", ""))
    cands = by_name.get(name, [])
    m = cands[0] if len(cands) == 1 else None
    if not cands:
        m = suffix_match(name) or reverse_suffix_match(name)
        if m:
            name = m["name"]
    if m:
        matched += 1
    elif len(cands) > 1:
        ambiguous += 1
    else:
        unknown += 1
    out.append({
        "계약번호": r["공고번호"], "구분": r["거래구분"] or "물품",
        "계약명": r["공고명"], "계약일": r["공고일"], "금액": "",
        "수요기관": org, "학교명": name, "업체명": "",
        "학교코드": m["code"] if m else "",
        "급별": m["level"] if m else "",
        "시도": m["sido"] if m else "",
        "상세URL": "",
    })

with open("s2b_refined.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

print(f"전체 {len(out)}건 — 코드 매칭 {matched}건, 동명 미확정 {ambiguous}건, 마스터에 없음 {unknown}건")
print("→ s2b_refined.csv (build_data.py가 S2B 출처로 병합)")
