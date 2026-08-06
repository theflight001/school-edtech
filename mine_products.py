# 미등록 제품명 자동 발굴 — 범주 태그로만 처리된 계약에서 제품명 후보를 캐내 근거로 검증한다.
# 사용: python3 mine_products.py [--apply]
#   (기본) 후보를 검증해 product_candidates.md 리포트만 생성
#   --apply  근거가 확실한 A등급만 mined_rules.csv에 반영 (build_data.py가 자동으로 읽음)
#
# 판정 근거 (사람 눈에 의존하지 않기 위한 기준):
#   A등급 = 에듀집 제품 사전(2,490종)에 있는 이름 → 실존 제품 확정
#   B등급 = 계약 상대 업체가 한 곳으로 쏠림(≥60%) + 3건 이상 → 특정 공급사 제품일 가능성 높음
#   C등급 = 그 외 (빈도만 높음) → 사람 확인 필요
import argparse, collections, csv, json, os, re

GENERIC = {"코스웨어(기타)", "SW·플랫폼(제품명 미상)", "로봇·교구·키트", "VR/XR 장비",
           "기기(PC·태블릿·전자칠판 등)", "인프라(교실·설비)", "드론", "3D 프린팅/CAD",
           "AI 면접시스템", "운영 부대구매(제품 미상)"}
# 제품명이 아닌 일반어·행정어 — 후보에서 제외
STOP = re.compile(
    r"^(카드|AI|SW|소프트웨어|코딩|전자칠판|노트북|로봇코딩|드론|VR|XR|수학|영어|국어|과학|"
    r"태블릿|컴퓨터|긴급|추가|변경|재공고|물품|기자재|프로그램|콘텐츠|온라인|디지털|스마트|"
    r"모니터|프린터|서버|충전함|공기청정기|정수기|책상|의자|가구|도서|교구|세트|외|등|목적|"
    r"보조금|인공지능|미래교실|로봇|정보화기기|에듀테크|제품명 미확인|수정|조달|유치원|상품권|"
    r"AIDT|EDU|CEU|LMS|PC|TV|USB|LED|CCTV|HDMI|SSD|GPU|CPU|OA|IT|ICT|STEAM|SW|HW|"
    r"MOU|NCS|KERIS|NEIS|S2B|G2B|VOD|PDF|HWP|OS|VR|AR|XR|3D|2D|AI|"
    r"협동로봇|메타버스|수업용|선택형교육)$"
    r"|^\d|^[A-Za-z0-9]{1,4}$|학교|교육청|지원청|계약|구입|구매|납품|설치|임차|대여|용역|공사|"
    r"수리|점검|예산|사업|지원|운영|활용|교실|센터|외 ?\d|,")
SW_CTX = re.compile(r"구독|라이선스|라이센스|이용권|이용료|사용료|플랫폼|소프트웨어|앱|어플|"
                    r"코스웨어|프로그램|계정|콘텐츠", re.I)

def norm(s):
    return re.sub(r"[\s·ㆍ\-_/()\[\]]+", "", (s or "")).lower()

def load_edzip():
    names = {}
    for path, col in [("edzip_products.csv", "제품명"), ("edzip_basic.csv", "제품명")]:
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            n = (r.get(col) or "").strip()
            if n:
                names.setdefault(norm(n), n)
    return names

def load_records():
    s = open("data.js", encoding="utf-8").read()
    return json.loads(s[s.index("{"):s.rindex("}") + 1])["records"]

