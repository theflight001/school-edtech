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


def _close(p, i):
    """p[i]가 '('일 때 짝이 되는 ')'의 자리 — 글자 묶음 [...] 안의 괄호와 \\ 이스케이프는 세지 않는다"""
    depth, j = 0, i
    while j < len(p):
        c = p[j]
        if c == "\\":
            j += 2
            continue
        if c == "[":
            j = p.index("]", j + 1) + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return len(p) - 1


def _split_top(p):
    """괄호·글자 묶음 밖의 '|'에서만 가른다"""
    parts, depth, cur, j = [], 0, [], 0
    while j < len(p):
        c = p[j]
        if c == "\\":
            cur.append(p[j:j + 2]); j += 2; continue
        if c == "[":
            k = p.index("]", j + 1) + 1
            cur.append(p[j:k]); j = k; continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        if c == "|" and depth == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(c)
        j += 1
    parts.append("".join(cur))
    return parts


def _class(body):
    """글자 묶음을 글자들로 — 범위(가-힣, 0-9)나 부정([^...])은 셀 수 없으니 None"""
    if body.startswith("^") or re.search(r"[^\\]-[^\]]", body.replace("\\-", "")):
        return None
    out, j = [], 0
    while j < len(body):
        if body[j] == "\\" and j + 1 < len(body):
            out.append(" " if body[j + 1] == "s" else body[j + 1]); j += 2
        else:
            out.append(body[j]); j += 1
    return out


def _alts(p):
    """괄호 깊이를 지키며 정규식 한 덩어리를 문자열들로 펼친다"""
    result = []
    for b in _split_top(p):
        seqs, i = [""], 0
        while i < len(b):
            c = b[i]
            opts = None
            if c == "(":
                j = _close(b, i)
                inner = b[i + 1:j]
                if inner.startswith("?:"):
                    inner = inner[2:]
                elif inner.startswith("?"):
                    inner = ""                     # (?i) 따위
                opts = _alts(inner) or [""]
                i = j + 1
            elif c == "[":
                j = b.index("]", i + 1)
                opts = _class(b[i + 1:j]) or [""]
                i = j + 1
            elif c == "\\":
                n = b[i + 1] if i + 1 < len(b) else ""
                opts = [" "] if n == "s" else [""] if n in "bBdDwW" else [n]
                i += 2
            elif c in "^$":
                i += 1; continue
            elif c == ".":
                i += 1
                if i < len(b) and b[i] in "*+?":
                    i += 1
                continue
            elif c == "{":
                i = b.index("}", i) + 1; continue
            else:
                opts = [c]; i += 1
            # 뒤따르는 수량자: ?·* 는 없어도 된다
            if i < len(b) and b[i] in "?*+":
                if b[i] in "?*":
                    opts = [""] + [o for o in opts if o != ""]
                i += 1
                if i < len(b) and b[i] == "?":
                    i += 1
            seqs = [a + o for a in seqs for o in opts]
            if len(seqs) > MAXALT * 4:
                seqs = seqs[:MAXALT * 4]
        result.extend(seqs)
    return result


def expand_rule(pat):
    """판정 규칙 하나를 검색어 후보로 펼친다.
    - (?!…) (?<!…) '이 말이 있으면 아니다'는 버린다 — 예전엔 이게 조각조각 검색어로 새어
      가방·커피·모듈 같은 말이 들어갔고, 강원 서버가 '모듈'에 500을 냈다(2026-09-11).
    - (?=…) '이 말이 있어야 한다'는 따로 펼쳐 더한다 — Tinkercad·교보문고처럼 제품명이
      거기 들어 있는 규칙이 있다.
    - (?:A|B)는 괄호 짝을 맞춰 곱해 펼친다 — 예전엔 괄호를 안 보고 '|'로 쪼개 Gamma·네프론·
      MS Office처럼 괄호 안 첫 갈래가 버려졌다."""
    main, pos, i = [], [], 0
    while i < len(pat):
        if pat.startswith(("(?=", "(?!", "(?<=", "(?<!"), i):
            j = _close(pat, i)
            head = 3 if pat[i + 2] in "=!" else 4
            if pat[i:i + head] == "(?=":
                pos.append(re.sub(r"^\.\*", "", pat[i + head:j]))
            i = j + 1
            continue
        main.append(pat[i]); i += 1
    out = []
    for piece in ["".join(main)] + pos:
        out.extend(_alts(piece))
    return out


