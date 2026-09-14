# 시도교육청이 직접 산 에듀테크 계약 정제 — 학교 단위가 아니라 시도 단위다.
# 사용: python3 refine_office_buy.py
#
# 왜 따로 두나: 이 서비스의 단위는 '학교 × 제품'인데 교육청 일괄 도입은 '시도 × 제품'이다.
# 계약명에 학교 이름이 없어(표본 31건 중 0건) 학교에 붙일 수 없다. 학교 수에 섞으면
# 없는 학교를 세는 셈이 되므로, 제품 화면에 따로 놓기 위한 자료만 만든다.
#
# 판정 규칙은 build_data.py의 정본을 그대로 불러 쓴다(이중 관리 금지).
import csv, re, sys, collections

SRC, OUT = "nara_office.csv", "office_refined.csv"
FIELDS = ["시도", "수요기관", "계약명", "계약일", "금액", "업체명", "구분", "태그"]
# 교육청 계약의 3분의 1은 냉난방기·전기 같은 시설 관급자재다 — 제품이 아니다
FACILITY = re.compile(r"관급자재|냉난방|공기순환|전기공사|통신공사|소방|승강기|방수|석면|창호|"
                      r"화장실|증개축|신축공사|개축|리모델링|외벽|지붕|바닥|급배수|보일러|"
                      r"태양광|CCTV|정수기|책걸상|사물함|교과용도서|복사용지")
# 교육청·교육지원청 직원이 행정에 쓰는 소프트웨어 — 본청 업무용 MS·한컴 라이선스, 시설과 AutoCAD,
# 서버 접속권(CAL), 홈페이지 DBMS, 직원 대상 연수. 학교 수업에 쓰는 에듀테크가 아니다(사용자 판정 2026-09-14).
OFFICE_ADMIN = re.compile(r"행정|업무용|본청|시설|도면|설계|서버|CAL|DBMS|홈페이지|예산|전산실|네트워크|보안|"
                          r"백업|그룹웨어|청사|직원|교육전문직")


def load_rules():
    src = open("build_data.py", encoding="utf-8").read()
    ns = {"__name__": "rules"}
    exec(compile(src[:src.index("rows = list(csv.reader(open(SRC")], "rules", "exec"), ns)
    return ns


def main():
    R = load_rules()
    tags_of, refine_aidt = R["tags_of"], R["refine_aidt"]
    EXCLUDE_EVENT, EDU_SERVICE, HARD_SERVICE = R["EXCLUDE_EVENT"], R["EDU_SERVICE"], R["HARD_SERVICE"]
    # 제품군 딱지 — GENERIC_RULES에 없는 것도 있다('SW·플랫폼'은 판정 중에 직접 붙인다).
    # app.js의 GENERIC_TAGS와 같은 목록이라야 화면과 어긋나지 않는다.
    GENERIC = {t for t, _ in R["GENERIC_RULES"]} | {
        "SW·플랫폼", "SW·플랫폼(제품명 미상)", "코스웨어(기타)", "AI·디지털 교육자료",
        "운영 부대구매", "운영 부대구매(제품 미상)"}

    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    # 나라장터는 계약을 바꿀 때마다 새 계약번호로 한 줄을 더 올린다 — 상세 주소의 ctrtNo는 같고
    # 변경 차수(ctrtChgOrd)만 다르다. 따로 세면 한 계약이 두세 건이 된다(2026-09-14: 3,291행).
    # 가장 늦은 변경 차수를 남긴다(금액이 최종 계약 금액이다). 날짜가 비면 앞 차수의 날짜를 쓴다.
    by_ctrt, rest = collections.OrderedDict(), []
    for r in rows:
        m = re.search(r"ctrtNo=([^&]+)", r.get("상세URL") or "")
        if not m:
            rest.append(r)
            continue
        by_ctrt.setdefault((r["수요기관"], m.group(1)), []).append(r)
    merged = 0
    for grp in by_ctrt.values():
        chg = lambda x: int((re.search(r"ctrtChgOrd=(\d+)", x.get("상세URL") or "") or [0, 0])[1])
        grp.sort(key=chg)
        last = dict(grp[-1])
        if not last.get("계약일"):
            last["계약일"] = next((x["계약일"] for x in reversed(grp) if x.get("계약일")), "")
        if not last.get("금액") or last["금액"] == "0":
            last["금액"] = next((x["금액"] for x in reversed(grp) if x.get("금액") not in ("", "0")), last.get("금액", ""))
        rest.append(last)
        merged += len(grp) - 1
    print(f"변경 계약을 한 건으로 합침: {merged:,}행")
    rows = rest
    out, drop_fac, drop_no = [], 0, 0
    for r in rows:
        name = (r["계약명"] or "").strip()
        if not name or FACILITY.search(name) or EXCLUDE_EVENT.search(name) or OFFICE_ADMIN.search(name):
            drop_fac += 1
            continue
        tags = refine_aidt(tags_of(name, ""), name, r.get("업체명", ""))
        # 제품군만 붙은 것(기기·SW 등)은 무엇을 샀는지 알 수 없어 화면에 놓을 값어치가 없다
        tags = [t for t in tags if t not in GENERIC]
        if not tags:
            drop_no += 1
            continue
        out.append({"시도": r.get("시도", ""), "수요기관": r["수요기관"], "계약명": name,
                    "계약일": r.get("계약일", ""), "금액": r.get("금액", ""),
                    "업체명": r.get("업체명", ""), "구분": r.get("구분", ""),
                    "태그": "|".join(tags)})
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    print(f"교육청 계약 {len(rows):,}건 → 시설·행사로 뺀 것 {drop_fac:,} · "
          f"제품 못 가린 것 {drop_no:,} · 남긴 것 {len(out):,}건 → {OUT}")
    c = collections.Counter(t for r in out for t in r["태그"].split("|"))
    print("\n제품별 (상위 20):")
    for t, n in c.most_common(20):
        sidos = {r["시도"] for r in out if t in r["태그"].split("|") and r["시도"]}
        print(f"   {t[:26]:<28}{n:>5}건 · 시도 {len(sidos)}곳")


if __name__ == "__main__":
    main()
