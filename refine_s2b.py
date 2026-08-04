# S2B 학교장터 전수(s2b_all.csv) → 에듀테크 계약만 추려 학교에 붙인다.
# 사용: python3 refine_s2b.py [--src s2b_all.csv] [--out s2b_refined.csv]
# 판정 규칙은 build_data.py의 정본을 그대로 재사용한다(이중 관리 금지).
# 기관명에 지역 정보가 없어(학교명 단독) 동명 학교는 특정하지 않고 남긴다.
import argparse, ast, collections, csv, json, re

csv.field_size_limit(10**7)

def load_rules():
    src = open("build_data.py", encoding="utf-8").read()
    ns = {"__name__": "rules"}
    exec(compile(src[:src.index('rows = list(csv.reader(open(SRC')], "rules", "exec"), ns)
    return ns

R = load_rules()
tags_of, refine_aidt, strip_school = R["tags_of"], R["refine_aidt"], R["strip_school"]
EXCLUDE_EVENT, EDU_SERVICE, HARD_SERVICE = R["EXCLUDE_EVENT"], R["EDU_SERVICE"], R["HARD_SERVICE"]
SVC_KEEP, SPECIFIC_RULES, GENERIC_RULES = R["SVC_KEEP"], R["SPECIFIC_RULES"], R["GENERIC_RULES"]
AIDT_PUBLISHERS, AIDT_TAG, ALIAS = R["AIDT_PUBLISHERS"], R["AIDT_TAG"], R["ALIAS"]
by_name = R["master_by_name"]
SPECIFIC_TAGS = {t for t, _ in SPECIFIC_RULES} | {f"{lab} {AIDT_TAG}" for lab, _ in AIDT_PUBLISHERS}
SW_BUY = re.compile(r"(?:소프트웨어|플랫폼|라이선스|라이센스|S/?W|구독권?)\s*구[입매]")

# 1차 관문: 273만 건에 규칙 150개를 다 돌릴 수 없으므로 신호가 하나라도 있는 건만 통과시킨다
PREGATE = re.compile("|".join(p for _, p in SPECIFIC_RULES) + "|" +
                     "|".join(p for _, p in GENERIC_RULES) +
                     r"|에듀테크|코스웨어|소프트웨어|SW|S/W|라이선스|라이센스|구독|플랫폼|"
                     r"인공지능|\bAI\b|디지털|스마트|온라인|앱\b|어플|시스템|프로그램", re.I)
EDTECH_CTX = re.compile(
    r"에듀테크|코스웨어|인공지능|\bAI\b|디지털|스마트|\bSW\b|S/W|소프트웨어|정보화|"
    r"메타버스|\bVR\b|\bXR\b|증강현실|가상현실|로봇|코딩|드론|3D ?프린|이러닝|e-?러닝|"
    r"온라인 ?수업|원격 ?수업|미래교실|스마트교실|전자칠판|태블릿|크롬북|노트북|컴퓨터실", re.I)

FIELDS = ["계약번호", "구분", "계약명", "계약일", "금액", "수요기관", "학교명",
          "업체명", "학교코드", "급별", "시도", "상세URL"]

def expand_abbrev(name):
    """사대부고 등 관용 약칭 → NEIS 정식 명칭"""
    name = name.replace("사대부설", "사범대학부설")
    for a, b in [("사대부고", "사범대학부설고등학교"), ("사대부중", "사범대학부설중학교"),
                 ("사대부초", "사범대학부설초등학교")]:
        if name.endswith(a):
            name = name[:-len(a)] + b
    return name

# 접두어가 붙거나 빠진 표기를 가리기 위한 색인 (273만 건을 도는 동안 매번 훑지 않도록 미리 만든다)
_by_suffix = collections.defaultdict(list)      # 마스터명이 끝에 오는 경우
for _n, _c in by_name.items():
    _by_suffix[_n].extend(_c)
_endswith_idx = collections.defaultdict(list)   # '해송고등학교' → '인천해송고등학교'
for _n, _c in by_name.items():
    for _k in range(3, min(len(_n), 12)):
        _endswith_idx[_n[-_k:]].extend(_c)

_cache = {}
def match_school(raw):
    """S2B 기관명 → 마스터 학교. 결과를 캐시해 같은 학교를 다시 계산하지 않는다."""
    if raw in _cache:
        return _cache[raw]
    nm = expand_abbrev(ALIAS.get(raw, raw).replace(" ", ""))
    cands = by_name.get(nm, [])
    res = (nm, cands[0]) if len(cands) == 1 else (nm, None)
    if not cands:
        # '삼척장원초등학교' → 접두어(삼척)가 시도·교육청·주소에 있으면 그 학교로 본다
        hit = []
        for k in range(5, len(nm)):
            for c in _by_suffix.get(nm[k:], []):
                pre = nm[:k]
                if pre and pre in (c["sido"] + c["office"] + (c.get("address") or "")):
                    hit.append(c)
            if hit:
                break
        if len(hit) == 1:
            res = (hit[0]["name"], hit[0])
        else:
            # 반대로 S2B가 접두어를 뺀 경우: '해송고등학교' → '인천해송고등학교' (전국 유일할 때만)
            back = [c for c in _endswith_idx.get(nm, []) if c["name"] != nm]
            if len(back) == 1:
                res = (back[0]["name"], back[0])
    _cache[raw] = res
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="s2b_all.csv")
    ap.add_argument("--out", default="s2b_refined.csv")
    a = ap.parse_args()

    out, drop = [], collections.Counter()
    n_all = n_gate = 0
    seen = set()
    tagcount = collections.Counter()
    with open(a.src, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            n_all += 1
            if n_all % 500000 == 0:
                print(f"  {n_all:,}건 처리 · 확정 {len(out):,}건", flush=True)
            name = (r.get("계약명") or "").strip()
            key = r.get("계약번호")
            if not name or key in seen:
                continue
            seen.add(key)
            if not PREGATE.search(name):
                continue
            n_gate += 1
            if EXCLUDE_EVENT.search(name):
                drop["행사·임대·비제품"] += 1
                continue
            school_raw = (r.get("기관명") or "").strip()
            school, m = match_school(school_raw)
            tags = refine_aidt(tags_of(strip_school(name, school), ""), name, "")
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
            if not m:
                drop["학교 특정 실패(동명·미등재)"] += 1
                continue                       # 어느 학교인지 못 가리면 수록할 수 없다
            for t in tags:
                tagcount[t] += 1
            out.append({
                "계약번호": f"S2B-{key}", "구분": r.get("거래구분") or "물품",
                "계약명": name, "계약일": r.get("계약일", ""), "금액": r.get("금액", ""),
                "수요기관": school_raw, "학교명": school, "업체명": "",
                "학교코드": m["code"], "급별": m["level"], "시도": m["sido"], "상세URL": "",
            })
    with open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    print(f"\n전체 {n_all:,}건 → 1차 관문 {n_gate:,}건 → 에듀테크 확정 {len(out):,}건")
    print("제외 사유:", dict(drop.most_common()))
    print(f"학교 {len({r['학교명'] for r in out}):,}개교 · 태그 {len(tagcount)}종 → {a.out}")
    print("\n태그 상위 20:")
    for t, c in tagcount.most_common(20):
        print(f"  {c:6d}건  {t}")

if __name__ == "__main__":
    main()
