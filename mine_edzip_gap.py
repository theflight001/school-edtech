# 에듀집 사전에는 있는데 우리가 아직 못 잡는 제품을 찾아 규칙 후보로 올린다.
# 사용: python3 mine_edzip_gap.py [--apply]
#
# 갭의 정체: 계약명에 제품 이름이 분명히 적혀 있는데도 규칙 사전에 없어 '제품군'에만 묶인 기록들.
# 판정 근거(추측하지 않는다):
#   A등급 = 계약명에 이름이 있고 + 그 계약의 업체가 에듀집에 적힌 그 제품의 회사와 같다
#           → 같은 이름의 다른 물건일 가능성이 사실상 없다
#   B등급 = 이름은 있으나 업체가 확인되지 않음 → 사람이 표본을 보고 판단
#   제외   = 보통명사(전자칠판·현미경 등)이거나 이미 다른 제품 태그가 붙은 계약이 섞임
import argparse, collections, csv, json, os, re

GENERIC = {"기기(PC·태블릿·전자칠판 등)", "SW·플랫폼", "인프라(교실·설비)", "로봇·교구·키트",
           "코스웨어", "VR/XR 장비", "드론", "3D 프린팅/CAD", "운영 부대구매", "AI 면접시스템"}
# 제품명이 아니라 물건 종류를 가리키는 말 — 그대로 규칙에 넣으면 대량 오태깅이 난다
COMMON = re.compile(
    r"^(전자칠판|현미경|로봇 ?코딩|공동교육과정|태블릿|노트북|프린터|스캐너|모니터|빔프로젝터|"
    r"교육용 ?소프트웨어|학습 ?소프트웨어|AI ?학습 ?소프트웨어|코딩로봇|드론|3D프린터|"
    r"실물화상기|충전함|서버|공유기|카메라|마이크|스피커|헤드셋|키보드|마우스|의자|책상|"
    r"소프트웨어|프로그램|콘텐츠|플랫폼|시스템|어플리케이션|앱)$|"
    r"^(SMART|AI|SW|ICT|VR|AR|XR|IoT|PC|TV)$")
MIN_LEN = 3


def load_db():
    s = open("data.js", encoding="utf-8").read()
    lit = s[s.index("'") + 1:s.rindex("'")]
    return json.loads(lit.replace("\\'", "'").replace("\\\\", "\\"))


def norm(x):
    return re.sub(r"[\s·ㆍ\-_/()\[\]]+", "", x or "").lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="A등급을 mined_rules.csv에 반영")
    ap.add_argument("--min-hit", type=int, default=3)
    a = ap.parse_args()

    # 에듀집: 제품명 → 회사명
    company = {}
    for p in ("edzip_company.csv", "edzip_products.csv", "edzip_basic.csv"):
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            n = (r.get("제품명") or "").strip()
            c = (r.get("회사명") or "").strip()
            if n and c:
                company.setdefault(n, c)
            elif n:
                company.setdefault(n, "")

    d = load_db()
    cols, dic, tl = d["cols"], d["dict"], d["tagList"]
    have = {norm(t) for t in tl if t not in GENERIC}
    idx = {k: cols.index(k) for k in ("product", "school", "vendor", "tags")}

    recs = []
    for row in d["rows"]:
        def v(k):
            x = row[idx[k]]
            return dic[k][x] if k in dic and isinstance(x, int) else x
        tags = [tl[i] for i in row[idx["tags"]]]
        recs.append({"p": v("product") or "", "s": v("school") or "",
                     "v": v("vendor") or "", "gen": all(t in GENERIC for t in tags),
                     "named": [t for t in tags if t not in GENERIC]})

    cand = [n for n in company
            if len(re.sub(r"\s", "", n)) >= MIN_LEN and norm(n) not in have and not COMMON.match(n.strip())]
    print(f"에듀집 제품 {len(company):,}종 중 우리가 아직 안 잡는 이름 {len(cand):,}종을 계약명에서 찾는다", flush=True)

    out = []
    for n in cand:
        hits = [r for r in recs if n in r["p"]]
        if len(hits) < a.min_hit:
            continue
        gen = [r for r in hits if r["gen"]]
        conflict = [r for r in hits if r["named"]]
        co = norm(company.get(n, ""))
        vend_ok = sum(1 for r in hits if co and co in norm(r["v"])) if co else 0
        vshare = vend_ok / len(hits) if hits else 0
        grade = ("A" if vshare >= 0.5 and not conflict else
                 "B" if not conflict else "C")
        out.append({"제품": n, "회사": company.get(n, ""), "걸린건수": len(hits),
                    "제품군만": len(gen), "학교": len({r["s"] for r in gen}),
                    "업체일치": round(vshare, 2), "충돌": len(conflict), "등급": grade,
                    "표본": [f"[{r['s']}] {r['p'][:48]}" for r in gen[:3]]})
    out.sort(key=lambda x: (x["등급"], -x["제품군만"]))

    lines = ["# 에듀집 대조 — 아직 못 잡는 제품", "",
             "| 등급 | 제품 | 회사 | 걸린 계약 | 제품군만 | 학교 | 업체 일치 | 충돌 |",
             "|:-:|---|---|---:|---:|---:|---:|---:|"]
    for r in out:
        lines.append(f"| {r['등급']} | {r['제품']} | {r['회사']} | {r['걸린건수']:,} | {r['제품군만']:,} | "
                     f"{r['학교']:,} | {int(r['업체일치']*100)}% | {r['충돌']} |")
    lines += ["", "## 표본", ""]
    for r in out:
        lines.append(f"**[{r['등급']}] {r['제품']}** — " + " / ".join(r["표본"]))
    open("edzip_gap.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")

    g = collections.Counter(r["등급"] for r in out)
    print(f"후보 {len(out)}종 → edzip_gap.md  (A {g['A']} · B {g['B']} · C {g['C']})")
    print(f"  A등급이 풀어 줄 기록: {sum(r['제품군만'] for r in out if r['등급']=='A'):,}건")
    for r in [x for x in out if x["등급"] == "A"][:15]:
        print(f"   {r['제품'][:22]:<24} {r['제품군만']:>4}건/{r['학교']:>3}교 · 업체 {r['회사'][:14]} ({int(r['업체일치']*100)}%)")

    if not a.apply:
        print("\n(확인만 했습니다. --apply 를 붙이면 A등급을 mined_rules.csv에 넣습니다)")
        return
    rules = list(csv.DictReader(open("mined_rules.csv", encoding="utf-8-sig"))) \
        if os.path.exists("mined_rules.csv") else []
    have_tag = {r["태그"] for r in rules}
    added = 0
    for r in out:
        if r["등급"] != "A" or r["제품"] in have_tag:
            continue
        pat = r"[\s·\-]*".join(re.escape(t) for t in r["제품"].split())
        rules.append({"태그": r["제품"], "패턴": pat, "건수": r["제품군만"],
                      "근거": f"에듀집 등록 제품 · 계약 업체 {r['회사']} 일치 {int(r['업체일치']*100)}%",
                      "문맥필요": "Y" if len(re.sub(r"\s", "", r["제품"])) <= 4 else ""})
        added += 1
    with open("mined_rules.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["태그", "패턴", "건수", "근거", "문맥필요"])
        w.writeheader(); w.writerows(rules)
    print(f"\nA등급 {added}종 → mined_rules.csv (build_data.py가 빌드 때 읽는다)")


if __name__ == "__main__":
    main()
