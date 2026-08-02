# 나라장터 학교 계약 전수(nara_full_*.csv)에서 에듀테크 계약만 추려낸다.
# 사용: python3 extract_edtech.py [--out refined_full.csv] [--report]
# 판정 규칙은 build_data.py의 것을 그대로 재사용한다(태그 규칙·제외 규칙 이중 관리 방지).
import argparse, csv, glob, re, sys, collections

csv.field_size_limit(10**7)

def load_rules():
    """build_data.py에서 규칙 정의 부분만 실행해 태그·제외 함수를 가져온다."""
    src = open("build_data.py", encoding="utf-8").read()
    marker = 'rows = list(csv.reader(open(SRC'
    ns = {"__name__": "rules"}
    exec(compile(src[:src.index(marker)], "build_data_rules", "exec"), ns)
    return ns

R = load_rules()
tags_of, refine_aidt, strip_school = R["tags_of"], R["refine_aidt"], R["strip_school"]
EXCLUDE_EVENT, EDU_SERVICE, HARD_SERVICE = R["EXCLUDE_EVENT"], R["EDU_SERVICE"], R["HARD_SERVICE"]
SVC_KEEP, SPECIFIC_RULES, GENERIC_RULES = R["SVC_KEEP"], R["SPECIFIC_RULES"], R["GENERIC_RULES"]
AIDT_PUBLISHERS, AIDT_TAG = R["AIDT_PUBLISHERS"], R["AIDT_TAG"]
resolve_school = R["resolve_school"]
SPECIFIC_TAGS = {t for t, _ in SPECIFIC_RULES} | {f"{lab} {AIDT_TAG}" for lab, _ in AIDT_PUBLISHERS}
SW_BUY = re.compile(r"(?:소프트웨어|플랫폼|라이선스|라이센스|S/?W|구독권?)\s*구[입매]")

# 1차 관문: 140만 건에 규칙 150개를 다 돌릴 수는 없으므로, 신호가 하나라도 있는 건만 통과시킨다
PREGATE = re.compile("|".join(p for _, p in SPECIFIC_RULES) + "|" +
                     "|".join(p for _, p in GENERIC_RULES) +
                     r"|에듀테크|코스웨어|소프트웨어|SW|S/W|라이선스|라이센스|구독|플랫폼|"
                     r"인공지능|\bAI\b|디지털|스마트|온라인|앱\b|어플|시스템|프로그램", re.I)

# 에듀테크 맥락어 — 범주 태그만 있는 계약의 수록 여부를 가른다
EDTECH_CTX = re.compile(
    r"에듀테크|코스웨어|인공지능|\bAI\b|디지털|스마트|\bSW\b|S/W|소프트웨어|정보화|"
    r"메타버스|\bVR\b|\bXR\b|증강현실|가상현실|로봇|코딩|드론|3D ?프린|이러닝|e-?러닝|"
    r"온라인 ?수업|원격 ?수업|미래교실|스마트교실|전자칠판|태블릿|크롬북|노트북|컴퓨터실", re.I)


COVER_END = "2026-07-31"   # 나라장터 전수 수집 종료일

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="refined_full.csv")
    ap.add_argument("--report", action="store_true", help="추출만 하고 통계 출력")
    a = ap.parse_args()

    files = sorted(glob.glob("nara_full_*.csv"))
    if not files:
        sys.exit("nara_full_*.csv 없음 — collect_nara_full.py 먼저 실행")

    out_rows, seen = [], set()
    n_all = n_gate = n_tag = 0
    drop = collections.Counter()
    tagcount = collections.Counter()
    for path in files:
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            n_all += 1
            name = r.get("계약명") or ""
            key = (r.get("계약번호"), r.get("학교명"))
            if key in seen:
                continue
            seen.add(key)
            if not PREGATE.search(name):
                continue
            n_gate += 1
            if EXCLUDE_EVENT.search(name):
                drop["행사·임대·비제품"] += 1
                continue
            tags = refine_aidt(tags_of(strip_school(name, r.get("학교명", "")), ""), name, r.get("업체명", ""))
            if not tags:
                drop["태그 없음"] += 1
                continue
            has_specific = bool(SPECIFIC_TAGS & set(tags))
            # 범주 태그(인프라·기기 등)만 붙은 계약은 에듀테크 맥락이 있어야 수록한다.
            # (전국 학교의 공기청정기·가구·교복 계약까지 '인프라'로 딸려 들어오는 것을 막는다)
            if not has_specific and not EDTECH_CTX.search(name):
                drop["에듀테크 맥락 없음"] += 1
                continue
            if EDU_SERVICE.search(name) and not has_specific and not SW_BUY.search(name):
                drop["교육·연수 용역"] += 1
                continue
            if HARD_SERVICE.search(name) and not SW_BUY.search(name) and not re.search(r"플랫폼|시스템", name):
                drop["교육 서비스 계약"] += 1
                continue
            if "용역" in name and not SVC_KEEP.search(name) and not has_specific:
                drop["일반 용역"] += 1
                continue
            # 조사 기간(수집 종료일) 이후로 찍힌 계약일은 고지한 기간 밖이라 제외한다
            if (r.get("계약일") or "") > COVER_END:
                drop["조사 기간 밖(미래 계약일)"] += 1
                continue
            r = resolve_school(r)
            n_tag += 1
            for t in tags:
                tagcount[t] += 1
            r["태그"] = "|".join(tags)
            out_rows.append(r)

    fields = list(out_rows[0].keys()) if out_rows else []
    with open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    print(f"전체 {n_all:,}건 → 1차 관문 통과 {n_gate:,}건 → 에듀테크 확정 {n_tag:,}건")
    print("제외 사유:", dict(drop))
    schools = len({r["학교명"] for r in out_rows if r["학교명"]})
    print(f"학교 {schools:,}개교 · 고유 태그 {len(tagcount)}종 → {a.out}")
    print("\n태그 상위 25:")
    for t, c in tagcount.most_common(25):
        print(f"  {c:6d}건  {t}")

if __name__ == "__main__":
    main()
