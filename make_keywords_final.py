# 확정 검색어 목록을 만든다 — 모든 검색형 자료원의 전 연도에 똑같이 적용할 '줄인 목록'.
# 사용: python3 make_keywords_final.py [--write]   → keywords_final.txt, keywords_final_report.md
#
# 기준(2026-09-20 사용자 결정):
#  - 모집단: 현재 판 edzip_brand_keywords.txt(3,964종) + 기본 검색어 19종 = 3,977종.
#  - 남기는 것: S2B 전수(s2b_all.csv)와 나라장터 전수(nara_full_*.csv)의 계약명에 한 번이라도 나타나는 검색어.
#    기본 검색어 19종은 나타나는지와 무관하게 모두 남긴다.
#  - 대조 방식: 교육청 검색창과 같은 '글자 그대로의 부분 일치'. 다만 영문 대소문자와
#    띄어쓰기·가운뎃점·하이픈 유무는 같은 것으로 본다(양쪽에서 [공백 · -]를 지우고 소문자로 바꾼 뒤 부분 일치).
#  - 되살리기: 빠지는 검색어 가운데 교육청 후보 CSV의 '키워드' 칸에 나타나고(=실제로 계약을 끌어왔고)
#    그 계약이 정제본(*_refined.csv)에 살아남은 적이 있는 것은 보고서에 따로 적는다. 되살릴지는 사람이 정한다(--revive 파일).
import argparse, csv, glob, importlib.util, os, re, collections

DEFAULTS = ["에듀테크", "코스웨어", "인공지능", "소프트웨어", "라이선스", "라이센스", "구독", "플랫폼", "GPT",
            "어도비", "디지털교과서", "교육자료", "챗봇", "메타버스", "코딩", "AIDT", "클래스팅", "패들렛", "캔바"]
SRC_LIST, OUT, REPORT = "edzip_brand_keywords.txt", "keywords_final.txt", "keywords_final_report.md"
norm = lambda x: re.sub(r"[\s·\-]+", "", x or "").lower()


