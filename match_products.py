# 에듀집 등록 제품 × 조달 계약 전수 대조 — 제품별 실사용 현황 산출
# 사용: python3 match_products.py [--min-len 4] [--detail-cap 50]
# 입력: edzip_products.csv, edzip_basic.csv, nara_full_*.csv(전수), refined_*.csv, s2b_candidates.csv
# 출력: product_usage.csv (제품별), product_usage_detail.csv (근거 계약 표본)
#
# 대조 방식: 계약 100만 건 × 제품 2,500종 전수 비교는 불가능하므로 3글자 접두 색인을 만들고
# 계약명을 훑으며 후보만 확인한다(스트리밍 — 계약을 메모리에 쌓지 않는다).
import argparse, csv, glob, os, re, sys, collections

csv.field_size_limit(10**7)

CL = {"private_domestic": "민간(국산)", "private_foreign": "민간(외산)",
      "ai_digital_educational_materials": "AI·디지털 교육자료",
      "other": "기타(교사 등 개인)", "public_including_city_province": "공공(시도포함)"}
ST = {"confirmed": "확인완료", "improvement_requested": "보완요청", "checking": "확인중"}
PREFIX = 3          # 색인 접두 길이
AIDT_PAT = re.compile(r"aidt|ai디지털교과서|디지털교과서|ai디지털교육자료|ai교육자료")

def norm(s):
    """제품명·공급자명 정규화 — 괄호 안 부연과 법인격 표기를 떼어낸다"""
    s = re.sub(r"\(.*?\)|\[.*?\]|<.*?>", " ", s or "")
    s = re.sub(r"주식회사|㈜|\(주\)|유한회사|Co\.?,?\s?Ltd\.?|Inc\.?|Corp\.?", " ", s, flags=re.I)
    return re.sub(r"[\s·ㆍ‧・\-_/,\.'\"]+", "", s).lower()

def norm_hay(s):
    """계약문 정규화 — 괄호 안에 제품명이 들어가는 경우가 많아 내용을 지우지 않는다"""
    s = re.sub(r"주식회사|㈜|\(주\)|유한회사|Co\.?,?\s?Ltd\.?|Inc\.?|Corp\.?", " ", s or "", flags=re.I)
    return re.sub(r"[\s·ㆍ‧・\-_/,\.'\"()\[\]<>]+", "", s).lower()

def load_catalog():
    cat = {}
    def add(name, alt, company, cls, status, src):
        key = norm(name)
        if not key:
            return
        e = cat.setdefault(key, {"제품명": name, "별칭": set(), "공급자": set(),
                                 "구분": cls, "승인상태": status, "카탈로그": set()})
        if alt and norm(alt) != key:
            e["별칭"].add(alt)
        if company:
            e["공급자"].add(company)
        e["카탈로그"].add(src)
        if cls and not e["구분"]:
            e["구분"] = cls
        if status and not e["승인상태"]:
            e["승인상태"] = status
    if os.path.exists("edzip_products.csv"):
        for p in csv.DictReader(open("edzip_products.csv", encoding="utf-8-sig")):
            add(p["제품명"], p.get("영문명"), p.get("공급자"),
                CL.get(p.get("구분", ""), p.get("구분", "")),
                ST.get(p.get("확인여부", ""), p.get("확인여부", "")), "학습지원SW")
    if os.path.exists("edzip_basic.csv"):
        for b in csv.DictReader(open("edzip_basic.csv", encoding="utf-8-sig")):
            add(b["제품명"], "", b.get("공급자"), "", "", "기본자료")
    return cat

def contract_files():
    """전수(nara_full)가 있으면 그것을, 없으면 기존 refined를 쓴다.
    교육청 계약공개(인천·부산 등)와 S2B 공고도 함께 대조한다."""
    full = sorted(glob.glob("nara_full_*.csv"))
    nara = (full or sorted(glob.glob("refined_2*.csv")))
    for extra in ("ice_refined.csv", "pen_refined.csv"):
        if os.path.exists(extra):
            nara.append(extra)
    return nara, (["s2b_candidates.csv"] if os.path.exists("s2b_candidates.csv") else [])

