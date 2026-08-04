# 시도교육청 계약공개 수집분 정제 — 학교 매칭 + 에듀테크 판정 (시도 공통)
# 사용: python3 refine_office.py [인천 부산 대구 ...]   (생략하면 수집 파일이 있는 시도 전부)
# 판정 규칙은 build_data.py의 정본을 그대로 불러 쓴다(이중 관리 금지).
import csv, hashlib, re, sys, collections

csv.field_size_limit(10**7)

# 시도별: (수집 파일, 결과 파일, 교명에 붙는 시도 접두어, 마스터 시도명 정규식)
# 광주·전남은 마스터에 '전남광주통합특별시(광주)' 형태라 접두어 비교가 통하지 않는다
OFFICES = {
    "인천": ("ice_candidates.csv", "ice_refined.csv", "인천", r"인천"),
    "부산": ("pen_candidates.csv", "pen_refined.csv", "부산", r"부산"),
    "대구": ("dge_candidates.csv", "dge_refined.csv", "대구", r"대구"),
    "광주": ("gen_candidates.csv", "gen_refined.csv", "광주", r".*\(광주\)"),
    "대전": ("dje_candidates.csv", "dje_refined.csv", "대전", r"대전"),
}

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
master_by_name = R["master_by_name"]
SPECIFIC_TAGS = {t for t, _ in SPECIFIC_RULES} | {f"{lab} {AIDT_TAG}" for lab, _ in AIDT_PUBLISHERS}
SW_BUY = re.compile(r"(?:소프트웨어|플랫폼|라이선스|라이센스|S/?W|구독권?)\s*구[입매]")
EDTECH_CTX = re.compile(
    r"에듀테크|코스웨어|인공지능|\bAI\b|디지털|스마트|\bSW\b|S/W|소프트웨어|정보화|"
    r"메타버스|\bVR\b|\bXR\b|증강현실|가상현실|로봇|코딩|드론|3D ?프린|이러닝|e-?러닝|"
    r"온라인 ?수업|원격 ?수업|미래교실|스마트교실|전자칠판|태블릿|크롬북|노트북|컴퓨터실", re.I)

FIELDS = ["계약번호", "구분", "계약명", "계약일", "금액", "수요기관", "학교명",
          "업체명", "학교코드", "급별", "시도", "상세URL"]

def match_school(name, prefix, sido_pat):
    """해당 시도 학교 중에서 찾는다. '대구OO초' ↔ 'OO초' 표기 차이도 본다."""
    nm = ALIAS.get(name, name)
    for cand_name in (nm, nm[len(prefix):] if nm.startswith(prefix) else prefix + nm):
        cands = [c for c in master_by_name.get(cand_name, []) if re.match(sido_pat, c["sido"])]
        if len(cands) == 1:
            return cand_name, cands[0]
    return nm, None

def refine(sido):
    src, out_path, prefix, sido_pat = OFFICES[sido]
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    out, drop = [], collections.Counter()
    matched = 0
    for r in rows:
        name = (r["계약명"] or "").strip()
        school_raw = (r["기관명"] or "").strip()
        if not re.search(r"(초등학교|중학교|고등학교|영재학교|특수학교)$", school_raw):
            drop["학교 아님(유치원 등)"] += 1
            continue
        if EXCLUDE_EVENT.search(name):
            drop["행사·임대·비제품"] += 1
            continue
        school, m = match_school(school_raw, prefix, sido_pat)
        tags = refine_aidt(tags_of(strip_school(name, school), ""), name, r.get("계약상대자", ""))
        if not tags:
            drop["태그 없음"] += 1
            continue
        has_spec = bool(SPECIFIC_TAGS & set(tags))
        if not has_spec and not EDTECH_CTX.search(name):
            drop["에듀테크 맥락 없음"] += 1
            continue
        if EDU_SERVICE.search(name) and not has_spec and not SW_BUY.search(name):
            drop["교육·연수 용역"] += 1
            continue
        if HARD_SERVICE.search(name) and not SW_BUY.search(name) and not re.search(r"플랫폼|시스템", name):
            drop["교육 서비스 계약"] += 1
            continue
        if "용역" in name and not SVC_KEEP.search(name) and not has_spec:
            drop["일반 용역"] += 1
            continue
        if m:
            matched += 1
        key = hashlib.md5(f"{school_raw}|{name}|{r['계약일']}".encode()).hexdigest()[:12]
        out.append({
            "계약번호": f"{prefix}-{key}", "구분": r.get("구분") or "물품", "계약명": name,
            "계약일": r.get("계약일", ""), "금액": r.get("계약금액", ""),
            "수요기관": f"{sido}광역시교육청 {school_raw}", "학교명": school,
            "업체명": r.get("계약상대자", ""),
            "학교코드": m["code"] if m else "", "급별": m["level"] if m else "",
            "시도": m["sido"] if m else f"{sido}광역시", "상세URL": "",
        })
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    print(f"[{sido}] 수집 {len(rows)}건 → 에듀테크 확정 {len(out)}건 "
          f"(학교 매칭 {matched}건 · {len({r['학교명'] for r in out})}개교) → {out_path}")
    print("   제외 사유:", dict(drop.most_common()))
    un = collections.Counter(r["학교명"] for r in out if not r["학교코드"])
    if un:
        print("   미매칭 학교:", dict(un.most_common(8)))

def main():
    import os
    todo = sys.argv[1:] or [s for s, (src, *_) in OFFICES.items() if os.path.exists(src)]
    for sido in todo:
        refine(sido)

if __name__ == "__main__":
    main()
