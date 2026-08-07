# 정정 요청(특히 공급 기업 제보)을 규칙으로 반영하는 도구.
#
# "제품군으로만 남아 있는 저 기록이 우리 제품이다"라는 제보는 기록을 하나씩 고치지 않는다.
# 계약명에서 그 제품을 알아보는 규칙을 mined_rules.csv에 넣으면 같은 이름이 적힌 다른 계약까지
# 한꺼번에 풀린다. build_data.py가 빌드 때 이 파일을 자동으로 읽는다.
#
# 사용:
#   python3 add_rule.py --tag "디딤" --pattern "플레이 ?디딤|디딤" --by "투핸즈인터랙티브 2026-08-08"
#       → 반영하지 않고 무엇이 달라지는지만 보여준다(기본값). 표본을 눈으로 확인한다.
#   python3 add_rule.py ... --apply          → 확인 후 mined_rules.csv에 기록
#   python3 add_rule.py ... --ctx            → 보통명사와 겹치는 짧은 이름은 소프트웨어 문맥이 있을 때만
#   python3 add_rule.py --list               → 지금 들어 있는 규칙 보기
#
# 반영 뒤에는 python3 build_data.py 로 다시 만들고 tag_review.md로 오매칭을 확인한다.
import argparse, csv, json, os, re, sys, collections

RULES = "mined_rules.csv"
FIELDS = ["태그", "패턴", "건수", "근거", "문맥필요"]
GENERIC = {"코스웨어", "SW·플랫폼", "로봇·교구·키트", "VR/XR 장비", "드론", "3D 프린팅/CAD",
           "기기(PC·태블릿·전자칠판 등)", "인프라(교실·설비)", "AI 면접시스템", "운영 부대구매",
           # 이름을 줄이기 전 기록도 함께 본다
           "SW·플랫폼(제품명 미상)", "코스웨어(기타)", "운영 부대구매(제품 미상)"}
SW_CTX = re.compile(r"구독|라이선스|라이센스|이용권|이용료|사용료|플랫폼|소프트웨어|앱|어플|"
                    r"코스웨어|프로그램|계정|콘텐츠|에듀테크|인공지능|\bAI\b|디지털", re.I)


def load_records():
    if not os.path.exists("data.js"):
        sys.exit("data.js가 없습니다 — 먼저 build_data.py를 돌리세요")
    s = open("data.js", encoding="utf-8").read()
    if "JSON.parse(" in s[:200]:                      # 문자열에 담긴 형식
        lit = s[s.index("'") + 1:s.rindex("'")]
        body = lit.replace("\\'", "'").replace("\\\\", "\\")
    else:
        body = s[s.index("{"):s.rindex("}") + 1]
    d = json.loads(body)
    cols, dict_, tagList = d["cols"], d.get("dict", {}), d["tagList"]
    out = []
    for row in d["rows"]:
        r = {}
        for c, k in enumerate(cols):
            v = row[c]
            if k == "tags":
                v = [tagList[n] for n in v]
            elif k in dict_ and isinstance(v, int):
                v = dict_[k][v]
            r[k] = v
        out.append(r)
    return out


def load_rules():
    if not os.path.exists(RULES):
        return []
    return list(csv.DictReader(open(RULES, encoding="utf-8-sig")))


def text_of(r):
    """계약명 — 화면의 '제품/서비스'와 조립된 '내용'을 함께 본다"""
    return f"{r.get('product') or ''} {r.get('ctpl') or ''}"


def vendor_of(r):
    m = re.search(r"계약업체[:：]\s*([^·)]+)", r.get("ctpl") or "")
    return (m.group(1) if m else (r.get("vendor") or "")).strip()