def names():
    csv.field_size_limit(10 ** 8)
    seen = set()
    for p in ["s2b_all.csv"] + sorted(glob.glob("nara_full_*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            n = norm(r.get("계약명"))
            if n and n not in seen:
                seen.add(n)
                yield n


def appearing(kws):
    """계약명에 한 번이라도 나타나는 검색어 — 두 글자 머리로 색인해 부분 일치를 찾는다. 찾은 검색어는 색인에서 뺀다."""
    idx = collections.defaultdict(list)
    for k in kws:
        nk = norm(k)
        if len(nk) >= 2:
            idx[nk[:2]].append((nk, k))
    found = set()
    for s in names():
        for i in range(len(s) - 1):
            lst = idx.get(s[i:i + 2])
            if not lst:
                continue
            hit = [t for t in lst if s.startswith(t[0], i)]
            if hit:
                for t in hit:
                    found.add(t[1]); lst.remove(t)
                if not lst:
                    del idx[s[i:i + 2]]
    return found


def pulled():
    """교육청 후보 CSV에서 검색어별로 끌어온 행 수와, 그 가운데 정제본에 살아남은 행 수"""
    refined = set()
    for p in glob.glob("*_refined.csv"):
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            refined.add(norm(r.get("계약명")))
    got, kept = collections.Counter(), collections.Counter()
    for p in glob.glob("*_candidates.csv"):
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            k = (r.get("키워드") or "").strip()
            if not k or k == "(전수)":
                continue
            got[k] += 1
            if norm(r.get("계약명")) in refined:
                kept[k] += 1
    return got, kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="keywords_final.txt를 쓴다(없으면 보고서만)")
    ap.add_argument("--revive", help="되살릴 검색어를 줄 단위로 적은 파일")
    ap.add_argument("--include-newer", action="store_true",
                    help="9/11 이후 판정 규칙에 새로 생긴 표기 가운데 S2B·나라장터에 나타나는 것도 넣는다(2026-09-20 사용자 결정)")
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("mk", "make_keywords.py")
    mk = importlib.util.module_from_spec(spec); spec.loader.exec_module(mk)
    regen, br, _ = mk.build()
    cur = [l.strip() for l in open(SRC_LIST, encoding="utf-8") if l.strip()]
    pool = list(dict.fromkeys(DEFAULTS + cur))
    def branch(k):
        if k in DEFAULTS: return "기본 검색어"
        if k in br["에듀집 제품명"]: return "에듀집 제품명"
        if k in br["에듀집 회사명"]: return "에듀집 회사명"
        return "규칙 표기 변형"
    newer = sorted(set(regen) - set(cur))            # 9/11 이후 판정 규칙에 새로 생긴 표기(참고용)
    found = appearing(pool + newer)
    revive = [l.strip() for l in open(a.revive, encoding="utf-8") if l.strip()] if a.revive else []
    final = [k for k in pool if k in found or k in DEFAULTS or k in revive]
    if a.include_newer:
        final += [k for k in newer if k in found and k not in final]   # 기본 검색어와 겹치는 새 표기는 한 번만
    # 가운뎃점이 든 표기는 검색창에서 글자 그대로는 걸리지 않는다(규칙의 [\s·]?를 펼친 꼴: '3D·스·팀·펜').
    # 위 대조가 가운뎃점을 무시해서 '나타난다'고 본 것뿐이다. 붙여 쓴 꼴이나 띄어 쓴 꼴이 목록에 있으면 빼고,
    # 없으면 띄어 쓴 꼴로 바꾼다. 글자마다 점이 낀 것은 띄어 써도 걸리지 않으므로 붙여 쓴 꼴로 바꾼다.
    fs, out = set(final), []
    for k in final:
        if "·" not in k:
            out.append(k); continue
        compact, spaced = k.replace("·", ""), re.sub(r"\s+", " ", k.replace("·", " ")).strip()
        perchar = bool(re.search(r"(?:[가-힣]·){2,}[가-힣]", k))
        if compact in fs or (not perchar and spaced in fs):
            continue
        alt = compact if perchar else spaced
        if alt not in fs:
            fs.add(alt); out.append(alt)
    final = out
    dropped = [k for k in pool if k not in set(final)]
    got, kept = pulled()
    risky = sorted(((kept[k], got[k], k) for k in dropped if kept[k] > 0), reverse=True)
    cnt_all, cnt_fin = collections.Counter(map(branch, pool + [k for k in final if k not in pool])), collections.Counter(map(branch, final))
    L = ["# 확정 검색어 목록 보고", "",
         f"- 되살린 검색어 {len([k for k in revive if k in pool]):,}종 · 9/11 이후 새 규칙 표기 {len([k for k in final if k not in pool]):,}종 포함" if (revive or a.include_newer) else "- (되살림·새 표기 없음)",
         f"- 모집단 {len(pool):,}종(현재 판 {len(cur):,} + 기본 {len(DEFAULTS)}, 겹침 제외) → **확정 {len(final):,}종**, 빠짐 {len(dropped):,}종",
         "- 대조: S2B 전수·나라장터 전수 계약명에 부분 일치(대소문자·띄어쓰기·가운뎃점·하이픈 무시). 기본 19종은 무조건 포함.", "",
         "| 갈래 | 모집단 | 확정 |", "|---|---:|---:|"]
    for b in ("기본 검색어", "에듀집 제품명", "에듀집 회사명", "규칙 표기 변형"):
        L.append(f"| {b} | {cnt_all[b]:,} | {cnt_fin[b]:,} |")
    L += ["", "갈래가 겹치는 검색어는 제품명 → 회사명 → 규칙 표기 순으로 한 번만 센다. 현재 판에만 있고 오늘 규칙으로는 다시 만들어지지 않는 것은 규칙 표기로 센다.", "",
          f"## 빠지는 검색어 가운데 교육청 자료에서 계약을 끌어와 정제본에 남긴 적이 있는 것 — {len(risky)}종",
          "(정제본 생존 행 수 / 끌어온 후보 행 수). 되살릴 후보다.", ""]
    L += [f"- {k} — {kp:,} / {g:,}" for kp, g, k in risky]
    nf = [k for k in newer if k in found]
    L += ["", f"## 참고: 9/11 이후 판정 규칙에 새로 생긴 표기 {len(newer)}종 가운데 S2B·나라장터에 나타나는 것 — {len(nf)}종",
          "현재 판(3,964종)에 없어 모집단 밖이다. 넣을지는 따로 정한다.", "", ", ".join(nf)]
    open(REPORT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    if a.write:
        open(OUT, "w", encoding="utf-8").write("\n".join(final) + "\n")
    print(f"확정 {len(final):,}종 / 모집단 {len(pool):,}종 · 되살릴 후보 {len(risky)}종 · 새 표기 중 등장 {len(nf)}종 → {REPORT}")


if __name__ == "__main__":
    main()
