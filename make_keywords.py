# 시도교육청 계약공개는 검색어로만 훑을 수 있다. 그 검색어를 한곳에서 만든다.
# 사용: python3 make_keywords.py   → edzip_brand_keywords.txt
#
# 세 갈래를 모은다.
#   1) 에듀집 제품명       — 등록된 제품 이름 그대로
#   2) 에듀집 회사명       — 계약명에 회사 이름만 적히는 일이 잦다((주)·주식회사는 뗀다)
#   3) 판정 규칙의 표기 변형 — build_data.py에 적어 둔 갈래를 펼친다.
#      '[챗쳇겟][\s\-]?지피티'는 챗지피티·쳇지피티·겟지피티·챗 지피티…로 펼쳐진다.
#      듀오링고/듀얼링고처럼 틀리기 쉬운 표기가 규칙에 이미 있으므로 그대로 검색어가 된다.
import csv, itertools, os, re

OUT = "edzip_brand_keywords.txt"
MAXALT = 64                     # 한 규칙에서 펼칠 최대 가짓수 (조합 폭발 막기)


def expand(pat):
    """정규식 한 갈래를 검색어 후보들로 펼친다"""
    pat = re.sub(r"\(\?[:=!][^)]*\)", "", pat)       # (?:…) (?=…) (?!…)
    pat = re.sub(r"\(\?<[=!][^)]*\)", "", pat)       # (?<=…) (?<!…)
    pat = pat.replace("\\b", "")
    parts, i = [], 0
    while i < len(pat):
        ch = pat[i]
        if ch == "[":                                 # 글자 묶음 → 갈래
            j = pat.index("]", i)
            body = pat[i + 1:j]
            i = j + 1
            opt = pat[i] in "?*" if i < len(pat) else False
            if opt:
                i += 1
            chars = [c for c in re.sub(r"\\s", " ", body).replace("\\-", "-") if c != "\\"]
            parts.append(([""] if opt else []) + chars)
        elif ch == "\\" and i + 1 < len(pat) and pat[i + 1] == "s":
            i += 2
            if i < len(pat) and pat[i] in "?*+":
                i += 1
            parts.append(["", " "])                   # 공백은 있어도 없어도 된다
        elif ch in "?*+":
            if parts and len(parts[-1]) == 1:         # 앞 글자가 없어도 된다
                parts[-1] = ["", parts[-1][0]]
            i += 1
        elif ch in "(){}^$":
            i += 1
        else:
            parts.append([ch])
            i += 1
    n = 1
    for p in parts:
        n *= max(1, len(p))
        if n > MAXALT:
            return []
    return ["".join(c).strip() for c in itertools.product(*[p or [""] for p in parts])]


def from_rules():
    src = open("build_data.py", encoding="utf-8").read()
    ns = {"__name__": "rules"}
    exec(compile(src[:src.index("rows = list(csv.reader(open(SRC")], "rules", "exec"), ns)
    out = set()
    for _t, pat in ns["SPECIFIC_RULES"]:
        for alt in re.split(r"\|(?![^\[]*\])", pat):
            for w in expand(alt):
                w = re.sub(r"\s+", " ", w).strip()
                # 판정 규칙에서 온 말은 두 글자여도 살린다 — 캔바·젭처럼 짧은 제품이 있다.
                # (에듀집 제품·회사 이름은 세 글자부터: 두 글자면 아무 계약에나 걸린다)
                if 2 <= len(w) <= 30 and re.fullmatch(r"[0-9A-Za-z가-힣][0-9A-Za-z가-힣 ·\-/]*", w):
                    out.add(w)
    return out


def from_edzip():
    prod, comp = set(), set()
    core = lambda x: re.sub(r"\(주\)|주식회사|㈜|\(유\)|유한회사|유한책임회사|\(재\)|재단법인|\(사\)|사단법인", "", x or "").strip()
    for p in ("edzip_company.csv",):
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            n = (r.get("제품명") or "").strip()
            c = core((r.get("회사명") or "").strip())
            # 두 글자 이름은 아무 계약에나 걸린다 — 판정 규칙에 든 것만 따로 인정한다
            if 3 <= len(n) <= 40:
                prod.add(n)
            if 3 <= len(c) <= 30 and not re.fullmatch(r"\(?[사재유주]\)?", c):
                comp.add(c)
    return prod, comp


def main():
    rules = from_rules()
    prod, comp = from_edzip()
    # 너무 흔한 낱말은 그 시도 계약을 통째로 끌어와 수집이 끝나지 않는다
    # 제품 이름이지만 보통명사와 겹쳐 엉뚱한 계약을 잔뜩 끌어오는 말들.
    # 경기 2025년에서 '프로' 3,339건 · '유아' 695 · '의자' 483 · '가구' 396건이 그랬다.
    STOP = {"교육", "학교", "학습", "수업", "프로그램", "콘텐츠", "시스템", "서비스",
            "소프트웨어", "온라인", "디지털", "스마트", "플랫폼", "센터", "미디어", "에듀",
            "프로", "유아", "의자", "가구", "책상", "도서", "카드", "블록", "키트", "노트",
            "수학", "영어", "과학", "미술", "음악", "체육", "국어", "한자", "독서", "진로",
            "로봇", "소파", "영상", "자막", "증강", "침대", "러닝", "AI", "SW", "엑셀", "워드"}
    # 에듀집 제품명에 보이지 않는 글자(U+200B 등)와 ®·™가 섞여 있다. 그대로 검색하면
    # 서버가 사실상 전부를 돌려준다 — 광주에서 한 검색어가 301페이지를 끌어왔다(2026-09-11).
    INVIS = re.compile(r"[\u200b-\u200f\u2060-\u206f\ufeff\u00ad\u00a0]|[®™©℠]")
    def clean(k):
        return re.sub(r"\s+", " ", INVIS.sub(" ", k)).strip()
    allk = sorted({clean(k) for k in (rules | prod | comp)} - STOP - {""})
    open(OUT, "w", encoding="utf-8").write("\n".join(allk) + "\n")
    print(f"{OUT} — {len(allk):,}종 "
          f"(규칙 표기 {len(rules):,} · 에듀집 제품 {len(prod):,} · 회사 {len(comp):,})")
    for w in ("듀얼링고", "듀오링고", "쳇GPT", "챗지피티", "겟지피티", "캔바", "패들렛", "클리포"):
        print(f"   {w}: {'있음' if w in allk else '없음'}")


if __name__ == "__main__":
    main()
