# 기존 활용사례 DB의 학교명을 NEIS 학교 마스터에 매칭 → 학교코드 부여 리포트
import csv, json, collections, re

master = json.load(open("school_master.json", encoding="utf-8"))["schools"]
by_name = collections.defaultdict(list)
for s in master:
    by_name[s["name"]].append(s)

# DB 지역 첫 토큰 → NEIS 시도명 대조용 접두어
SIDO_PREFIX = {"서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천", "광주": "광주",
               "대전": "대전", "울산": "울산", "세종": "세종", "경기": "경기", "강원": "강원",
               "충북": "충청북", "충남": "충청남", "전북": "전라북|전북", "전남": "전라남",
               "경북": "경상북", "경남": "경상남", "제주": "제주"}

rows = list(csv.reader(open("db_export.csv", encoding="utf-8-sig")))
data = [[c.strip() for c in r] for r in rows[3:] if len(r) > 4 and r[0].strip()]

def match(name, region):
    cands = by_name.get(name, [])
    if not cands:
        return None, "미매칭"
    if len(cands) == 1:
        return cands[0], "정확"
    tok = region.split()[0] if region else ""
    pat = SIDO_PREFIX.get(tok)
    if pat:
        filtered = [c for c in cands if re.match(pat, c["sido"])]
        if len(filtered) == 1:
            return filtered[0], "지역으로 판별"
    return cands, "동명 다수"

results = {}
for r in data:
    name, region = r[1], r[3]
    if name not in results:
        results[name] = (match(name, region), region)

ok = sum(1 for (m, st), _ in results.values() if st in ("정확", "지역으로 판별"))
print(f"고유 학교명 {len(results)}개 중 매칭 {ok}개")
print("\n--- 미매칭 학교명 ---")
for name, ((m, st), region) in sorted(results.items()):
    if st == "미매칭":
        print(f"  {name} ({region})")
print("\n--- 동명 다수(지역으로도 판별 불가) ---")
for name, ((m, st), region) in sorted(results.items()):
    if st == "동명 다수":
        opts = ", ".join(f"{c['sido']}({c['code']})" for c in m)
        print(f"  {name} [DB지역: {region}] → 후보: {opts}")

# 지역 불일치 12건: DB의 지역 vs NEIS 마스터의 실제 소재지
conflicts = ["경기모바일과학고등학교", "한국에너지마이스터고등학교", "전남기술과학고등학교",
             "경기영상과학고등학교", "동아마이스터고등학교", "창의경영고등학교",
             "한국문화영상고등학교", "신일비즈니스고등학교", "경일관광경영고등학교",
             "충남기계공업고등학교", "경기경영고등학교", "경상공업고등학교"]
print("\n--- 지역 불일치 12건의 NEIS 실제 소재지 ---")
db_regions = collections.defaultdict(set)
for r in data:
    db_regions[r[1]].add(r[3])
for name in conflicts:
    cands = by_name.get(name, [])
    neis = "; ".join(f"{c['sido']} {c['address']}" for c in cands) or "NEIS에 없음"
    print(f"  {name}\n    DB 기재: {sorted(db_regions[name])}\n    NEIS: {neis}")
