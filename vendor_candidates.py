# 공급사 태그 후보 뽑기 — '제품군으로만 남은 기록'을 업체명으로 풀 수 있는지 살펴본다.
# 사용: python3 vendor_candidates.py [--min 20] [--top 40]
#
# 원칙: 업체명으로 제품을 추정하지 않는다. 다만 두 경우는 예외로 인정해 왔다.
#   (가) 업체명이 곧 제품명인 경우 (Padlet.com·READDY AI 등)
#   (나) 그 업체가 파는 제품이 하나로 확인되는 경우 (투핸즈인터랙티브 → 디딤)
# 그래서 '이름이 적힌 계약에서 어떤 제품이 나오는가'를 함께 보여 준다.
# 한 제품으로 쏠려 있으면 (나)에 해당하고, 여러 제품이 섞여 있으면 규칙으로 풀 수 없다.
import argparse, collections, csv, json, os, re

GENERIC = {"기기(PC·태블릿·전자칠판 등)", "SW·플랫폼", "인프라(교실·설비)", "로봇·교구·키트",
           "코스웨어", "VR/XR 장비", "드론", "3D 프린팅/CAD", "운영 부대구매", "AI 면접시스템"}
# 유통·총판·조달 대행처럼 여러 회사 제품을 파는 곳은 업체명으로 제품을 알 수 없다
RESELLER = re.compile(r"몰$|마켓|쇼핑|유통|상사|문구|서점|오피스|컴퓨터|시스템|정보통신|"
                      r"엔지니어링|테크놀로지|아이앤씨|아이앤디|11번가|쿠팡|인터파크|지마켓")


def load_records():
    s = open("data.js", encoding="utf-8").read()
    lit = s[s.index("'") + 1:s.rindex("'")]
    d = json.loads(lit.replace("\\'", "'").replace("\\\\", "\\"))
    cols, dic, tl = d["cols"], d.get("dict", {}), d["tagList"]
    out = []
    for row in d["rows"]:
        r = {}
        for i, k in enumerate(cols):
            v = row[i]
            if k == "tags":
                v = [tl[n] for n in v]
            elif k in dic and isinstance(v, int):
                v = dic[k][v]
            r[k] = v
        out.append(r)
    return out


def norm(name):
    """(주)·주식회사·괄호를 떼어 같은 회사를 하나로 모은다"""
    n = re.sub(r"\(주\)|주식회사|㈜|\(유\)|유한회사|\(재\)|재단법인|\(사\)|사단법인", "", name or "")
    return re.sub(r"\s+", "", n).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=20, help="제품군으로만 남은 기록이 이만큼 이상인 업체만")
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()

    edzip = {}
    if os.path.exists("edzip_company.csv"):
        for r in csv.DictReader(open("edzip_company.csv", encoding="utf-8-sig")):
            edzip.setdefault(norm(r["회사명"]), set()).add(r["제품명"])

    recs = load_records()
    stat = collections.defaultdict(lambda: {"generic": 0, "named": collections.Counter(),
                                            "schools": set(), "raw": collections.Counter(),
                                            "sample": []})
    for r in recs:
        v = norm(r.get("vendor"))
        if not v:
            continue
        s = stat[v]
        s["raw"][r.get("vendor")] += 1
        named = [t for t in r["tags"] if t not in GENERIC]
        if named:
            for t in named:
                s["named"][t] += 1
        else:
            s["generic"] += 1
            s["schools"].add(r["school"])
            if len(s["sample"]) < 3:
                s["sample"].append(f"[{r['school']}] {(r.get('product') or '')[:46]}")

    rows = []
    for v, s in stat.items():
        if s["generic"] < a.min:
            continue
        total_named = sum(s["named"].values())
        top_named, top_n = (s["named"].most_common(1)[0] if total_named else ("", 0))
        share = top_n / total_named if total_named else 0
        full = s["raw"].most_common(1)[0][0]
        rows.append({
            "업체": full, "정규화": v, "제품군만": s["generic"], "학교수": len(s["schools"]),
            "이름있는계약": total_named, "대표제품": top_named, "쏠림": round(share, 2),
            "제품가짓수": len(s["named"]),
            "에듀집": "O" if v in edzip else "",
            "유통성": "유통 의심" if RESELLER.search(v) else "",
            "표본": " / ".join(s["sample"]),
        })
    rows.sort(key=lambda x: -x["제품군만"])

    # 조달 대행·대형 제조사는 파는 물건이 많아 업체명으로 제품을 특정할 수 없다
    AGENCY = re.compile(r"조달청|교육청|학교장터|우체국|은행|카드|페이|파이낸셜")
    MAKER = re.compile(r"삼성전자|엘지전자|LG전자|애플|레노버|에이서|델|한국HP|아수스")

    def verdict(r):
        if AGENCY.search(r["정규화"]):
            return "× 조달 대행·결제 창구 — 업체가 아니다"
        if MAKER.search(r["정규화"]):
            return "× 대형 제조사 — 파는 물건이 여러 가지다"
        if r["유통성"]:
            return "× 유통·시스템 업체로 보임 — 업체명으로 제품을 알 수 없다"
        if r["이름있는계약"] < 10:
            return f"? 이름이 적힌 계약이 {r['이름있는계약']}건뿐 — 근거가 얇다"
        if r["제품가짓수"] == 1:
            return f"○ 단일 제품 → '{r['대표제품']}' 규칙 후보"
        if r["쏠림"] >= 0.85:
            return f"○ {int(r['쏠림']*100)}%가 '{r['대표제품']}' — 규칙 후보"
        if r["쏠림"] >= 0.7:
            return f"△ {int(r['쏠림']*100)}%가 '{r['대표제품']}' — 표본 확인 필요"
        return f"× 제품이 {r['제품가짓수']}종으로 섞여 있다"

    lines = ["# 공급사 태그 후보", "",
             f"제품군으로만 남은 기록이 {a.min}건 이상인 업체 {len(rows)}곳 (상위 {a.top}곳 표시)", "",
             "| 업체 | 제품군만 | 학교 | 이름있는 계약 | 대표 제품(쏠림) | 에듀집 | 판단 |",
             "|---|---:|---:|---:|---|:-:|---|"]
    for r in rows[:a.top]:
        nm = f"{r['대표제품']} ({int(r['쏠림']*100)}%)" if r["대표제품"] else "—"
        lines.append(f"| {r['업체']} | {r['제품군만']:,} | {r['학교수']:,} | {r['이름있는계약']:,} | "
                     f"{nm} | {r['에듀집']} | {verdict(r)} |")
    lines += ["", "## 표본", ""]
    for r in rows[:a.top]:
        lines.append(f"**{r['업체']}** — {r['표본']}")
    open("vendor_candidates.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")

    print(f"업체 {len(rows)}곳 → vendor_candidates.md")
    for r in rows[:a.top]:
        nm = f"{r['대표제품']}({int(r['쏠림']*100)}%)" if r["대표제품"] else "—"
        print(f"  {r['업체'][:22]:<24} 제품군만 {r['제품군만']:>5,}건/{r['학교수']:>4,}교 · "
              f"이름있는 {r['이름있는계약']:>4,}건 · {nm:<22} {verdict(r)}")


if __name__ == "__main__":
    main()