def known_tags():
    src = open("build_data.py", encoding="utf-8").read()
    tags = set(re.findall(r'\("([^"]+)",\s+r"', src[src.index("SPECIFIC_RULES = ["):src.index("# 에듀집 등록 제품")]))
    for path in ("edzip_rules.csv", "mined_rules.csv"):
        if os.path.exists(path):
            tags |= {r["태그"] for r in csv.DictReader(open(path, encoding="utf-8-sig"))}
    return tags

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="A등급 후보를 mined_rules.csv에 반영")
    ap.add_argument("--min-count", type=int, default=3)
    a = ap.parse_args()

    edzip, recs, known = load_edzip(), load_records(), known_tags()
    known_norm = {norm(t) for t in known}

    cand = collections.defaultdict(lambda: {"n": 0, "vendors": collections.Counter(),
                                            "sw": 0, "samples": [], "brand_of": ""})
    for r in recs:
        if not r["tags"] or (set(r["tags"]) - GENERIC):
            continue                                   # 이미 제품명이 붙은 기록은 대상 아님
        name = r.get("product") or ""
        vendor = ""
        m = re.search(r"계약업체[:：]\s*([^·)]+)", r.get("content") or "")
        if m:
            vendor = m.group(1).strip()
        # 괄호·따옴표 안 이름 + 문장 속 영문 제품명(Mathematica, MATLAB 등)
        picks = [next((x for x in p if x), "") for p in
                 re.findall(r"\(([^)]{2,16})\)|'([^']{2,16})'|\"([^\"]{2,16})\"", name)]
        picks += re.findall(r"\b([A-Za-z][A-Za-z0-9.]{3,15})\b", name)
        for t in picks:
            t = (t or "").strip().rstrip(",")
            if not t or STOP.search(t) or len(re.sub(r"\s", "", t)) < 2:
                continue
            if norm(t) in known_norm:
                continue                               # 이미 규칙이 있는 제품
            c = cand[t]
            c["n"] += 1
            if vendor:
                c["vendors"][vendor] += 1
            if SW_CTX.search(name):
                c["sw"] += 1
            if len(c["samples"]) < 3:
                c["samples"].append((r["school"], name[:60], vendor))

    # 업체명이 곧 제품명인 경우(READDY AI, PADLET.COM 등) — 유통·조달상은 제외
    RESELLER = re.compile(r"지마켓|쿠팡|이베이|옥션|조달청|문구|상사|유통|서점|총판|"
                          r"컴퓨터|시스템|테크|엔지니어링|건설|인쇄|물산|상회|마트")
    for r in recs:
        if not r["tags"] or (set(r["tags"]) - GENERIC):
            continue
        m = re.search(r"계약업체[:：]\s*([^·)]+)", r.get("content") or "")
        if not m:
            continue
        v = re.sub(r"주식회사|㈜|\(주|유한회사|\(유|Co\.?,?\s?Ltd\.?|Inc\.?", "", m.group(1)).strip()
        v = re.sub(r"[,\s]+$", "", v)
        if len(v) < 3 or RESELLER.search(v) or norm(v) in known_norm:
            continue
        c = cand[v]
        c["n"] += 1
        c["vendors"][m.group(1).strip()] += 1
        c["sw"] += 1                       # 업체명 후보는 SW 문맥으로 간주
        if len(c["samples"]) < 3:
            c["samples"].append((r["school"], (r.get("product") or "")[:60], m.group(1).strip()))

    # 에듀집 등록명은 정식명(브랜드+수식어)인데 계약서엔 브랜드만 적히는 경우
    # (예: '코들 AI 클래스룸' → 계약명 '프로그램 코들 구입'). 첫 토큰이 고유 브랜드일 때만.
    BRAND_STOP = re.compile(
        r"^(AI|인공지능|스마트|디지털|온라인|클래스|교실|수학|영어|국어|과학|코딩|학습|교육|에듀|"
        r"메타버스|가상현실|증강현실|미래|우리|한국|글로벌|플랫폼|프로그램|콘텐츠|서비스|시스템|"
        r"솔루션|초등|중등|고등|모두의|리딩|매쓰|잉글리시|무한|기초|교재|학내망|스마트기기|교사용|"
        r"이동식|프로젝트|미래역량|구독형|전자책|학급|현장|기숙사|지게차|라이트|이미지|방송부|"
        r"직업계고|그린스마트스쿨|스마트팜|스마트시티|인터렉티브|저스트|SW|ICT|IoT|VR|XR|3D)$", re.I)
    brands = collections.defaultdict(set)
    for full in edzip.values():
        toks = full.split()
        if len(toks) < 2:
            continue
        b = toks[0].strip("[]()「」〈〉")
        if len(re.sub(r"\s", "", b)) < 2 or BRAND_STOP.match(b) or norm(b) in known_norm:
            continue
        brands[b].add(full)
    # 같은 브랜드로 시작하는 제품이 여럿이면 어느 제품인지 못 가리므로 제외
    starts = collections.Counter()
    for full in edzip.values():
        for b in brands:
            if full.startswith(b):
                starts[b] += 1
    BR = {b: v for b, v in brands.items() if starts[b] == 1}
    TOK = re.compile(r"[가-힣]+|[A-Za-z][A-Za-z0-9]*")
    BR3 = [b for b in BR if len(b) >= 3]
    for r in recs:
        if not r["tags"] or (set(r["tags"]) - GENERIC):
            continue
        nm = r.get("product") or ""
        hit = None
        for t in set(TOK.findall(nm)):
            if t in BR:
                hit = t
            else:
                hit = next((b for b in BR3 if t.startswith(b) and t != b), None)
            if hit:
                break
        if not hit:
            continue
        c = cand[hit]
        c["n"] += 1
        c["sw"] += 1
        c["brand_of"] = sorted(BR[hit])[0]
        if len(c["samples"]) < 3:
            c["samples"].append((r["school"], nm[:60], ""))

    rows = []
    for name, c in cand.items():
        # 에듀집 사전에 있거나 SW 구매 문맥이 뚜렷하면 1건이어도 후보로 올린다
        # (bitly처럼 한 학교만 산 제품도 실존 제품이므로 사람이 볼 기회를 준다)
        if c["n"] < a.min_count and norm(name) not in edzip and c["sw"] == 0:
            continue
        top = c["vendors"].most_common(1)
        share = (top[0][1] / sum(c["vendors"].values())) if c["vendors"] else 0
        in_edzip = norm(name) in edzip
        if c.get("brand_of"):
            grade, why = "B", f"에듀집 등록명 '{c['brand_of']}'의 브랜드부 — 확인 후 반영"
        elif in_edzip:
            grade, why = "A", f"에듀집 등록 제품({edzip[norm(name)]})"
        elif share >= 0.6 and c["n"] >= 3:
            grade, why = "B", f"업체 쏠림 {share:.0%} ({top[0][0]})"
        else:
            grade, why = "C", "빈도만 확인 — 사람 확인 필요"
        rows.append({"등급": grade, "후보": name, "건수": c["n"], "SW문맥": c["sw"],
                     "근거": why, "표본": c["samples"]})
    rows.sort(key=lambda x: (x["등급"], -x["건수"]))

    lines = ["# 미등록 제품명 후보", "",
             f"범주 태그로만 처리된 계약에서 캐낸 후보입니다. 총 {len(rows)}종 "
             f"(A {sum(1 for r in rows if r['등급']=='A')} · "
             f"B {sum(1 for r in rows if r['등급']=='B')} · "
             f"C {sum(1 for r in rows if r['등급']=='C')})", "",
             "- **A**: 에듀집 제품 사전에 있는 이름 — 실존 제품 확정, `--apply`로 자동 반영",
             "- **B**: 계약 업체가 한 곳으로 쏠림 — 특정 공급사 제품일 가능성 높음, 확인 후 반영",
             "- **C**: 빈도만 높음 — 사람 확인 필요", ""]
    for r in rows:
        lines.append(f"## [{r['등급']}] {r['후보']} — {r['건수']}건 (SW 문맥 {r['SW문맥']}건)")
        lines.append(f"근거: {r['근거']}")
        for s, p, v in r["표본"]:
            lines.append(f"- [{s}] {p}" + (f"  · 업체: {v}" if v else ""))
        lines.append("")
    open("product_candidates.md", "w", encoding="utf-8").write("\n".join(lines))
    print(f"후보 {len(rows)}종 → product_candidates.md")

    # 에듀집에 있어도 보통명사·기존 규칙과 겹치는 이름은 자동 반영하지 않는다
    AUTO_BLOCK = {"디지털교과서", "로봇 코딩", "SMART", "Smart", "온라인 교육", "전자칠판",
                  "심리검사", "공동교육과정", "스마트", "코딩", "소프트웨어",
                  # 동아리·사업 명칭과 겹쳐 오탐 확인된 것들
                  "사이언스타임", "수학 놀이터", "함께학교", "경기관광", "오늘도",
                  "학생참여중심수업", "진로이음", "저스트", "AI튜터",
                  "티처몰", "기숙사 관리 프로그램", "온라인 수강 신청"}
    def rule_covered(name):
        src2 = open("build_data.py", encoding="utf-8").read()
        pats = re.findall(r'\("[^"]+",\s+r"([^"]+)"\),',
                          src2[src2.index("SPECIFIC_RULES = ["):src2.index("# 자동 발굴 규칙")])
        for p in ("edzip_rules.csv",):
            if os.path.exists(p):
                pats += [r["패턴"] for r in csv.DictReader(open(p, encoding="utf-8-sig"))]
        return any(re.search(p, name, re.I) for p in pats if p)

    if a.apply:
        agrade = [r for r in rows if r["등급"] == "A"
                  and r["후보"] not in AUTO_BLOCK and not rule_covered(r["후보"])]
        seen_norm = set()
        agrade = [r for r in agrade if not (norm(r["후보"]) in seen_norm or seen_norm.add(norm(r["후보"])))]
        exist = []
        if os.path.exists("mined_rules.csv"):
            exist = list(csv.DictReader(open("mined_rules.csv", encoding="utf-8-sig")))
        have = {r["태그"] for r in exist}
        added = 0
        for r in agrade:
            if r["후보"] in have:
                continue
            pat = r"[\s·\-]*".join(re.escape(t) for t in r["후보"].split())
            exist.append({"태그": r["후보"], "패턴": pat, "건수": r["건수"],
                          "근거": r["근거"], "문맥필요": "Y" if len(re.sub(r"\s", "", r["후보"])) <= 4 else ""})
            added += 1
        with open("mined_rules.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["태그", "패턴", "건수", "근거", "문맥필요"])
            w.writeheader(); w.writerows(exist)
        print(f"A등급 {added}종 → mined_rules.csv (빌드 시 자동 적용)")

if __name__ == "__main__":
    main()
