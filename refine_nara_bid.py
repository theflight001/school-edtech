# 나라장터 입찰공고 정제 — 학교 매칭 + 에듀테크 판정
# 사용: python3 refine_nara_bid.py
# 판정 규칙은 build_data.py의 정본을 그대로 불러 쓴다(이중 관리 금지).
#
# 계약공개와 다른 점: 낙찰 전이라 계약 상대자가 없고, 금액은 기초금액이다.
# 수요기관이 '대구광역시교육청 경북기계공업고등학교'처럼 교육청 이름을 달고 오므로 교명만 남긴다.
import csv, hashlib, re, collections

csv.field_size_limit(10**7)
SRC, OUT = "nara_bid.csv", "nara_bid_refined.csv"
FIELDS = ["계약번호", "구분", "계약명", "계약일", "금액", "수요기관", "학교명",
          "업체명", "학교코드", "급별", "시도", "상세URL"]

def load_rules():
    src = open("build_data.py", encoding="utf-8").read()
    ns = {"__name__": "rules"}
    exec(compile(src[:src.index('rows = list(csv.reader(open(SRC')], "rules", "exec"), ns)
    return ns

R = load_rules()
tags_of, refine_aidt, strip_school = R["tags_of"], R["refine_aidt"], R["strip_school"]
EXCLUDE_EVENT, EDU_SERVICE, HARD_SERVICE = R["EXCLUDE_EVENT"], R["EDU_SERVICE"], R["HARD_SERVICE"]
SVC_KEEP, SPECIFIC_RULES = R["SVC_KEEP"], R["SPECIFIC_RULES"]
AIDT_PUBLISHERS, AIDT_TAG, ALIAS = R["AIDT_PUBLISHERS"], R["AIDT_TAG"], R["ALIAS"]
master_by_name, lookup_school = R["master_by_name"], R["lookup_school"]
resolve_school = R["resolve_school"]
master_by_code = {c["code"]: c for cs in master_by_name.values() for c in cs}
SPECIFIC_TAGS = {t for t, _ in SPECIFIC_RULES} | {f"{lab} {AIDT_TAG}" for lab, _ in AIDT_PUBLISHERS}
SW_BUY = re.compile(r"(?:소프트웨어|플랫폼|라이선스|라이센스|S/?W|구독권?)\s*구[입매]")
EDTECH_CTX = re.compile(
    r"에듀테크|코스웨어|인공지능|\bAI\b|디지털|스마트|\bSW\b|S/W|소프트웨어|정보화|"
    r"메타버스|\bVR\b|\bXR\b|증강현실|가상현실|로봇|코딩|드론|3D ?프린|이러닝|e-?러닝|"
    r"온라인 ?수업|원격 ?수업|미래교실|스마트교실|전자칠판|태블릿|크롬북|노트북|컴퓨터실", re.I)
SCHOOL_END = re.compile(r"(초등학교|중학교|고등학교|영재학교|특수학교)$")

def clean_school(name):
    """'대구광역시교육청 경북기계공업고등학교' → '경북기계공업고등학교'"""
    parts = (name or "").split()
    for p in reversed(parts):
        if SCHOOL_END.search(p):
            return p
    return (name or "").strip()

def main():
    out, drop = [], collections.Counter()
    matched = 0
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    for r in rows:
        # 공사 발주는 건물·설비를 짓는 계약이다 — 이름에 낀 제품·시설명이 도입 기록으로 잘못 잡힌다
        # (예: 인천영종고 "지능형과학실, 실내스크린골프연습장, 온니유클래스 구축공사")
        if (r.get("구분") or "") == "공사":
            drop["공사 발주"] += 1
            continue
        name = (r["공고명"] or "").strip()
        school = clean_school(r.get("학교명") or r.get("수요기관"))
        if not SCHOOL_END.search(school):
            drop["학교 아님"] += 1
            continue
        if EXCLUDE_EVENT.search(name):
            drop["행사·임대·비제품"] += 1
            continue
        tags = refine_aidt(tags_of(strip_school(name, school), ""), name, "")
        if not tags:
            drop["태그 없음"] += 1
            continue
        has = bool(SPECIFIC_TAGS & set(tags))
        if not has and not EDTECH_CTX.search(name):
            drop["에듀테크 맥락 없음"] += 1
            continue
        if EDU_SERVICE.search(name) and not has and not SW_BUY.search(name):
            drop["교육·연수 용역"] += 1
            continue
        if HARD_SERVICE.search(name) and not SW_BUY.search(name) and not re.search(r"플랫폼|시스템", name):
            drop["교육 서비스 계약"] += 1
            continue
        if "용역" in name and not SVC_KEEP.search(name) and not has:
            drop["일반 용역"] += 1
            continue
        # 띄어쓰기·시도 접두어가 다른 표기까지 본다 (build_data.py의 정본 대조 함수)
        # 수요기관(관할 교육청)을 근거로 동명 학교를 가린다 — build_data.py의 정본 대조를 그대로 쓴다
        rr = resolve_school({"학교명": school, "학교코드": "", "시도": "",
                             "수요기관": r.get("수요기관") or "", "계약명": name})
        if rr.get("학교코드"):
            nm, m = rr["학교명"], master_by_code[rr["학교코드"]]
        else:
            cands = lookup_school(school)
            nm = cands[0]["name"] if len(cands) == 1 else ALIAS.get(school, school)
            m = cands[0] if len(cands) == 1 else None
        if m:
            matched += 1
        key = hashlib.md5(f"{school}|{name}|{r['공고일']}".encode()).hexdigest()[:12]
        out.append({
            "계약번호": f"입찰-{key}", "구분": r.get("구분") or "물품", "계약명": name,
            "계약일": r.get("공고일", ""), "금액": r.get("기초금액", ""),
            "수요기관": r.get("수요기관", ""), "학교명": nm, "업체명": "",
            "학교코드": m["code"] if m else "", "급별": m["level"] if m else "",
            "시도": m["sido"] if m else "", "상세URL": "",
        })
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    print(f"[나라장터 입찰] 수집 {len(rows):,}건 → 에듀테크 확정 {len(out):,}건 "
          f"(학교 매칭 {matched:,}건 · {len({r['학교명'] for r in out}):,}개교) → {OUT}")
    print("   제외 사유:", dict(drop.most_common()))
    tag = collections.Counter(t for r in out for t in
                              refine_aidt(tags_of(strip_school(r["계약명"], r["학교명"]), ""), r["계약명"], ""))
    print("   태그 상위:", tag.most_common(8))

if __name__ == "__main__":
    main()