def from_rules():
    src = open("build_data.py", encoding="utf-8").read()
    ns = {"__name__": "rules"}
    exec(compile(src[:src.index("rows = list(csv.reader(open(SRC")], "rules", "exec"), ns)
    out = set()
    for _t, pat in ns["SPECIFIC_RULES"]:
        for w in expand_rule(pat):
            if True:
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
    # 시도교육청 검색창은 특수문자와 긴 이름을 제대로 못 다룬다(2026-09-11 발견).
    #  - 괄호·/·&·+·주소가 든 검색어에 서버가 400·409·500을 내고 수집기가 통째로 죽었다(경북·대전·강원).
    #  - 낱말이 여럿인 이름은 낱말 하나만 맞아도 다 돌려줘 한 검색어가 301쪽을 끌어왔다(광주).
    #  - '11'·'MS'처럼 짧은 말은 그 시도 계약을 통째로 끌어왔다(강원 '11' 한 마디에 1,812건).
    # 그래서 주소와 괄호 속을 걷고, 특수문자는 띄어쓰기로 바꾸고, 짧은 말과 숫자만인 말은 뺀다.
    # 긴 이름은 앞 세 낱말까지만 쓴다 — 제품을 알아보는 핵심은 대개 앞에 온다.
    URL = re.compile(r"https?://\S+|www\.\S+|\b[\w-]+\.(?:com|co\.kr|kr|net|org|io)\b\S*", re.I)
    PAREN = re.compile(r"[\(\[（【][^\)\]）】]*[\)\]）】]")
    # 밑줄도 띄어쓰기로 바꾼다 — 검색이 데이터베이스 LIKE로 돌면 _는 "아무 글자 하나"라는 뜻이다
    # (광주가 "스파이크_에센셜앱" 앞에서 멈췄다, 2026-09-11).
    PUNCT = re.compile(r"[^\w가-힣\s\-·]|_")
    GENERIC_WORD = re.compile(r"^(?:초등|중등|고등|초등학교|중학교|고등학교|중학|고교|유치원|특수|\d+학년|\d+학기|\d+|"
                              r"학년|학기|국어|영어|수학|과학|사회|정보|음악|미술|체육|도덕|기술|가정|실과|한문|역사|"
                              r"지리|통합|공통|AI|디지털|인공지능|교과서|교육자료|교재|자료|교사용|학생용|지도서|학습|"
                              r"교육|수업|활동|공동|시도교육청|\d+개|개정|개정판|초중고|전학년|전과목|상|하)$", re.I)
    DOMAIN_ONLY = re.compile(r"^(?:https?://)?(?:www\.)?([\w가-힣-]+)\.(?:com|co\.kr|kr|net|org|io)/?$", re.I)
    def clean(k, trim=True):
        k = INVIS.sub(" ", k).strip()
        # 이름 자체가 주소인 제품(Typing.com·Classwork.com)은 이름 부분을 남긴다.
        # 처음엔 주소를 통째로 지워 이런 제품 6종을 잃었다(2026-09-11).
        d = DOMAIN_ONLY.match(k)
        if d:
            k = d.group(1)
        k = URL.sub(" ", k)
        k = PAREN.sub(" ", k)
        k = PUNCT.sub(" ", k)
        # 하이픈은 띄어쓰기와 같이 본다 — 규칙의 [\s\-]?를 펼치면 'Copilot-MS 365'·'Copilot MS 365'가
        # 따로 생겨 서버에 같은 걸 두 번 묻게 된다.
        k = k.replace("-", " ")
        k = re.sub(r"\s+", " ", k).strip(" -·")
        words = k.split()
        if trim and len(words) > 3:
            k = " ".join(words[:3])
        return k
    def usable(k, generic_ok=False):
        # 빼는 것은 숫자만인 말('11'), 영문 두 글자 이하('MS'), 한 글자뿐이다.
        # 두 글자 한글 제품명(캔바·노션·알공)과 세 글자 영문 약칭(ZEP·EBS)은 남긴다 —
        # 처음엔 '3글자 미만'으로 걸렀다가 캔바·ZEP까지 잘라 먹었다(2026-09-11).
        core = re.sub(r"[\s\-·]", "", k)
        if len(core) < 2 or core.isdigit():
            return False
        if re.fullmatch(r"[A-Za-z0-9]{1,2}", core):
            return False
        # 학교급·학년·학기·과목·숫자로만 된 말은 뺀다. 긴 교과서 이름을 세 낱말로 자르면
        # '초등학교 6학년 2학기'·'중학교 수학 1'이 남는데, 준비물·교재 계약을 통째로 끌어온다.
        words = k.split()
        if not generic_ok and len(words) >= 2 and all(GENERIC_WORD.match(w) for w in words):
            return False
        return True
    # 규칙 표기는 판정 규칙에 사람이 적어 둔 것이라 자르지도 흔한 말로 거르지도 않는다
    # ('AI 디지털 교과서'가 그렇다 — 자료에서 가장 큰 범주다). 특수문자만 다듬는다.
    kw_rules = {c for c in (clean(k, trim=False) for k in rules) if usable(c, generic_ok=True)}
    kw_edzip = {c for c in (clean(k) for k in (prod | comp)) if usable(c)}
    pool = sorted((kw_rules | kw_edzip) - STOP)
    # 띄어쓰기·가운뎃점만 다른 변형은 무리마다 둘만 남긴다 — '다 띄운 것'과 '다 붙인 것'.
    # 교육청 검색은 글자 그대로 찾아서 변형이 아예 쓸모없진 않지만, 규칙의 \s?를 곱해 펼치면
    # '11개 시도교육청 공동 구축'이 여덟 갈래로 늘어 같은 걸 여덟 번 묻게 된다(2026-09-11).
    groups = {}
    for k in pool:
        groups.setdefault(re.sub(r"[\s·]+", "", k).lower(), []).append(k)
    allk = []
    for vs in groups.values():
        if len(vs) <= 2:
            allk.extend(vs)
            continue
        spaced = max(vs, key=lambda v: (len(re.findall(r"[\s·]", v)), v))
        compact = min(vs, key=lambda v: (len(re.findall(r"[\s·]", v)), v))
        allk.extend({spaced, compact})
    allk = sorted(allk)
    open(OUT, "w", encoding="utf-8").write("\n".join(allk) + "\n")
    print(f"{OUT} — {len(allk):,}종 "
          f"(규칙 표기 {len(rules):,} · 에듀집 제품 {len(prod):,} · 회사 {len(comp):,})")
    for w in ("듀얼링고", "듀오링고", "쳇GPT", "챗지피티", "겟지피티", "캔바", "패들렛", "클리포"):
        print(f"   {w}: {'있음' if w in allk else '없음'}")


if __name__ == "__main__":
    main()