def report(tag, pattern, recs, ctx_only, sample):
    try:
        pat = re.compile(pattern, re.I)
    except re.error as e:
        sys.exit(f"패턴이 잘못됐습니다: {e}")

    hit = [r for r in recs if pat.search(text_of(r))]
    if ctx_only:
        hit = [r for r in hit if SW_CTX.search(text_of(r))]
    generic_only = [r for r in hit if set(r["tags"]) <= GENERIC]
    already = [r for r in hit if tag in r["tags"]]
    # 다른 제품 태그가 이미 붙은 기록에 새 태그가 얹히면 오매칭일 수 있다
    conflict = [r for r in hit if not set(r["tags"]) <= GENERIC and tag not in r["tags"]]
    schools = {r["school"] for r in generic_only}
    vendors = collections.Counter(vendor_of(r) for r in hit if vendor_of(r))

    print(f"\n■ 태그 '{tag}' · 패턴 /{pattern}/{' (문맥 필요)' if ctx_only else ''}")
    print(f"  계약명에 걸리는 기록 {len(hit):,}건")
    print(f"   · 제품군으로만 남아 있던 기록 {len(generic_only):,}건 → 이 제품으로 풀린다 "
          f"({len(schools):,}개교)")
    if already:
        print(f"   · 이미 같은 태그가 붙은 기록 {len(already):,}건")
    if conflict:
        print(f"   ⚠ 다른 제품 태그가 이미 붙은 기록 {len(conflict):,}건 — 오매칭인지 확인하세요")
    if vendors:
        top = " · ".join(f"{v}({n})" for v, n in vendors.most_common(5))
        print(f"   · 계약 상대 업체: {top}")
        first, n1 = vendors.most_common(1)[0]
        share = n1 / sum(vendors.values())
        if share < 0.6 and len(vendors) > 3:
            print(f"   ⚠ 업체가 여러 곳({len(vendors)}곳)에 흩어져 있습니다 — 일반 명사와 겹치지 않는지 보세요")

    def show(title, rows):
        if not rows:
            return
        print(f"\n  [{title}] 표본 {min(sample, len(rows))}건")
        for r in rows[:sample]:
            v = vendor_of(r)
            print(f"   - {r['school']} | {text_of(r).strip()[:80]}"
                  f"{' | ' + v if v else ''} | 현재태그 {','.join(r['tags'])[:40]}")

    show("제품군으로만 남아 있던 기록", generic_only)
    show("다른 제품 태그가 붙은 기록", conflict)
    return hit, generic_only, conflict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="화면에 표시할 제품명")
    ap.add_argument("--pattern", help="계약명에서 이 제품을 알아보는 정규식 (생략하면 태그명 그대로)")
    ap.add_argument("--by", default="", help="근거 — 제보한 곳과 날짜 (예: '투핸즈인터랙티브 2026-08-08')")
    ap.add_argument("--ctx", action="store_true", help="소프트웨어 문맥이 있을 때만 인정(짧은 이름·보통명사)")
    ap.add_argument("--sample", type=int, default=12)
    ap.add_argument("--apply", action="store_true", help="확인을 마쳤으면 mined_rules.csv에 기록")
    ap.add_argument("--list", action="store_true", help="지금 들어 있는 규칙 보기")
    a = ap.parse_args()

    if a.list:
        for r in load_rules():
            print(f"{r['태그']:<20} /{r['패턴']}/  {r.get('근거','')}"
                  f"{' (문맥필요)' if (r.get('문맥필요') or '').strip() == 'Y' else ''}")
        return
    if not a.tag:
        sys.exit("--tag 를 주세요 (예: --tag '디딤' --pattern '플레이 ?디딤|디딤')")

    pattern = a.pattern or r"[\s·\-]*".join(re.escape(t) for t in a.tag.split())
    rules = load_rules()
    if any(r["태그"] == a.tag for r in rules):
        print(f"! 이미 '{a.tag}' 규칙이 있습니다 — 패턴을 고치려면 {RULES}를 직접 손보세요")

    recs = load_records()
    hit, generic_only, conflict = report(a.tag, pattern, recs, a.ctx, a.sample)

    if not a.apply:
        print(f"\n(확인만 했습니다. 표본이 모두 이 제품이 맞으면 --apply 를 붙여 다시 실행하세요)")
        return
    if not hit:
        sys.exit("\n걸리는 기록이 없습니다 — 계약명에 제품 이름이 아예 없는 경우입니다.\n"
                 "  이때는 규칙으로 풀 수 없습니다. 업체명이 곧 제품명인 경우에만\n"
                 "  build_data.py의 VENDOR_RULES에 한 줄 넣고, 근거를 주석으로 남기세요.")
    if any(r["태그"] == a.tag for r in rules):
        sys.exit("같은 태그가 이미 있어 그대로 둡니다")

    rules.append({"태그": a.tag, "패턴": pattern, "건수": len(generic_only),
                  "근거": ("정정 요청 " + a.by).strip() if a.by else "정정 요청",
                  "문맥필요": "Y" if a.ctx else ""})
    with open(RULES, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rules)
    print(f"\n→ {RULES}에 기록했습니다. 이어서:")
    print("   python3 build_data.py     (규칙을 반영해 data.js 다시 만들기)")
    print("   tag_review.md 로 오매칭 확인 후 커밋 — 커밋 메시지에 제보자·판단 결과를 적습니다")


if __name__ == "__main__":
    main()