def iter_contracts():
    nara, s2b = contract_files()
    seen = set()
    for path in nara:
        with open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                k = (r.get("계약번호"), r.get("학교명"))
                if k in seen:
                    continue
                seen.add(k)
                yield {"학교": r.get("학교명", ""), "계약명": r.get("계약명", ""),
                       "업체": r.get("업체명", ""), "일자": r.get("계약일", ""),
                       "시도": r.get("시도", ""), "출처": "나라장터"}
    for path in s2b:
        with open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                k = (r.get("공고번호"), r.get("기관명"))
                if k in seen:
                    continue
                seen.add(k)
                yield {"학교": r.get("기관명", ""), "계약명": r.get("공고명", ""),
                       "업체": "", "일자": r.get("공고일", ""),
                       "시도": "", "출처": "S2B"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-len", type=int, default=4,
                    help="이 길이 미만 제품명은 공급자명이 함께 나올 때만 인정(오탐 방지)")
    ap.add_argument("--detail-cap", type=int, default=50, help="제품당 근거 계약 저장 상한")
    a = ap.parse_args()

    cat = load_catalog()
    # 별칭 → 대표키 매핑과 접두 색인
    alias2key, index, short_keys, skipped = {}, collections.defaultdict(list), [], []
    for key, e in cat.items():
        forms = {key} | {norm(x) for x in e["별칭"] if norm(x)}
        for f in forms:
            if len(f) < PREFIX:
                skipped.append(e["제품명"])
                continue
            alias2key[f] = key
            index[f[:PREFIX]].append(f)
        if len(key) < a.min_len:
            short_keys.append(key)
    comp_of = {k: {norm(c) for c in e["공급자"] if len(norm(c)) >= 3} for k, e in cat.items()}
    aidt_keys = {k for k, e in cat.items() if e["구분"] == "AI·디지털 교육자료"}

    nara, s2b = contract_files()
    print(f"제품 사전 {len(cat)}종 (색인 {len(alias2key)}개 표기, 너무 짧아 제외 {len(set(skipped))}종)")
    print(f"계약 파일: 나라장터 {len(nara)}개 + S2B {len(s2b)}개 — 대조 시작", flush=True)

    stat = collections.defaultdict(lambda: {"schools": set(), "n": 0, "last": "", "src": set(),
                                            "vendors": collections.Counter(), "sup_hit": 0})
    detail = collections.defaultdict(list)
    aidt_generic = {"schools": set(), "n": 0, "last": ""}
    scanned = 0
    for r in iter_contracts():
        scanned += 1
        if scanned % 200000 == 0:
            print(f"  {scanned:,}건 대조…", flush=True)
        hay = norm_hay(r["계약명"])          # 제품명 대조 대상
        vend = norm_hay(r["업체"])            # 공급자 확인 대상
        if not hay:
            continue
        found = set()
        for i in range(len(hay) - PREFIX + 1):
            for f in index.get(hay[i:i+PREFIX], ()):
                if hay.startswith(f, i):
                    found.add(alias2key[f])
        # AI·디지털 교육자료: 등록명이 "출판사+과목" 형식이라 계약명과 글자가 안 맞는다.
        # 출판사명이 계약명에 있으면 그 제품으로, 없으면 출판사 미확인 집계로 돌린다.
        if AIDT_PAT.search(hay):
            hit_pub = {k for k in aidt_keys if any(c in vend or c in hay for c in comp_of[k])}
            if hit_pub:
                found |= hit_pub
            else:
                aidt_generic["n"] += 1
                if r["학교"]:
                    aidt_generic["schools"].add(r["학교"])
                if r["일자"] > aidt_generic["last"]:
                    aidt_generic["last"] = r["일자"]
        for k in found:
            if len(k) < a.min_len and not any(c in vend or c in hay for c in comp_of[k]):
                continue    # 짧은 이름은 공급자 동시 등장 시에만 인정
            s = stat[k]
            s["n"] += 1
            if r["학교"]:
                s["schools"].add(r["학교"])
            if r["일자"] > s["last"]:
                s["last"] = r["일자"]
            s["src"].add(r["출처"])
            if r["업체"]:
                s["vendors"][norm(r["업체"])] += 1
            if any(c in vend or c in hay for c in comp_of[k]):
                s["sup_hit"] += 1
            if len(detail[k]) < a.detail_cap:
                detail[k].append({"제품명": cat[k]["제품명"], "학교": r["학교"], "시도": r["시도"],
                                  "계약명": r["계약명"], "업체": r["업체"], "일자": r["일자"],
                                  "출처": r["출처"]})
    print(f"  대조 완료: 계약 {scanned:,}건", flush=True)

    rows = []
    for key, e in cat.items():
        s = stat.get(key)
        # 신뢰도: 등록 공급자가 계약 상대 업체로 확인되면 '높음'.
        # 공급자 확인이 전혀 없는데 서로 다른 업체가 여러 곳이면 일반명사 오탐일 가능성이 크다.
        if not s:
            conf = ""
        elif s["sup_hit"] > 0:
            conf = "높음"                      # 등록 공급자가 계약 상대로 확인됨
        else:
            vs = s["vendors"]
            top = vs.most_common(1)[0][1] if vs else 0
            share = top / sum(vs.values()) if vs else 0
            if len(vs) >= 3 and share >= 0.5:
                conf = "높음"                  # 특정 업체가 계약을 도맡음 = 실제 제품
            elif len(vs) >= 5 and share < 0.35:
                conf = "낮음(일반명사 의심)"    # 업체가 제각각 = 보통명사가 우연히 걸린 것
            elif len(key) >= 4:
                conf = "중간"
            else:
                conf = "낮음(짧은 이름)"
        rows.append({
            "제품명": e["제품명"], "공급자": " / ".join(sorted(e["공급자"]))[:60],
            "구분": e["구분"] or "미분류", "승인상태": e["승인상태"] or "-",
            "카탈로그": "+".join(sorted(e["카탈로그"])),
            "확인학교수": len(s["schools"]) if s else 0, "계약건수": s["n"] if s else 0,
            "최근계약일": s["last"] if s else "", "출처": "+".join(sorted(s["src"])) if s else "",
            "신뢰도": conf,
            "판정": ("사용 확인" if conf in ("높음", "중간") else "검증 필요") if s else "조달 기록 없음",
        })
    if aidt_generic["n"]:
        rows.append({"제품명": "AI·디지털 교육자료 (출판사 미확인)", "공급자": "", "구분": "AI·디지털 교육자료",
                     "승인상태": "-", "카탈로그": "집계", "확인학교수": len(aidt_generic["schools"]),
                     "계약건수": aidt_generic["n"], "최근계약일": aidt_generic["last"],
                     "출처": "나라장터+S2B", "신뢰도": "높음", "판정": "사용 확인"})
    rows.sort(key=lambda x: (-x["확인학교수"], x["제품명"]))
    with open("product_usage.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open("product_usage_detail.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["제품명", "학교", "시도", "계약명", "업체", "일자", "출처"])
        w.writeheader()
        for k in detail:
            w.writerows(detail[k])

    used = [r for r in rows if r["판정"] == "사용 확인"]
    weak = [r for r in rows if r["판정"] == "검증 필요"]
    print(f"\n사용 확인 {len(used)}종 / 전체 {len(rows)}종 ({len(used)/len(rows)*100:.1f}%)"
          f" · 검증 필요 {len(weak)}종")
    byc = collections.Counter(r["구분"] for r in used)
    tot = collections.Counter(r["구분"] for r in rows)
    for k in sorted(tot, key=lambda x: -tot[x]):
        print(f"  {k}: {byc.get(k,0)}/{tot[k]}종 ({byc.get(k,0)/tot[k]*100:.0f}%)")
    print("\n확인 학교 수 상위 25종 (신뢰도 높음·중간):")
    for r in used[:25]:
        print(f"  {r['확인학교수']:5d}개교 {r['계약건수']:6d}건  {r['제품명'][:32]}  [{r['신뢰도']}]")
    if weak:
        print("\n검증 필요(오탐 의심) 상위 10종:")
        for r in weak[:10]:
            print(f"  {r['확인학교수']:5d}개교  {r['제품명'][:32]}  [{r['신뢰도']}]")
    if skipped:
        print(f"\n※ 이름이 2글자 이하라 자동 대조에서 제외: {len(set(skipped))}종 (예: {', '.join(sorted(set(skipped))[:8])})")
    print("\n→ product_usage.csv, product_usage_detail.csv")

if __name__ == "__main__":
    main()
