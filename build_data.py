# CSV → data.js 변환 스크립트 (정적 프로토타입용)
# 사용: python3 build_data.py  → data.js 생성
import csv, html, json, re, collections, os

SRC = "db_export.csv"
OUT = "data.js"
MASTER = "school_master.json"

# 개명 확인된 학교 별칭 (DB 표기 → NEIS 현재 교명). NEIS 대조로 확정된 것만 넣을 것.
ALIAS = {
    "한국과학영재학교(KSA)": "한국과학영재학교",
    "미림여자정보과학고등학교": "미림마이스터고등학교",
    "부산자동차고등학교": "부산자동차마이스터고등학교",
    "광주자동화설비공업고등학교": "광주자동화설비마이스터고등학교",
    # 2026-07-22 웹 검증 확정분 (교육청 공고·언론 근거 확인, 상세 근거는 검증 기록 참조)
    "한양공업고등학교": "한양과학기술고등학교",          # 2026.3 교명 변경
    "경주공업고등학교": "한국반도체마이스터고등학교",     # 2026.3 마이스터고 전환
    "논산공업고등학교": "국방항공고등학교",              # 2025.3 교명 변경
    "인천정보과학고등학교": "인천반도체고등학교",         # 2024.3 교명 변경
    "태백기계공업고등학교": "한국항공고등학교",           # 2024.3 교명 변경
    "평촌공업고등학교": "평촌과학기술고등학교",           # 2023.3 교명 변경
    "한림공업고등학교": "한림항공우주고등학교",           # 2026.3 교명 변경
    "예산전자공업고등학교": "충남반도체마이스터고등학교",  # 2025.3 마이스터고 전환
    "순천전자고등학교": "순천미래과학고등학교",           # 2023.3 교명 변경
    "성남금융고등학교": "분당아람고등학교",              # 2023.3 교명 변경
    "송원여자상업고등학교": "송원미래인재고등학교",       # 2026 교명 변경·남녀공학 전환
    "상지여자상업고등학교": "상지미래경영고등학교",       # 2023.3 교명 변경 (소재지 경북 상주)
    "대중금속공업고등학교": "대구스마트고등학교",         # 2026.3 교명 변경
    "인천중앙여자상업고등학교": "인천중앙여자고등학교",    # 2024 교명 변경
    "경일관광경영고등학교": "경일고등학교",              # 2026.3 교명 환원 (경기 안산)
    "부경보건고등학교": "학력인정부경보건고등학교",       # NEIS 등재명 차이(동일 학교)
    # 2026-07-27 웹 검증 확정분
    "보영여자중학교": "한빛누리중학교",                  # 2023.3 교명 변경·남녀공학 전환 (경기 동두천)
    "보영여자고등학교": "한빛누리고등학교",               # 2023.3 교명 변경·남녀공학 전환 (경기 동두천)
    "화곡보건경영고등학교": "서울홍신고등학교",        # 2024.3 교명 변경 (제보 2026-08-11, 마스터 대조 확인)
    # 2026-08-11 웹 검증 확정분 — 조달 기록의 옛 교명을 NEIS 현재 교명으로 잇는다
    "파주여자고등학교": "정목고등학교",                       # 2026.3 교명 변경 (경기 파주)
    "경북소프트웨어고등학교": "경북소프트웨어마이스터고등학교",  # 2025.3 마이스터고 전환 (의성)
    "전북하이텍고등학교": "수소에너지고등학교",                 # 2025.3 교명 변경 (완주)
    "원주의료고등학교": "한국의료마이스터고등학교",             # 2026.3 교명 변경
    "영주동산고등학교": "한국미래산업고등학교",                 # 2023.3 교명 변경
    "충남인터넷고등학교": "한국국제비즈니스고등학교",           # 2026.3 교명 변경 (논산)
    "강서공업고등학교": "서울디지털콘텐츠고등학교",             # 2025.3 교명 변경 (서울 강서)
    "서울전자고등학교": "서울웹툰애니메이션고등학교",           # 2023.9 교명 변경
    "김포제일공업고등학교": "김포과학기술고등학교",             # 2024.3 교명 변경
    "안강전자고등학교": "경북모빌리티고등학교",                 # 2026.3 교명 변경 (경주 안강)
    "대구달서공업고등학교": "대구하이텍고등학교",               # 2023.3 교명 변경
    "동의공업고등학교": "동의고등학교",                        # 2024.3 교명 변경·남녀공학 전환 (부산)
    "진안공업고등학교": "한국기술부사관고등학교",               # 군특성화고 전환에 따른 교명 변경
    "강구정보고등학교": "경북이커머스고등학교",                 # 2026.3 교명 변경 (영덕 강구)
    "소양고등학교": "강원생명과학고등학교",                     # 2023.3 교명 변경 (춘천)
    "미양고등학교": "솔샘고등학교",                            # 2023.3 교명 변경 (서울 강북)
    "목포성신고등학교": "목포조리과학고등학교",                 # 2026.3 교명 변경
    "서천여자정보고등학교": "한국미래문화고등학교",             # 2026.3 교명 변경
    "서울항공비즈니스고등학교": "서울백영고등학교",             # 2025.3 교명 변경
    "숭신여자고등학교": "숭신고등학교",                        # 2026.3 남녀공학 전환·교명 변경 (성남)
    "숭신여자중학교": "숭신중학교",                            # 2026.3 남녀공학 전환·교명 변경 (성남)
    "여주여자중학교": "여흥중학교",                            # 2026.3 남녀공학 전환·교명 변경
    "성의여자중학교": "공학성의중학교",                        # 2026.3 남녀공학 전환·교명 변경 (김천)
    "경상여자중학교": "대구청라중학교",                        # 2024.3 남녀공학 전환·교명 변경
    "영훈중학교": "영훈국제중학교",                            # 국제중 전환 (서울 성북)
    # NEIS 등재명과 표기만 다른 것 (개명이 아니라 같은 학교의 정식 명칭)
    "온양한올고등학교": "한올고등학교",                        # NEIS에 '온양' 없이 등재 (충남 아산)
    "온양한올중학교": "한올중학교",                            # 〃
    "한림중실업연예예술고등학교": "학력인정 한림연예예술고등학교",  # 같은 학교의 다른 교육과정 표기
    "전통예술고등학교": "국립전통예술고등학교",                 # 문체부 소속 국립학교
    "남인천고등학교": "학력인정남인천고등학교",
    "건양중학교": "건양대학교병설건양중학교",                   # 충남 논산
    "석천중학교": "김천석천중학교",                            # 경북 김천
    "서울특별시교육청해성여자고등학교": "해성여자고등학교",
    "한국과학기술원부설한국과학영재학교": "한국과학영재학교",
    # 2026-08-02 웹 검증 확정분
    "김화공업고등학교": "한국국방과학고등학교",            # 2026.3 마이스터고 전환 (강원 철원)
    "의정부공업고등학교": "한국모빌리티고등학교",          # 2026.3 교명 변경 (경기 의정부)
    "마산의신여자중학교": "의신중학교",                   # 2025.3 교명 변경·남녀공학 전환 (경남 창원)
    "대구전자공업고등학교": "대구반도체마이스터고등학교",   # 2025.3 마이스터고 전환 (대구 달서)
    # 2026-08-02 웹 검증 확정분 (부산 계약공개 수집 중 발견)
    "부산여자상업고등학교": "해연여자고등학교",             # 2026.3 교명 변경 (부산 동래)
    "해운대공업고등학교": "부산해군과학기술고등학교",        # 2025.3 교명 변경 (부산 해운대)
    "금정전자고등학교": "금샘고등학교",                    # 2024.3 교명 변경 (부산 금정)
    "부일외국어고등학교": "부일고등학교",                  # 자사고 전환에 따른 교명 변경 (부산 해운대)
    # 2026-08-03 웹 검증 확정분 (인천 브랜드 스윕·대구 수집 중 발견)
    "인천정보산업고등학교": "인천반도체고등학교",           # 2020 인천정보과학고 → 2024 인천반도체고
    "부일여자중학교": "인천동수중학교",                   # 2023 교명 변경·남녀공학 전환 (인천 부평)
    # 2026-08-04 웹 검증 확정분 (울산 수집 중 발견)
    "울산중앙여자고등학교": "울산가온고등학교",            # 2025.3 교명 변경·남녀공학 전환
    "명덕여자중학교": "명덕중학교",                       # 2026.3 교명 변경·남녀공학 전환 (울산 동구)
}

SIDO_PREFIX = {"서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천", "광주": "광주",
               "대전": "대전", "울산": "울산", "세종": "세종", "경기": "경기", "강원": "강원",
               "충북": "충청북", "충남": "충청남", "전북": "전라북|전북", "전남": "전라남",
               "경북": "경상북", "경남": "경상남", "제주": "제주"}

master_by_name = collections.defaultdict(list)
master_by_nkey = collections.defaultdict(list)
# 띄어쓰기·기호만 다른 표기를 함께 찾는다 ('경화여자EnglishBusiness고' ↔ '경화여자English Business고')
def _nkey(n):
    return re.sub(r"[\s·ㆍ\-_()（）]", "", n or "")
if os.path.exists(MASTER):
    for s in json.load(open(MASTER, encoding="utf-8"))["schools"]:
        master_by_name[s["name"]].append(s)
        master_by_nkey[_nkey(s["name"])].append(s)

# 시도 접두어가 붙거나 빠진 표기 ('인천재능고' ↔ '재능고', '담방초' ↔ '인천담방초').
# 다른 시도에 같은 이름이 있을 수 있으니 후보가 딱 하나일 때만 인정한다.
_SIDO_PFX = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
             "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
def lookup_school(name):
    """교명 하나로 마스터에서 찾는다 — 정확 일치 → 띄어쓰기 무시 → 시도 접두어 가감"""
    nm = ALIAS.get(name, name)
    cands = master_by_name.get(nm, [])
    if cands:
        return cands
    cands = master_by_nkey.get(_nkey(nm), [])
    if len(cands) == 1:
        return cands
    alts = []
    for p in _SIDO_PFX:
        alts.append(p + nm)
        if nm.startswith(p):
            alts.append(nm[len(p):])
    hit = [c for a in alts for c in master_by_nkey.get(_nkey(a), [])]
    return hit if len(hit) == 1 else []

def find_school(name, region):
    cands = lookup_school(name)
    if len(cands) == 1:
        return cands[0]
    if len(cands) > 1:
        tok = region.split()[0] if region else ""
        pat = SIDO_PREFIX.get(tok)
        if pat:
            f = [c for c in cands if re.match(pat, c["sido"])]
            if len(f) == 1:
                return f[0]
    return None

_by_name = master_by_name
# 주의: 광주·전남은 마스터에 '전남광주통합특별시(광주)' 형태로 들어 있어 접두 비교가 통하지 않는다
SIDO_FROM_ORG = [("서울", "서울"), ("부산", "부산"), ("대구", "대구"), ("인천", "인천"),
                 ("광주", r".*\(광주\)"), ("대전", "대전"), ("울산", "울산"), ("세종", "세종"),
                 ("경기", "경기"), ("강원", "강원"), ("충청북", "충청북"), ("충북", "충청북"),
                 ("충청남", "충청남"), ("충남", "충청남"), ("전북", "전북|전라북"),
                 ("전라북", "전북|전라북"), ("전라남", r".*\(전남\)"), ("전남", r".*\(전남\)"),
                 ("경상북", "경상북"), ("경북", "경상북"), ("경상남", "경상남"),
                 ("경남", "경상남"), ("제주", "제주")]

def resolve_school(row):
    """학교코드가 비어 있는 행을 관할 시도교육청 기준으로 다시 매칭한다."""
    if row.get("학교코드"):
        return row
    name = (row.get("학교명") or "").strip()
    org = (row.get("수요기관") or "").strip()
    toks = org.split()
    head = toks[0] if toks else ""            # 예: '경기도교육청' — 광역 단위가 확실한 토큰
    name = ALIAS.get(name, name)              # 개명 학교 반영
    cands = _by_name.get(name, [])
    if not cands and len(toks) > 1:
        # 교명에 띄어쓰기가 있어 마지막 토큰만 잘린 경우 ('… 사범대학 부설고등학교')
        for k in (2, 3, 4):
            if len(toks) >= k:
                cand_name = "".join(toks[-k:])
                cand_name = ALIAS.get(cand_name, cand_name)
                if _by_name.get(cand_name):
                    cands, name = _by_name[cand_name], cand_name
                    break
    if not cands:
        # '인천재능고등학교'처럼 시도 접두어가 교명에 붙은 표기 보정
        for pre, _ in SIDO_FROM_ORG:
            if name.startswith(pre) and _by_name.get(name[len(pre):]):
                cands = _by_name[name[len(pre):]]
                name = name[len(pre):]
                break
    if not cands and len(toks) > 1:
        # '경상국립대학교 대학 사범대학 부설고등학교' — 붙이면 '대학'이 한 번 더 낀다
        for k in (2, 3, 4):
            if len(toks) >= k:
                cand_name = re.sub(r"대학교대학", "대학교", "".join(toks[-k:]))
                for v in (cand_name, "국립" + cand_name):   # NEIS는 국립대 부설교에 '국립'을 붙인다
                    if _by_name.get(v):
                        cands, name = _by_name[v], v
                        break
                if cands:
                    break
    if not cands:
        # 교명 앞에 시·군 이름이 붙은 표기 ('파주광일중' ↔ '광일중').
        # 아무 말이나 떼지 않는다 — 수요기관의 교육지원청 이름에 그 지명이 있을 때만.
        loc = re.sub(r"(교육지원청|교육청)$", "", toks[-2] if len(toks) > 2 else head)
        loc = re.sub(r"^(경기도|강원특별자치도|강원도|충청남도|충청북도|경상남도|경상북도|"
                     r"전라남도|전라북도|전북특별자치도|제주특별자치도|제주도)", "", loc)
        if len(loc) >= 2 and name.startswith(loc) and _by_name.get(name[len(loc):]):
            c2 = _by_name[name[len(loc):]]
            if len(c2) == 1:
                cands, name = c2, name[len(loc):]
    if not cands:
        # 띄어쓰기·기호만 다른 표기 ('경화여자EnglishBusiness고' ↔ '경화여자English Business고')와
        # 시도 접두어가 반대로 붙은 표기 ('담방초' ↔ '인천담방초') — 후보가 하나일 때만
        alt = lookup_school(name)
        if len(alt) == 1:
            cands, name = alt, alt[0]["name"]
    if len(cands) > 1 and head:
        for kw, pat in SIDO_FROM_ORG:
            if head.startswith(kw):
                f = [c for c in cands if re.match(pat, c["sido"])]
                if len(f) == 1:
                    cands = f
                break
    if len(cands) > 1 and len(toks) > 1:
        # 같은 시도에 동명 학교가 여럿이면 교육지원청 지명으로 가른다 ('경기도수원교육청' → 수원시)
        mid = re.sub(r"(교육지원청|교육청|특별자치도|광역시|특별시|도)$", "", toks[-2] if len(toks) > 2 else toks[0])
        mid = re.sub(r"^(경기도|강원도|충청남도|충청북도|경상남도|경상북도|전라남도|전라북도|제주도)", "", mid)
        if len(mid) >= 2:
            f = [c for c in cands if mid in (c.get("address") or "")]
            if len(f) == 1:
                cands = f
    if len(cands) == 1:
        c = cands[0]
        row["학교명"], row["학교코드"] = name, c["code"]
        row["급별"], row["시도"] = c["level"], c["sido"]
    return row

# 주요 브랜드/제품군 태깅 규칙: (태그명, 정규식) — 제품/서비스명 + 내용 필드에서 탐지
# 제품명 태그 (제품/서비스명 + 내용에서 탐지) — 제품명을 그대로 태그로, 회사명 괄호 없이
SPECIFIC_RULES = [
    # '챗지피티'처럼 한글로 옮겨 적은 표기가 많다. 다만 GPT킬러·MonoGPT·타임리 GPT처럼
    # 다른 제품에 GPT가 붙는 경우가 있어, GPT 단독은 잡지 않는다.
    ("ChatGPT",            r"Chat[\s\-]?GPT|[챗쳇][\s\-]?GPT|[챗쳇겟][\s\-]?지피티|GPT[- ]?[45]|OpenAI"),
    # Google AI Pro/Ultra는 2025년 개편된 구글 AI 구독 요금제 공식 명칭(구 Gemini Advanced·Google One AI Premium)
    ("Google AI Pro",       r"구글 ?AI ?(?:PRO|프로|Ultra|울트라)|Google ?AI ?(?:Pro|Ultra)|Gemini ?Advanced|제미나이 ?어드밴스드"),
    ("Gemini",             r"Gemini|제미나이"),
    ("Claude",             r"Claude|클로드"),
    ("Replit",             r"\bReplit\b"),   # 한글 '리플릿'은 인쇄물을 뜻해 오탐
    ("카피킬러",            r"카피킬러|무하유"),
    ("GPT킬러",            r"GPT ?킬러"),
    ("Adobe",              r"Adobe|어도비|포토샵|Photoshop|일러스트레이터|Illustrator|프리미어"),
    ("AI·디지털 교육자료", r"AIDT|AI ?디지털 ?교과서|디지털교과서|AI[·:]? ?디지털 ?교육자료"),
    ("리로스쿨",            r"리로스쿨|riroschool"),
    ("구름EDU",            r"구름 ?EDU|goorm|구름에듀"),
    ("이음AI",             r"이음 ?AI|화이트소프트"),
    ("MS Office",          r"\bMS\b|Microsoft|마이크로소프트|MS ?Office|오피스 ?365|M365"),
    ("Google Workspace",   r"구글 ?워크스페이스|Google Workspace|구글 ?클래스룸|Google Classroom"),
    ("Notion",             r"노션|Notion"),
    ("Zoom",               r"\bZoom\b|줌 ?프로"),
    ("Canva",              r"Canva|캔바"),
    ("미리캔버스",          r"미리캔버스"),
    ("Padlet",             r"Padlet|패들렛"),
    ("하이러닝",            r"하이러닝|Hi-?Learning"),
    ("바당",               r"바당|BADANG"),
    ("클래스팅",            r"클래스팅|Classting"),
    # '레고월'은 레고 모양 벽 블록(인테리어 시공)이라 레고 에듀케이션과 무관하다
    # '레고'라는 낱말만으로는 브랜드 제품을 알 수 없다 — 레고체험존·레고의자·벽레고처럼
    # 일반 블록이나 시공물이 훨씬 많다. 교육용 제품이라는 신호가 있을 때만 태그를 붙인다.
    # '레고스파이크'처럼 줄여 쓴 표기도 레고 제품이다(스파이크 프라임·에센셜은 레고 전용 제품명)
    ("레고 에듀케이션",      r"레고 ?에듀케이션|LEGO ?Education|레고 ?스파이크|레고 ?SPIKE|"
                            r"스파이크 ?(?:프라임|에센셜)|SPIKE ?(?:Prime|Essential)|"
                            r"마인드스톰|Mindstorm|\bEV3\b|WeDo|위두 ?2|레고 ?[Ww]e[Dd]o|"
                            r"레고(?=[^가-힣]{0,8}(?:코딩|로봇|프로그래밍|교육용|SW|AI|인공지능))|"
                            r"(?:코딩|로봇|프로그래밍)[^가-힣]{0,8}레고"),
    ("듀오링고",            r"듀오 ?링고|듀얼 ?링고|\bDuolingo\b"),
    ("코디마스터",          r"코디마스터"),
    # 아이스크림 계열은 제품이 여럿이라 이름이 적힌 것만 각각 잡는다.
    #   홈런  = 아이스크림에듀의 AI 맞춤학습(가정·방과후)
    #   스쿨런 = 아이스크림에듀의 학교 수업용
    #   S      = 아이스크림미디어의 수업 플랫폼
    # 'S'는 뒤에 글자가 붙으면 다른 말이다 — 출처 문구의 'S2B'에 걸리지 않도록 막는다.
    # 제품 이름 없이 '아이스크림'만 적힌 것은 아이스크림몰에서 산 문구·교구·교재가 대부분이라
    # (수납 정리함·핸드벨·미술 플레이북 등) 브랜드만으로는 태그하지 않는다.
    ("아이스크림 홈런",     r"아이스크림 ?홈런|아이스크림 ?에듀|i-?Scream ?(?:홈런|home|edu)"),
    ("아이스크림 스쿨런",   r"아이스크림 ?스쿨런|\b스쿨런\b"),
    ("아이스크림 S",        r"아이스크림 ?[Ss](?![0-9A-Za-z가-힣])|i-?Scream ?[Ss](?![0-9A-Za-z])"),
    ("젭(ZEP)",            r"젭|\bZEP\b"),
    ("매쓰플랫",            r"매쓰플랫"),
    ("스쿨플랫",            r"스쿨플랫"),
    ("퀴즈앤",             r"퀴즈앤|QuizN"),
    ("Cursor",             r"\bCursor\b|커서 ?(AI|프로|Pro)"),
    ("엘리스",             r"엘리스|\belice\b"),
    ("니어팟",             r"니어팟|Nearpod"),
    ("밀크T",              r"밀크티|밀크T"),
    ("넷클래스",            r"넷클래스|Net[\s\-]?Class"),   # 계약명엔 'Net-Class 9.0'처럼 하이픈 표기도 쓰인다
    ("루디쿤",             r"루디쿤"),
    ("인공지능 히어로",      r"인공지능 ?히어로|AI ?히어로"),
    ("DBpia",              r"DBpia|디비피아"),
    ("마타수학",            r"마타수학|마타에듀"),
    ("아이엠스쿨",          r"아이엠스쿨|iamschool"),
    ("슈퍼스쿨",            r"슈퍼스쿨|SuperSchool"),
    ("마이크로비트",         r"마이크로비트|micro:?bit"),
    ("교보문고 전자도서관",   r"교보문고"),
    ("아이톡톡",            r"아이톡톡"),
    ("KT AICE",            r"\bAICE\b"),
    ("와콤",               r"와콤|Wacom"),
    # 전문 소프트웨어 — 계약명에 영문 그대로 적히는 제품군 (오탈자 표기 포함)
    ("Mathematica",        r"Math\s?e?matica|매스매티카"),
    ("MATLAB",             r"\bMATLAB\b|매트랩"),
    ("OrCAD",              r"\bOr ?CAD\b|오르캐드"),
    ("ANSYS",              r"\bANSYS\b|(?<![가-힣])안시스(?![가-힣])"),   # '보안시스템'·'이안시스테크'에 걸리던 것을 막는다
    ("SolidWorks",         r"Solid ?Works|솔리드웍스"),
    ("AutoCAD",            r"Auto ?CAD|오토캐드"),
    ("Movavi",             r"\bMovavi\b|모바비"),
    # Unity 규칙을 뺀다 — 걸린 24건이 유니티비(TV 셋톱박스)·원두커피 탬핑기·젠더였고
    # 영문 UNITY 1건도 동아리 이름이었다
    # ("Unity", r"\bUnity\b(?! ?교육)|유니티"),
    # 스크래치·엔트리는 뺀다. 둘 다 무료 도구라 학교가 사들일 일이 없고,
    # 계약명에 나오는 '스크래치/엔트리'는 산 물건(로봇·교구·교재)이 그 도구와 호환된다는 설명이다.
    # 게다가 한글 '스크래치'는 미술 재료(스크래치북·스크래치 페이퍼)와 수세미(제로스크래치)에도 쓰인다.
    # 실제로 1,220건(스크래치)·680건(엔트리) 가운데 구독·라이선스·이용권 신호가 있는 계약은 0건이었다.
    # ("Scratch", r"\bScratch\b|스크래치(?!치)"), ("엔트리", r"엔트리(?! ?고|타)|\bEntry\b(?! ?Level)")
    ("Tinkercad",          r"Tinkercad|팅커캐드"),
    # 투핸즈인터랙티브의 체육활동 에듀테크 교구. 이 회사의 유일한 제품이라 태그는 '디딤'으로 통일한다.
    # ('디딤' 단독으로 잡으면 디딤돌·디딤학교 등과 겹치므로 앞말이 붙은 표기만 인정)
    ("디딤",                 r"플레이 ?디딤|play ?didim|투핸즈인터랙티브|디딤_|"
                             r"디딤 ?(?:소프트웨어|증강|디지털 ?체육)"),
    ("Bitly",              r"\bbitly\b|비틀리"),
    ("Readdy AI",          r"\bReaddy\b|리디 ?AI"),
    # 에듀집 등록명은 '코들 AI 클래스룸'이지만 계약서엔 브랜드만 적힌다. '코들리'는 다른 제품
    ("코들",               r"코들(?!리)|\bCODLE\b"),
    ("inline AI",          r"\binline ?AI\b"),
    ("WeeAI",              r"\bWee\s?AI\b|위\s?AI(?=\s?플랫폼)"),
    ("Suno",               r"\bSuno\b|수노 ?AI"),
    ("Ghost",              r"\bGhost\b(?! ?Rider)"),            # 디스크 이미징 도구(Norton Ghost)
    ("Symantec",           r"\bSymantec\b|시만텍"),
    # 에듀집 등록명의 브랜드부만 계약서에 적힌 사례 (자동 스캔으로 발굴)
    ("뚜루뚜루",           r"뚜루뚜루"),
    ("소프트웨어야 놀자",  r"소프트웨어야\s?놀자"),
    ("곰캠",               r"곰캠"),
    ("말랑말랑 코딩여행",  r"말랑말랑\s?코딩\s?여행"),   # '말랑말랑코딩'만으로는 방과후 과정 이름이다
    ("네오봇",             r"네오봇"),
    ("알티노",             r"알티노"),
    ("파이보츠",           r"파이보츠"),
    ("페더",               r"페더(?!럴|레)"),
    ("스마트올",           r"스마트올"),
    ("웨이메이커",          r"웨이메이커|메이저맵"),
    ("오르조",             r"오르조"),
    ("EdgeCAM",            r"\bEdge ?CAM\b"),
    ("엠타이니",           r"엠타이니"),
    ("로보마스터",          r"로보마스터|RoboMaster"),
    ("메타퀘스트",          r"메타 ?퀘스트|Meta ?Quest"),
    ("Canva",              r"\bCanva\b|캔바"),
    # 한글 '피그마'는 사쿠라 피그마 드로잉펜이다(73건 전부). 진짜 Figma 계약은 영문을 함께 적는다
    ("Figma",              r"\bFigma\b"),
    ("Miro",               r"\bMiro\b(?! ?사|타)|미로 ?보드"),
    ("Perplexity",         r"Perplexity|퍼플렉시티"),
    ("Gamma",              r"\bGamma ?(?:Pro|AI)\b|감마 ?(?:프로|AI)"),
    ("젠스파크",             r"젠스파크|Genspark"),
    ("KAIST 공동 AP",       r"KAIST ?공동 ?AP|공동 ?AP ?학사관리|apscience|대학과목선이수"),
    ("캐츠잉글리시",          r"캐츠 ?잉글리시|캣츠 ?잉글리시|Cats ?English"),
    ("윌라",                r"윌라(?!드)|welaaa"),
    ("알툴즈",               r"알툴즈|알PDF|알집(?! ?파일)|ALTools"),
    ("이지에듀",             r"이지에듀|EZ ?EDU"),
    ("반디캠",               r"반디캠|Bandicam"),
    ("곰믹스",               r"곰믹스|GOM ?Mix"),
    ("클립스튜디오",          r"클립 ?스튜디오|Clip ?Studio"),
    ("쿨메신저",             r"쿨메신저|Cool ?Messenger"),
    ("하드보안관",            r"하드보안관"),
    ("리딩앤",               r"리딩앤(?!드)|Reading& ?"),
    ("네프론",               r"네프론|Nephron"),
    ("마인크래프트 에듀케이션", r"마인크래프트|Minecraft"),
    ("카훗",               r"카훗|Kahoot"),
    ("김킷",               r"김킷|Gimkit"),
    ("카미",               r"카미ᅟ?\(|\bKami\b"),
    ("체더스",              r"체더스|Cheddar"),
    ("띵커벨",              r"띵커벨"),
    # 하이픈·띄어쓰기 변형까지 (e-알리미, 이 알리미). '아이알리미'는 다른 제품이라 제외
    ("e알리미",             r"e[\s\-]?알리미|(?<!아)이[\s\-]?알리미"),
]

# 에듀집 등록 제품 중 조달 기록으로 실사용이 확인된 제품 — edzip_rules.csv에서 자동 로드
# (제품 단위 전수조사 결과: 나라장터 전수 140만 건 × 에듀집 2,490종 대조)
# 자동 발굴 규칙 — mine_products.py가 에듀집 사전과 대조해 확정한 제품명(A등급)
if os.path.exists("mined_rules.csv"):
    _seen_m = {t for t, _ in SPECIFIC_RULES}
    for _row in csv.DictReader(open("mined_rules.csv", encoding="utf-8-sig")):
        if _row["태그"] not in _seen_m and _row["패턴"]:
            SPECIFIC_RULES.append((_row["태그"], _row["패턴"]))
            _seen_m.add(_row["태그"])

# 문맥 조건부 태그: 제품명이 보통명사와 겹칠 수 있어 소프트웨어 문맥이 확인될 때만 인정한다
CTX_REQUIRED = set()
if os.path.exists("edzip_rules.csv"):
    _seen_tags = {t for t, _ in SPECIFIC_RULES}
    for _row in csv.DictReader(open("edzip_rules.csv", encoding="utf-8-sig")):
        if _row["태그"] not in _seen_tags and _row["패턴"]:
            SPECIFIC_RULES.append((_row["태그"], _row["패턴"]))
            _seen_tags.add(_row["태그"])
            if (_row.get("문맥필요") or "").strip() == "Y":
                CTX_REQUIRED.add(_row["태그"])
if os.path.exists("mined_rules.csv"):
    for _row in csv.DictReader(open("mined_rules.csv", encoding="utf-8-sig")):
        if (_row.get("문맥필요") or "").strip() == "Y":
            CTX_REQUIRED.add(_row["태그"])
# 소프트웨어·서비스 도입임을 알려주는 신호 / 시설·공사임을 알려주는 신호
SW_CTX = re.compile(r"구독|라이선스|라이센스|이용권|이용료|사용료|사용 ?계약|플랫폼|프로그램|"
                    r"소프트웨어|\bSW\b|S/W|계정|어플|\b앱\b|콘텐츠|코스웨어|에듀테크|"
                    r"인공지능|\bAI\b|디지털|학습|수업|교육자료", re.I)
FACILITY_CTX = re.compile(r"공사|설비|보수|조성|정비|철거|배관|전기|도색|방수|제초|살포|청소|"
                          r"급식|차량|버스|가구|책상|의자|운동장|화장실|냉난방")

# AI·디지털 교육자료(AIDT)는 출판사별로 다른 제품 — 계약 상대 업체로 발행처를 특정한다
AIDT_PUBLISHERS = [
    ("천재교과서", r"천재교과서|천재교육"), ("비상교육", r"비상교육"),
    ("YBM", r"와이비엠|\bYBM\b"), ("NE능률", r"엔이능률|NE ?능률"),
    ("동아출판", r"동아출판"), ("미래엔", r"미래엔"), ("금성출판사", r"금성출판"),
    ("지학사", r"지학사"), ("아이스크림미디어", r"아이스크림미디어"), ("교학사", r"교학사"),
]
# "AIDT 활용 부속품·태블릿"류는 교재가 아니라 기기 구매다
AIDT_ACCESSORY = re.compile(r"부속품|부속 ?물품|활용 ?물품|태블릿|무선 ?인프라|제작 ?용역")
AIDT_TAG = "AI·디지털 교육자료"

def refine_aidt(tags, name, vendor):
    if AIDT_TAG not in tags:
        return tags
    if AIDT_ACCESSORY.search(name or ""):
        return [("기기(PC·태블릿·전자칠판 등)" if t == AIDT_TAG else t) for t in tags]
    for label, pat in AIDT_PUBLISHERS:
        if re.search(pat, vendor or "", re.I):
            return [(f"{label} {AIDT_TAG}" if t == AIDT_TAG else t) for t in tags]
    return tags

# 행사·캠프 용역, 비제품 계약(버스 임대 등)은 수록 제외 — 제품 도입이 아닌 활동성 계약
# 산 것이 책이면 소프트웨어가 아니다 — '맞춤형 프로그램 (코딩 스크래치) 교재 구입'의 '프로그램'은
# 수업 과정을 가리키는 말이지 소프트웨어가 아니다 (소프트웨어·라이선스·구독이 함께 적히면 예외)
BOOK_BUY = re.compile(r"(교재|도서|워크북|문제집|참고서|학습지)\s*(?:외 ?\d+종)?\s*(?:구[입매]|구매|납품|대금)|"
                      r"(교재|도서|워크북|문제집|참고서|학습지)\s*$")
# 계약명이 '~공사'로 끝나면 건물·설비를 짓는 계약이다 ('SW/AI교육 채움교실 구축에 따른 전기 공사').
# '공사에 따른 소프트웨어 구입'처럼 끝이 구매인 것은 그대로 둔다.
EXCLUDE_WORK = re.compile(r"공사\s*(?:비|대금|계약|건)?\s*$|공사\s*\(?[^)]{0,12}\)?\s*(?:계약|입찰|발주)\s*$")
EXCLUDE_EVENT = re.compile(r"전세버스|버스 ?임차|차량 ?임차|차량 ?렌트|임대차|숙박|수송|캠프|위탁용역|위탁 ?운영|여행|정기간행물|간행물|설계 ?용역|감리|도시락|급식|체험학습|물류|청소|방역|소독|경비 ?용역|인쇄|승강기|엘리베이터|정수기|교복|체육복|상품권|기념품|시상품|트로피|기념패|홍보물품")
# "○○ 프로그램 운영"의 '프로그램'은 소프트웨어가 아니라 교육·연수 과정 — 특정 제품명이 없으면 비제품 용역
EDU_SERVICE = re.compile(r"프로그램(?:\s*[\(（][^)）]{0,40}[\)）])?\s*운영|운영 ?용역|특강|연수|강사")   # 'GROW2기 프로그램(과학교육과 인공지능) 운영 물품(목걸이형 명찰외)'
# 계약 전체가 교육 서비스인 유형 — 브랜드가 언급돼도 제품 도입이 아니므로 무조건 제외 (SW 구입 문구만 예외)
HARD_SERVICE = re.compile(r"교육 ?용역|동아리 ?운영|방과후 ?운영|체험.{0,12}용역|체험 ?교육|운영비")
# 일반 '용역' 계약은 대부분 교육활동 — 제품 이용 신호가 있으면 유지 (플랫폼·구독·콘텐츠·설치·임차 등)
# 자격증·위탁교육 등 '교육 실행' 계약 — 물품·라이선스 구매 신호가 없으면 제품 도입이 아니다
# 학교 보안·시설 설비 — 학습과 무관하므로 수록 대상이 아니다
# ('출결관리'는 에듀테크에 해당하므로 '출입'과 구분해서 적을 것)
SECURITY_SYS = re.compile(r"출입 ?관리|출입 ?통제|출입 ?시스템|출입문|무인경비|방범|CCTV|"
                          r"도어락|잠금장치|주차 ?관리|스피드게이트|지문 ?인식기|안면인식 ?출입|"
                          r"마스터키(?!트)|키박스|자물쇠|시건장치")
EDU_TRAINING = re.compile(r"위탁 ?교육|위탁교육|자격증|직무 ?연수|연수 ?용역|캠프 ?운영|"
                          r"교육과정 ?운영|아카데미 ?운영|과정 ?운영|취득 ?교육|체험 ?위탁|"
                          r"역량 ?강화 ?프로그램|프로그램 ?위탁")
# 계약 상대가 여행·운송업이면 제품 공급이 아니라 연수·체험 운영 계약이다
#  (예: '글로벌 소프트웨어 역량 강화 프로그램 위탁 용역' — 계약업체 ○○항공여행사)
# 책걸상·수납가구 등 일반 가구 — 컴퓨터실에 놓여도 에듀테크 제품이 아니다
# (태블릿 충전보관함·전자교탁처럼 기기와 한 몸인 것은 제외 대상이 아니다)
FURNITURE = re.compile(
    r"(?:학생용 ?)?(?:의자|걸상|책상(?! ?위)|책걸상|가구|사물함|캐비닛|수납장|서가|책장|"
    r"칸막이|파티션|게시판|커튼|블라인드|소파|테이블|교구장|신발장|우산꽂이|리빙박스|정리함|보관함(?! ?충전)|트레이)"
    r"(?![^가-힣]{0,4}(?:형|용) ?(?:전자칠판|모니터|태블릿))")
# 레고월·벽면 장식처럼 공간 꾸미기 시공은 학습 제품 도입이 아니다
WALL_DECOR = re.compile(r"레고 ?[월벽]|벽면 ?(?:장식|조형)|현관 ?(?:조형|장식)|포토존|조형물")

FURNITURE_KEEP = re.compile(r"충전 ?(?:보관)?함|충전 ?카트|전자 ?교탁|스마트 ?교탁|거치대|모니터 ?암")

# 시설 유지보수·설비 계약 — 학습과 무관하므로 인프라 태그가 붙어도 수록 대상이 아니다
# (예: '기숙사 냉난방기 유지보수 용역' — 냉난방이 인프라 규칙에 걸리지만 에듀테크가 아니다)
FACILITY_MAINT = re.compile(
    r"(?:냉난방|난방|냉방|보일러|공조|급배수|배관|상하수|소방|승강기|엘리베이터|정화조|"
    r"방수|도색|창호|바닥|천장|지붕|외벽|담장|화장실|기숙사|급식실|조리|보안등|가로등|"
    r"전기 ?안전|전기공사|누수|해빙|제설|수목|조경|화단|운동장|체육관 ?바닥)"
    r"[가-힣]{0,3}\s*(?:유지 ?보수|보수|수리|교체|점검|공사|정비|관리 ?용역|대행)"
    r"|(?:유지 ?보수|수리|교체|점검)[^가-힣]{0,12}(?:냉난방|보일러|공조|승강기|기숙사)")

NON_SUPPLIER = re.compile(r"여행사|여행㈜|관광\s?개발|항공여행|투어|여객|전세버스|운수")
GOODS_SIGNAL = re.compile(r"구입|구매|라이선스|라이센스|구독|임차|대여|렌탈|이용권|사용료|이용료|"
                          r"계정|납품|설치|유지보수")
SVC_KEEP = re.compile(r"플랫폼|시스템|구독|라이선스|라이센스|콘텐츠|설치|유지보수|임차|사용료|이용료|대여|렌탈|코스웨어|소프트웨어|S/?W ?구[입매]")
# 범주형 태그 — 제품명이 특정되지 않는 계약용. 오분류 방지를 위해 제품/서비스명 필드에서만 탐지
GENERIC_RULES = [
    ("AI 면접시스템",        r"AI ?면접|AI ?비대면 ?면접|면접기"),
    ("코스웨어",       r"코스웨어"),
    ("VR/XR 장비",          r"\bVR\b|\bXR\b|가상현실|메타버스"),
    ("로봇·교구·키트",       r"로봇|자율주행|교구|키트|블록코딩"),
    ("드론",                r"드론"),
    ("3D 프린팅/CAD",       r"3D ?프린|3D ?CAD|\bCAD\b|\bCAM\b|인벤터|Inventor"),
    ("인프라(교실·설비)",    r"냉난방|에어컨|공기청정|환경개선|리모델링|배선|전기 ?공사|구축 ?공사|책상|테이블|의자|가구|커튼|블라인드|바닥 ?공사|도색|칸막이|이전 ?설치|증축|전면장|교실 ?구축|실습실|기자재|팩토리|미래교실|스튜디오|구축|충전함"),
    ("기기(PC·태블릿·전자칠판 등)", r"컴퓨터(?! ?책상)(?! ?실)|노트북|태블릿|전자칠판|모니터|크롬북|\bPC\b|(?<!3D)(?<!3D )프린터|디스플레이|디지털 ?기기|서버"),
]

def sido(region):
    if not region:
        return "미상"
    t = region.split()[0]
    return {"전국": "전국(공동)"}.get(t, t)

def year_of(period):
    m = re.search(r"(20\d\d)", period or "")
    return int(m.group(1)) if m else None

def ym_of(period):
    # 시기 문자열에서 첫 연·월을 YYYYMM 정수로 (월 없으면 None)
    m = re.search(r"(20\d\d)[.\-/년\s]\s*(\d{1,2})", period or "")
    if m and 1 <= int(m.group(2)) <= 12:
        return int(m.group(1)) * 100 + int(m.group(2))
    return None

DEPT_NAME = re.compile(r"[가-힣]{0,8}(?:소프트웨어|정보통신|정보처리|컴퓨터|전자|반도체|"
                       r"인공지능|디지털|스마트|메카트로닉스)[가-힣]{0,6}과(?=[\s,)·]|$)")

def strip_school(name, school):
    """계약명 앞의 학교 이름이 태그 규칙에 걸리는 것을 막는다
    (예: '부산소프트웨어마이스터고 교복 구매' → 소프트웨어 태그 오탐)"""
    if not school:
        return name
    out = (name or "").replace(school, " ")
    base = re.sub(r"(초등학교|중학교|고등학교|학교)$", "", school)
    if len(base) >= 3:
        out = out.replace(base, " ")
    return DEPT_NAME.sub(" ", out)      # 학과명도 제거 ('반도체소프트웨어과 대회 상품권' 오탐 방지)

# 한 제품군의 여러 제품을 줄여 적는 표기를 펼친다.
# '토도한글&수학' → '토도한글 토도수학' (계약명 원문에 두 제품이 함께 적힌 것이므로 둘 다 인정한다)
_SHORT_PAIR = re.compile(r"(토도|아이스크림|밀크티|웅진|천재)\s?(한글|수학|영어|국어|과학|사회)"
                         r"\s*(?:[&/·,]|및|과|와)\s*(한글|수학|영어|국어|과학|사회)")

def expand_shorthand(text):
    prev = None
    while prev != text:                      # '토도한글&수학&영어'처럼 이어 붙은 것도 푼다
        prev = text
        text = _SHORT_PAIR.sub(lambda m: f"{m.group(1)}{m.group(2)} {m.group(1)}{m.group(3)}", text)
    return text

SW_KW = r"소프트웨어|SW|S/W|플랫폼|프로그램|라이선스|라이센스|구독|시스템|어플|앱"
GENERIC_SET = {t for t, _ in GENERIC_RULES}

def tags_of(name, content):
    hay = expand_shorthand(f"{name} {content}")
    tags = []
    aux = False
    for t, pat in SPECIFIC_RULES:
        if not re.search(pat, hay, re.I):
            continue
        # "○○(선도학교) 운영/활용/수업용 물품 구입"처럼 브랜드가 맥락으로만 등장하면 그 브랜드 사용 기록이 아님
        CTX = r"\s*(?:프로그램|플랫폼|집중|선도)*\s*(?:선도학교|운영|연계|활용|수업|주간)"
        ctx = re.search(f"(?:{pat})" + CTX, hay, re.I)
        plain = re.search(f"(?:{pat})" + f"(?!{CTX})", hay, re.I)
        if ctx and not plain:
            aux = True
            continue
        tags.append(t)
    # 특정 제품명이 확인되면 범주 태그는 생략 (제품명 속 단어에 범주 규칙이 오반응하는 것도 방지)
    # "영어 튜터로봇 활용 수업에 필요한 영어 전자책 도서관 앱 구입" —
    # '활용·위한·필요한' 앞은 무엇에 쓰려는지(목적)이고, 뒤가 실제로 산 것이다.
    # 제품명이 잡힌 계약은 건드리지 않고, 범주만 붙은 계약에서만 뒤쪽을 우선한다.
    if not tags or all(t in GENERIC_SET for t in tags):
        mp = re.search(r"(?:활용|위한|필요한)\s*(.+)$", name)
        if mp and re.search(r"구[입매]|구매|구독|납품|지출|대금", mp.group(1)):
            ttags = [t for t, pat in GENERIC_RULES if re.search(pat, mp.group(1), re.I)]
            if not ttags and re.search(SW_KW, mp.group(1), re.I):
                ttags = ["SW·플랫폼"]          # '… 도서관 앱 구입'처럼 산 것이 소프트웨어일 때
            if ttags:
                tags = ttags
    if not tags:
        # "기자재(EDA소프트웨어)"처럼 괄호 안이 실제 구매 대상이면 괄호 내용만으로 분류
        paren = " ".join(re.findall(r"\(([^)]*)\)", name))
        ptags = [t for t, pat in GENERIC_RULES if re.search(pat, paren, re.I)] if paren else []
        if not ptags and paren and re.search(SW_KW, paren, re.I):
            ptags = ["SW·플랫폼"]
        tags += ptags or [t for t, pat in GENERIC_RULES if re.search(pat, name, re.I)]
    # "실습기자재 소프트웨어 구입"처럼 대상이 소프트웨어로 명시되면 시설·기기 태그보다 SW가 우선
    if tags and set(tags) <= {"인프라(교실·설비)", "기기(PC·태블릿·전자칠판 등)"} \
            and re.search(r"소프트웨어|S/?W\b|라이선스|라이센스|구독|프로그램", name, re.I):
        tags = ["SW·플랫폼"]
    # "AI교실 환경 구축 노트북 구입"처럼 '구축·조성'이 목적 문구일 뿐이면 기기 구매이지 인프라가 아님
    if "기기(PC·태블릿·전자칠판 등)" in tags and "인프라(교실·설비)" in tags:
        stripped = re.sub(r"(?:환경 ?)?구축|조성|기자재|실습실|환경개선", "", name)
        infra_pat = dict(GENERIC_RULES)["인프라(교실·설비)"]
        if not re.search(infra_pat, stripped, re.I):
            tags.remove("인프라(교실·설비)")
    # 보통명사와 겹치는 제품명은 소프트웨어 문맥이 있고 시설·공사 문맥이 아닐 때만 인정
    if tags and CTX_REQUIRED:
        tags = [t for t in tags if t not in CTX_REQUIRED
                or (SW_CTX.search(hay) and not FACILITY_CTX.search(hay))]
    if "GPT킬러" in tags and "ChatGPT" in tags:
        name_wo = re.sub(r"GPT ?킬러", "", name)
        if not re.search(r"ChatGPT|챗GPT|GPT[- ]?[45]|OpenAI", name_wo, re.I):
            tags.remove("ChatGPT")
    if aux and not tags:
        tags.append("SW·플랫폼" if re.search(r"서비스|구독|이용권|이용료|사용료|라이선스|라이센스|콘텐츠", name)
                    else "운영 부대구매")
    # 통화녹음 단말기(알티폰·RT폰)는 '단말시스템'이라는 말 때문에 소프트웨어로 잡혔다 — 기기다
    if not tags and re.search(r"알티폰|\bRT ?폰\b|알티텔레콤|녹음기|녹취기|키폰", name, re.I):
        return ["기기(PC·태블릿·전자칠판 등)"]
    if not tags and re.search(r"소프트웨어|SW|S/W|플랫폼|프로그램|라이선스|라이센스|구독|시스템|어플|앱", name, re.I) \
            and not (BOOK_BUY.search(name) and not re.search(r"소프트웨어|S/?W\b|라이선스|라이센스|구독|플랫폼", name, re.I)):
        tags.append("SW·플랫폼")
    return tags

rows = list(csv.reader(open(SRC, encoding="utf-8-sig")))
header = rows[2]
records = []
for i, r in enumerate(rows[3:]):
    if len(r) < 11 or not r[0].strip():
        continue
    r = [c.strip() for c in r]
    m = find_school(r[1], r[3])
    records.append({
        "id": int(r[0]) if r[0].isdigit() else i,
        "school": r[1], "type": r[2], "region": r[3], "sido": sido(r[3]),
        "product": r[4], "category": r[5], "period": r[6],
        "year": year_of(r[6]), "ym": ym_of(r[6]), "content": r[7],
        "sourceType": "나라장터" if "나라장터" in r[8] else r[8],
        "url": r[9], "confidence": r[10], "note": r[11] if len(r) > 11 else "",
        "tags": refine_aidt(tags_of(r[4], r[7]), r[4], r[7]),
        "amt": (lambda ms: int(max(float(x.replace(",", "")) for x in ms) * 10000) if ms else None)(re.findall(r"\(([\d,]+(?:\.\d+)?)만", r[7])),
        "schoolCode": m["code"] if m else None,
        "schoolName": m["name"] if m else None,     # NEIS 현재 교명(개명 반영)
        "hsType": (m.get("hsType") or "") if m else "",
        "founding": (m.get("founding") or "") if m else "",
        "neisAddress": (m.get("address") or "") if m else "",
    })

# 마이스터고 판별: NEIS는 법령대로 특목고로 분류하지만 서비스는 특성화고와 묶음
MEISTER_EXTRA = {"인천해사고등학교", "합덕제철고등학교", "군산기계공업고등학교"}
def is_meister(s):
    if s.get("hsType") != "특목고":
        return False
    d = s.get("hsDetail") or ""
    if "산업수요" in d:
        return True
    if d:
        return False
    return "마이스터" in s["name"] or s["name"] in MEISTER_EXTRA

# --- 파일럿 자동수집분(나라장터 API) 병합: refined_*.csv → 기존 형식으로 변환 ---
NEIS_SIDO_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주",
    "전남광주통합특별시(전남)": "전남", "전남광주통합특별시(광주)": "광주", "재외한국학교": "재외"}

master_by_code = {}
for cands in master_by_name.values():
    for c in cands:
        master_by_code[c["code"]] = c

import glob
# 수동 보정: 계약번호 → 실제 제품명 (조달 기록에 브랜드가 없는 계약을 사람이 확인해 채움)
OVERRIDES = {}
if os.path.exists("manual_overrides.csv"):
    for row in csv.DictReader(open("manual_overrides.csv", encoding="utf-8-sig")):
        if row.get("계약번호") and row.get("실제제품명"):
            OVERRIDES[row["계약번호"].strip()] = row

# --- 학교 재매칭 보정 ---------------------------------------------------------
# 수집 단계의 시도 추정은 "경기도광주교육청"에서 '광주'(광역시)를 먼저 잡는 등 오판이 있었다.
# 여기서는 수요기관 첫 토큰(관할 시도교육청)을 근거로 다시 맞춘다.
# 통합운영학교 보정: 조달 주체(예: 무릉초등학교)와 계약명 속 실사용 학교(무릉중학교)가
# 같은 어간에 급만 다르면 계약명 쪽 학교로 귀속 (같은 시도에 실재할 때만)
TITLE_SCHOOL = re.compile(r"([가-힣]{2,})(초등학교|중학교|고등학교)")
_LV = {"초": "초등학교", "중": "중학교", "고": "고등학교"}
# 실사용 학교 재귀속 확정 쌍: (조달 명의 학교, 계약명 속 실사용 학교) — 웹 검증 근거 있음
REATTR_PAIRS = {("창원기계공업고등학교", "양산인공지능고등학교")}  # 2025.3 신설교 개교준비팀이 창원기계공고 상주
def _switch(row, target):
    cands = master_by_name.get(target, [])
    if len(cands) == 1:
        row = dict(row)
        row["_원학교명"] = row["학교명"]
        row["학교명"], row["학교코드"] = target, cands[0]["code"]
        row["급별"], row["시도"] = cands[0]["level"], cands[0]["sido"]
    return row

def reattribute(row):
    # 개명 학교 별칭 적용 (미매칭 파일럿 기록)
    if row["학교명"] in ALIAS:
        row = _switch(row, ALIAS[row["학교명"]])
    for org, real in REATTR_PAIRS:
        if row["학교명"] == org and real in row["계약명"].replace(" ", ""):
            return _switch(row, real)
    mo = TITLE_SCHOOL.fullmatch(row["학교명"] or "")
    if not mo:
        return row
    name = row["계약명"]
    target = None
    mt = TITLE_SCHOOL.search(name)
    if mt and mt.group(0) != row["학교명"] and mt.group(1) == mo.group(1) and mt.group(2) != mo.group(2):
        target = mt.group(0)          # "무릉중학교 ... 구입" (전체 이름)
    if not target:
        ab = re.search(r"([가-힣]{2,})(초|중|고)(?=\s)", name)
        if ab and ab.group(1) == mo.group(1) and _LV[ab.group(2)] != mo.group(2):
            target = ab.group(1) + _LV[ab.group(2)]   # "무릉중 2026..." (약칭)
    if not target:
        mk = re.match(r"\s*\((초|중|고)\)", name)
        if mk and _LV[mk.group(1)] != mo.group(2):
            target = mo.group(1) + _LV[mk.group(1)]   # "(중)2025..." (급 표기)
    if not target:
        return row
    cands = [c for c in master_by_name.get(target, [])
             if not row["시도"] or c["sido"] == row["시도"]]
    if len(cands) == 1:
        row = dict(row)
        row["_원학교명"] = row["학교명"]
        row["학교명"], row["학교코드"] = target, cands[0]["code"]
        row["급별"], row["시도"] = cands[0]["level"], cands[0]["sido"]
    return row

pilot_count = 0
seen_pilot = set()
for path in sorted(glob.glob("refined_*.csv")):
    for row in csv.DictReader(open(path, encoding="utf-8-sig")):
        row = resolve_school(reattribute(row))
        key = (row["계약번호"], row["학교명"])
        if key in seen_pilot:
            continue
        seen_pilot.add(key)
        m = master_by_code.get(row["학교코드"])
        level = row["급별"]
        if level == "고등학교":
            if m and is_meister(m):
                stype = "마이스터고"
            else:
                stype = (m.get("hsType") if m else "") or "고등학교"
        elif level in ("초등학교", "중학교"):
            stype = level
        else:
            # 마스터 대조에 실패해도 교명 끝이 말해 준다 — '남산초등학교'는 초등학교다
            # (동명 학교가 여럿이라 어느 곳인지 못 정한 것이지, 학교급을 모르는 것이 아니다)
            _nm = row.get("학교명") or ""
            stype = level or next((lv for lv in ("초등학교", "중학교", "고등학교")
                                   if _nm.endswith(lv)), None) or "미확정"
        s_short = NEIS_SIDO_SHORT.get(row["시도"], row["시도"] or "미상")
        amt = int(row["금액"] or 0)
        amt_txt = f"({amt/10000:,.0f}만원)" if amt else ""
        year = int(row["계약일"][:4]) if row.get("계약일") else None
        ov = OVERRIDES.get((row.get("계약번호") or "").strip())
        ov_tags = tags_of(ov["실제제품명"], "") if ov else []
        records.append({
            "id": 100000 + pilot_count,
            "school": row["학교명"], "type": stype,
            "region": s_short, "sido": s_short,
            "product": row["계약명"], "category": f"자동수집({row['구분']})",
            "period": row.get("계약일") or "", "year": year, "amt": amt or None,
            "ym": int(row["계약일"][:7].replace("-", "")) if row.get("계약일") and len(row["계약일"]) >= 7 else None,
            "content": f"나라장터 {row['구분']} 계약 {amt_txt}"
                + (f" · 계약업체: {row['업체명']}" if row.get("업체명") else "")
                + (f" · 실제 제품: {ov['실제제품명']} (수동 확인)" if ov else ""),
            "sourceType": "나라장터",
            "url": row.get("상세URL") or "", "confidence": "상" if ov else "중",
            "note": (f"실제 제품 수동 확인: {ov['실제제품명']}" + (f" — 근거: {ov['근거']}" if ov.get("근거") else "")) if ov else "파일럿 자동수집분 — 제품명·내용 검증 전",
            "tags": sorted(set(refine_aidt(tags_of(strip_school(row["계약명"], row["학교명"]), "") + ov_tags, row["계약명"], row.get("업체명", "")))),
            "schoolCode": row["학교코드"] or None,
            "schoolName": m["name"] if m else row["학교명"],
            "hsType": (m.get("hsType") or "") if m else "",
            "founding": (m.get("founding") or "") if m else "",
            "neisAddress": (m.get("address") or "") if m else "",
            "origSchool": row.get("_원학교명") or "",
        })
        pilot_count += 1
print(f"파일럿 자동수집분 병합: {pilot_count}건")

# --- S2B 학교장터 수집분 병합: s2b_refined.csv (공고 기준 — 금액·업체 정보 없음) ---
def _norm_title(t):
    return re.sub(r"\s|계약|공고|체결|의\s*건|건$", "", t)

# 나라장터 기록과 같은 학교·같은 계약명·±2개월이면 동일 계약의 이중 등재로 보고 S2B 쪽 제외
_nara_titles = {}
for r in records:
    if r["sourceType"] == "나라장터" and r.get("ym"):
        _nara_titles.setdefault((r["school"], _norm_title(r["product"])), []).append(
            (r["ym"] // 100) * 12 + r["ym"] % 100)

s2b_count, s2b_dup = 0, 0
if os.path.exists("s2b_refined.csv"):
    for row in csv.DictReader(open("s2b_refined.csv", encoding="utf-8-sig")):
        key = (row["계약번호"], row["학교명"])
        if key in seen_pilot:
            continue
        seen_pilot.add(key)
        ym = int(row["계약일"][:7].replace("-", "")) if row.get("계약일") and len(row["계약일"]) >= 7 else None
        if ym:
            mm = (ym // 100) * 12 + ym % 100
            if any(abs(mm - pm) <= 2 for pm in _nara_titles.get((row["학교명"], _norm_title(row["계약명"])), [])):
                s2b_dup += 1
                continue
        m = master_by_code.get(row["학교코드"])
        level = row["급별"]
        if level == "고등학교":
            stype = "마이스터고" if (m and is_meister(m)) else ((m.get("hsType") if m else "") or "고등학교")
        elif level in ("초등학교", "중학교"):
            stype = level
        else:
            # 마스터 대조에 실패해도 교명 끝이 말해 준다 — '남산초등학교'는 초등학교다
            # (동명 학교가 여럿이라 어느 곳인지 못 정한 것이지, 학교급을 모르는 것이 아니다)
            _nm = row.get("학교명") or ""
            stype = level or next((lv for lv in ("초등학교", "중학교", "고등학교")
                                   if _nm.endswith(lv)), None) or "미확정"
        s_short = NEIS_SIDO_SHORT.get(row["시도"], row["시도"] or "미상")
        records.append({
            "id": 200000 + s2b_count,
            "school": row["학교명"], "type": stype,
            "region": s_short, "sido": s_short,
            "product": row["계약명"], "category": f"자동수집({row['구분']})",
            "period": row.get("계약일") or "", "year": int(row["계약일"][:4]) if row.get("계약일") else None,
            "amt": None, "ym": ym,
            "content": f"S2B 학교장터 수의계약({row['구분']})",   # 공고가 아니라 체결분 — 계약일·금액이 있다
            "sourceType": "S2B 학교장터",
            "url": "", "confidence": "중",
            "note": "S2B 자동수집분 — 공고 기준(금액·계약업체 미표시)",
            "tags": refine_aidt(tags_of(strip_school(row["계약명"], row["학교명"]), ""), row["계약명"], ""),
            "schoolCode": row["학교코드"] or None,
            "schoolName": m["name"] if m else row["학교명"],
            "hsType": (m.get("hsType") or "") if m else "",
            "founding": (m.get("founding") or "") if m else "",
            "neisAddress": (m.get("address") or "") if m else "",
        })
        s2b_count += 1
    print(f"S2B 학교장터 병합: {s2b_count}건 (나라장터 중복 제외 {s2b_dup}건)")

# --- 시도교육청 계약공개 수집분 병합 (소액 구매 포함) ---
# 시도를 늘릴 때는 이 표에 한 줄만 추가한다 (정제 스크립트가 같은 스키마를 내보내므로)
OFFICE_SOURCES = [
    ("ice_refined.csv", "인천", "인천교육청 계약공개", 300000),
    ("pen_refined.csv", "부산", "부산교육청 계약공개", 400000),
    ("dge_refined.csv", "대구", "대구교육청 계약공개", 500000),
    ("gen_refined.csv", "광주", "광주교육청 계약공개", 600000),
    ("dje_refined.csv", "대전", "대전교육청 계약공개", 700000),
    ("use_refined.csv", "울산", "울산교육청 계약공개", 800000),
    ("cbe_refined.csv", "충북", "충북교육청 계약공개", 900000),
    ("jne_refined.csv", "전남", "전남교육청 계약공개", 1000000),
    # 2026-08 추가분
    ("goe_refined.csv", "경기", "경기교육청 계약공개", 1100000),
    ("gbe_refined.csv", "경북", "경북교육청 계약공개", 1200000),
    ("gwe_refined.csv", "강원", "강원교육청 계약공개", 1300000),
    ("sje_refined.csv", "세종", "세종교육청 계약공개", 1400000),
    ("jje_refined.csv", "제주", "제주교육청 계약공개", 1500000),
    ("cne_refined.csv", "충남", "충남교육청 계약공개", 1600000),
    ("gne_refined.csv", "경남", "경남교육청 계약공개", 1700000),
    ("sen_refined.csv", "서울", "서울교육청 계약공개", 1800000),
    ("nara_bid_refined.csv", "", "나라장터 입찰공고", 1900000),   # 전국 — 시도는 행마다 다르다
]
for _src, _sido, _label, _idbase in OFFICE_SOURCES:
    if not os.path.exists(_src):
        continue
    office_count, office_dup = 0, 0
    _idx = {}
    for r in records:
        if r.get("ym"):
            _idx.setdefault((r["school"], _norm_title(r["product"])), []).append(
                (r["ym"] // 100) * 12 + r["ym"] % 100)
    for row in csv.DictReader(open(_src, encoding="utf-8-sig")):
        key = (row["계약번호"], row["학교명"])
        if key in seen_pilot:
            continue
        seen_pilot.add(key)
        ym = int(row["계약일"][:7].replace("-", "")) if row.get("계약일") and len(row["계약일"]) >= 7 else None
        # 나라장터·S2B에 이미 있는 계약이면 중복 (같은 학교·같은 계약명·±2개월)
        if ym:
            mm = (ym // 100) * 12 + ym % 100
            if any(abs(mm - pm) <= 2 for pm in _idx.get((row["학교명"], _norm_title(row["계약명"])), [])):
                office_dup += 1
                continue
        m = master_by_code.get(row["학교코드"])
        level = row["급별"]
        if level == "고등학교":
            stype = "마이스터고" if (m and is_meister(m)) else ((m.get("hsType") if m else "") or "고등학교")
        elif level in ("초등학교", "중학교"):
            stype = level
        else:
            # 마스터 대조에 실패해도 교명 끝이 말해 준다 — '남산초등학교'는 초등학교다
            # (동명 학교가 여럿이라 어느 곳인지 못 정한 것이지, 학교급을 모르는 것이 아니다)
            _nm = row.get("학교명") or ""
            stype = level or next((lv for lv in ("초등학교", "중학교", "고등학교")
                                   if _nm.endswith(lv)), None) or "미확정"
        amt = int(row["금액"] or 0)
        amt_txt = f"({amt/10000:,.0f}만원)" if amt >= 10000 else (f"({amt:,}원)" if amt else "")
        records.append({
            "id": _idbase + office_count,
            "school": row["학교명"], "type": stype,
            "region": _sido or NEIS_SIDO_SHORT.get(row.get("시도", ""), row.get("시도") or "미상"),
            "sido": _sido or NEIS_SIDO_SHORT.get(row.get("시도", ""), row.get("시도") or "미상"),
            "product": row["계약명"], "category": f"자동수집({row['구분']})",
            "period": row.get("계약일") or "", "year": int(row["계약일"][:4]) if row.get("계약일") else None,
            "amt": amt or None, "ym": ym,
            "content": f"{_label} {row['구분']} {amt_txt}"
                + (f" · 계약업체: {row['업체명']}" if row.get("업체명") else ""),
            "sourceType": _label,
            "url": "", "confidence": "중",
            "note": ("나라장터 입찰공고 자동수집분 — 낙찰 전이라 계약 상대자가 없고 금액은 기초금액"
                     if "입찰" in _label else "교육청 계약정보공개 자동수집분 — 소액 구매 포함"),
            "tags": refine_aidt(tags_of(strip_school(row["계약명"], row["학교명"]), ""), row["계약명"], row.get("업체명", "")),
            "schoolCode": row["학교코드"] or None,
            "schoolName": m["name"] if m else row["학교명"],
            "hsType": (m.get("hsType") or "") if m else "",
            "founding": (m.get("founding") or "") if m else "",
            "neisAddress": (m.get("address") or "") if m else "",
        })
        office_count += 1
    print(f"{_label} 병합: {office_count}건 (중복 제외 {office_dup}건)")

# 행사·캠프 용역 등 비제품 계약 제외
before = len(records)
records = [r for r in records if not EXCLUDE_EVENT.search(r["product"]) and not EXCLUDE_WORK.search(r["product"])]
# 교육·연수 운영 용역 제외 — 단, 특정 제품명 태그나 명시적 SW 구입 문구가 있으면 유지
SPECIFIC_TAGS = {t for t, _ in SPECIFIC_RULES} | {f"{lab} {AIDT_TAG}" for lab, _ in AIDT_PUBLISHERS}
SW_BUY = re.compile(r"(?:소프트웨어|플랫폼|라이선스|라이센스|S/?W|구독권?)\s*구[입매]")
records = [r for r in records
           if not (EDU_SERVICE.search(r["product"])
                   and not (SPECIFIC_TAGS & set(r["tags"]))
                   and not SW_BUY.search(r["product"]))]
records = [r for r in records
           if not (HARD_SERVICE.search(r["product"]) and not SW_BUY.search(r["product"])
                   and not re.search(r"플랫폼|시스템", r["product"]))]
# 용역 계약인데 계약명이 교육 실행이고 물품 신호가 없으면, 제품군 태그만으로는 도입 근거가 못 된다.
# (예: '드론 교육', '메타버스 진로체험' — 제품을 산 게 아니라 교육을 산 것)
EDU_WORD = re.compile(r"교육|연수|캠프|아카데미|특강|강좌|체험|수업")
_before_svc = len(records)
_spec_all = {t for t, _ in SPECIFIC_RULES} | {f"{lab} {AIDT_TAG}" for lab, _ in AIDT_PUBLISHERS}
records = [r for r in records
           if not (re.search(r"용역", (r.get("content") or "") + (r.get("category") or ""))
                   and EDU_WORD.search(r["product"])
                   and not GOODS_SIGNAL.search(r["product"])
                   and not (_spec_all & set(r["tags"])))]
if _before_svc - len(records):
    print(f"교육 실행 용역(제품군 태그만) 제외: {_before_svc - len(records)}건")

# 계약 상대가 여행·운송업이면 제품 공급이 아니다 (연수·체험 운영 계약)
_before_ns = len(records)
records = [r for r in records
           if not (NON_SUPPLIER.search(r.get("content") or "")
                   and not (_spec_all & set(r["tags"])))]
if _before_ns - len(records):
    print(f"여행·운송 업체 계약 제외: {_before_ns - len(records)}건")

# 이전·재설치 비용은 이미 도입한 물건을 옮기는 지출이라 새 도입으로 세면 중복이 된다.
# ('구입 및 이전 설치'처럼 구매가 함께 있으면 도입이므로 남긴다)
MOVE_ONLY = re.compile(r"이전\s?설치|이설\s?비|이전\s?비용|재설치|이전에 ?따른|철거")
_before_mv = len(records)
records = [r for r in records
           if not (MOVE_ONLY.search(r["product"])
                   and not re.search(r"구[입매]|구독|라이선스|라이센스|납품|제작", r["product"]))]
if _before_mv - len(records):
    print(f"이전·재설치 비용 제외: {_before_mv - len(records)}건")

# 벽면 장식 시공 제외 (레고월 등)
_before_wd = len(records)
records = [r for r in records if not WALL_DECOR.search(r["product"])]
if _before_wd - len(records):
    print(f"벽면 장식 시공 계약 제외: {_before_wd - len(records)}건")

# 일반 가구 계약 제외 — 특정 제품 태그나 기기 부속 신호가 있으면 유지
_before_fn = len(records)
records = [r for r in records
           if not (FURNITURE.search(r["product"])
                   and not FURNITURE_KEEP.search(r["product"])
                   and not (_spec_all & set(r["tags"])))]
if _before_fn - len(records):
    print(f"책걸상·수납가구 계약 제외: {_before_fn - len(records)}건")

# 시설 유지보수·설비 계약 제외 (냉난방·기숙사·승강기 등) — 특정 제품 태그가 있으면 유지
_before_fm = len(records)
records = [r for r in records
           if not (FACILITY_MAINT.search(r["product"]) and not (_spec_all & set(r["tags"])))]
if _before_fm - len(records):
    print(f"시설 유지보수·설비 계약 제외: {_before_fm - len(records)}건")

# '용역'은 일을 시키는 계약이라 제품 구매와 거리가 멀다 — 제품 이용 신호가 없으면 제외한다
# (예외: 아이스크림 홈런 용역·리로스쿨 용역처럼 제품명이나 구독·라이선스 신호가 뚜렷한 경우)
_before_svc2 = len(records)
records = [r for r in records
           if not (re.search(r"용역", r["product"] + (r.get("content") or "") + (r.get("category") or ""))
                   and not (_spec_all & set(r["tags"]))
                   and not GOODS_SIGNAL.search(r["product"])
                   and not SVC_KEEP.search(r["product"]))]
if _before_svc2 - len(records):
    print(f"제품 신호 없는 용역 계약 제외: {_before_svc2 - len(records)}건")

# 보안·시설 설비 계약 제외 (출입통제·CCTV·방범 등)
_before_sec = len(records)
records = [r for r in records if not SECURITY_SYS.search(r["product"])]
if _before_sec - len(records):
    print(f"보안·시설 설비 계약 제외: {_before_sec - len(records)}건")

# 자격증 취득·위탁 교육류: 물품 구매 신호가 없으면 교육 용역이므로 제외
_before_edu = len(records)
records = [r for r in records
           if not (EDU_TRAINING.search(r["product"]) and not GOODS_SIGNAL.search(r["product"]))]
if _before_edu - len(records):
    print(f"자격증·위탁교육 등 교육 실행 계약 제외: {_before_edu - len(records)}건")
# 일반 '용역' 계약 — 제품 이용 신호도, 특정 제품명 태그도 없으면 교육활동으로 보고 제외
records = [r for r in records
           if not ("용역" in r["product"] and not SVC_KEEP.search(r["product"])
                   and not (SPECIFIC_TAGS & set(r["tags"])))]
print(f"행사·캠프·임대·교육운영 계약 제외: {before - len(records)}건")

# AI 일괄 분류(검증 전) — 규칙 태그가 없는 기록에만 적용, 잡음 판정은 제외
AI_CLS = {}
if os.path.exists("ai_classified.csv"):
    for row in csv.DictReader(open("ai_classified.csv", encoding="utf-8-sig")):
        AI_CLS[(row["school"], row["product"])] = row["분류"].strip()
if AI_CLS:
    kept_ai, ai_n, ai_noise = [], 0, 0
    for r in records:
        if not r["tags"]:
            c = AI_CLS.get((r["school"], r["product"])) or AI_CLS.get((r.get("origSchool") or "", r["product"]))
            # "교육 프로그램·연수"는 소프트웨어가 아니라 교육 용역 — 에듀테크 아님
            if c in ("잡음", "교육 프로그램·연수"):
                ai_noise += 1
                continue
            if c:
                tag = c[3:].strip() if c.startswith("제품:") else c
                if tag:
                    r["tags"] = [tag]
                    r["note"] = (r["note"] + " · " if r["note"] else "") + "AI 일괄 분류(검증 전)"
                    ai_n += 1
        kept_ai.append(r)
    records = kept_ai
    print(f"AI 분류 적용: {ai_n}건, AI 잡음 제외: {ai_noise}건")

# 결제 수수료 기록 표시 — 해외/카드 결제의 부대 지출은 제품 구매액이 아니다.
# ('아이엠스쿨 이용 수수료'처럼 이용료 자체인 경우는 제외하려고 결제 수단·소액 조건을 함께 본다)
FEE_ANCILLARY = re.compile(r"(?:해외|카드|결제|승인|송금|환전|이용액)[^)\n]{0,6}수수료")
_fee_n = 0
for r in records:
    p = r.get("product") or ""
    if "수수료" not in p:
        continue
    small = (r.get("amt") or 0) and r["amt"] < 10000
    if FEE_ANCILLARY.search(p) or small:
        r["note"] = (r["note"] + " · " if r.get("note") else "") + "결제 수수료 — 제품 이용의 부대 지출(구매액 아님)"
        r["feeOnly"] = 1
        _fee_n += 1
print(f"결제 수수료 부대 지출 표시: {_fee_n}건")

# 업체명 자체가 제품명인 경우 — 계약명에 제품이 없어도 업체로 특정된다
# (자동 도출은 3건 이상이라야 작동하므로, 1~2건뿐인 단일 제품 업체는 여기에 적는다)
VENDOR_RULES = [
    (r"READDY|리디 ?AI", "Readdy AI"),
    (r"툰스퀘어", "투닝"),
    (r"제로엑스플로우", "원아워"),
    (r"투핸즈인터랙티브", "디딤"),
    # 해외 구독은 카드 결제 표기가 그대로 업체명 칸에 들어온다 — 'OPENAI *CHATGPT SUBSCR'처럼
    # 업체명이 곧 제품명이라 추론이 아니다. 계약명에는 '에듀테크 소프트웨어 구입'만 적혀 있다.
    (r"chat ?gpt|챗지피티|openai", "ChatGPT"),
    (r"^\s*(?:\(주\)|주식회사)?\s*adobe|어도비", "Adobe"),
    (r"padlet|패들렛", "Padlet"),
    (r"kahoot|카훗", "카훗"),
    (r"anthropic|claude\.ai|클로드", "Claude"),
    (r"^\s*canva|canva ?(?:pro|for|inc)", "Canva"),
    (r"^\s*notion|notion ?labs", "Notion"),
    (r"quizlet|퀴즐렛", "Quizlet"),
    (r"^\s*suno(?:\s|,|$)|suno ?ai", "Suno"),
    (r"perplexity", "Perplexity"),
]
_vr_n = 0
for r in records:
    m = re.search(r"계약업체[:：]\s*([^·)]+)", r.get("content") or "")
    if not m:
        continue
    for pat, tag in VENDOR_RULES:
        if re.search(pat, m.group(1), re.I) and tag not in r["tags"]:
            r["tags"] = sorted((set(r["tags"]) | {tag}) - {"SW·플랫폼", "코스웨어"})
            r["note"] = (r["note"] + " · " if r.get("note") else "") + f"계약 업체명이 제품명({tag})"
            _vr_n += 1
if _vr_n:
    print(f"업체명=제품명 규칙 적용: {_vr_n}건")

# 업체 기반 통계 추론(어떤 업체의 계약 다수가 한 제품이면 나머지도 그 제품으로 봄)은 폐기했다.
# 근거: 데이터 안내에 "업체명으로 제품을 추정하지 않는다"고 공개해 온 원칙과 어긋나고,
#       실제로 계약명에 다른 제품이 적힌 건까지 덮어썼다
#       (안산청석초 '블록 로봇(네오 쏘코)' → 업체가 레고를 주로 판다는 이유로 레고 태그).
#       레고 유통사로 확인된 퓨너스조차 자체 제품을 함께 팔아, '단일 공급사'라는 전제가 성립하지 않는다.
# 업체명 자체가 제품명인 경우(Padlet.com·READDY AI 등)만 위 VENDOR_RULES로 남긴다.

# 원자료에 남은 HTML 엔티티(&apos; &amp; 등) 정리 — 화면에 그대로 노출되는 것을 막는다
_ent = re.compile(r"&[a-zA-Z]{2,8};|&#\d{2,5};")
_ent_n = 0
for r in records:
    for k in ("product", "content", "school", "note"):
        v = r.get(k)
        if isinstance(v, str) and _ent.search(v):
            r[k] = html.unescape(v)
            _ent_n += 1
if _ent_n:
    print(f"HTML 엔티티 정리: {_ent_n}곳")

# 태그가 하나도 붙지 않은 기록 제외 — 학교 이름에 '소프트웨어'가 들어가 딸려온 비에듀테크 계약 등
_before_ut = len(records)
records = [r for r in records if r["tags"]]
if _before_ut - len(records):
    print(f"태그 없는 기록 제외: {_before_ut - len(records)}건")

# 언론보도가 같은 학교·제품의 조달 기록과 ±6개월 내면 동일 건으로 보고 집계에서 1건 처리
def _months(ym):
    return (ym // 100) * 12 + ym % 100
_proc_idx = {}
for r in records:
    st = r["sourceType"]
    if (st == "나라장터" or "S2B" in st or "교육청 계약" in st) and r.get("ym"):
        for t in r["tags"]:
            _proc_idx.setdefault((r["school"], t), []).append(_months(r["ym"]))
_dup_n = 0
for r in records:
    if r["sourceType"] == "언론보도" and r.get("ym"):
        m = _months(r["ym"])
        if any(abs(m - pm) <= 6 for t in r["tags"] for pm in _proc_idx.get((r["school"], t), [])):
            r["dup"] = 1
            r["note"] = (r["note"] + " · " if r["note"] else "") + "조달 기록과 동일 건 추정 — 집계 1건 처리"
            _dup_n += 1
print(f"언론-조달 동일 건 병합 집계: {_dup_n}건")

# 손으로 정리한 씨앗 기록과 자동수집 기록이 같은 계약이면(학교·금액 일치, ±2개월)
# 계약명 원문이 남는 자동수집분을 살리고, 씨앗이 특정해 둔 제품 태그를 옮겨 붙인다
_auto_idx = collections.defaultdict(list)
for r in records:
    if str(r.get("category", "")).startswith("자동수집") and r.get("amt") and r.get("ym"):
        _auto_idx[(r["school"], r["amt"])].append(r)
_seed_dup, _drop_ids = 0, set()
for r in records:
    if str(r.get("category", "")).startswith("자동수집") or not r.get("amt"):
        continue
    m = _months(r["ym"]) if r.get("ym") else None
    for a2 in _auto_idx.get((r["school"], r["amt"]), []):
        if m is not None:
            if abs(m - _months(a2["ym"])) > 2:
                continue
        elif r.get("year") and r["year"] != a2.get("year"):
            continue      # 씨앗에 월이 없으면 연도만 대조 (금액이 원 단위로 같아 충돌 위험은 낮다)
        gained = sorted(set(r["tags"]) - set(a2["tags"]) - {"SW·플랫폼", "코스웨어"})
        if gained:
            a2["tags"] = sorted((set(a2["tags"]) | set(gained)) - {"SW·플랫폼", "코스웨어"})
            a2["note"] = (a2["note"] + " · " if a2.get("note") else "") + "제품 확인 완료"
        _drop_ids.add(id(r))
        _seed_dup += 1
        break
if _seed_dup:
    records = [r for r in records if id(r) not in _drop_ids]
    print(f"씨앗-자동수집 동일 계약 정리: {_seed_dup}건 (계약명 원문 쪽을 남김)")

# 완전 중복 제거: 학교+제품명+시기+내용(금액 포함)이 모두 같으면 이중 등재로 보고 첫 건만 유지
seen_exact = set()
deduped = []
for rec in records:
    key = (rec["school"], rec["product"], rec["period"], rec["content"])
    if key in seen_exact:
        continue
    seen_exact.add(key)
    deduped.append(rec)
print(f"완전 중복 제거: {len(records) - len(deduped)}건")
records = deduped

# 태깅 커버리지 리포트
tagged = sum(1 for rec in records if rec["tags"])
coded = len({rec["school"] for rec in records if rec["schoolCode"]})
total_schools = len({rec["school"] for rec in records})
print(f"총 {len(records)}건, 태그 부여 {tagged}건 ({tagged/len(records):.0%}), 학교코드 매칭 {coded}/{total_schools}교")
tag_counts = collections.Counter(t for rec in records for t in rec["tags"])
for t, c in tag_counts.most_common():
    schools = len({rec["school"] for rec in records if t in rec["tags"]})
    print(f"  {t}: {c}건 / {schools}개교")

# 전국 학교 검색 인덱스 — 기록 없는 학교도 검색·열람 가능하게
# 국내 공교육 전체(특수학교·방송통신·각종학교·평생학교 포함).
# 재외한국학교·외국인학교·국제학교는 국내 공교육이 아니어서, 공동실습소는 학교가 아니어서 제외.
INDEX_EXCLUDE = ("재외한국학교", "외국인학교", "국제학교", "공동실습소")
school_index = []
for cands in master_by_name.values():
    for s in cands:
        if s["level"] and not any(e in s["level"] for e in INDEX_EXCLUDE):
            rec = {
                "c": s["code"], "n": s["name"], "l": s["level"],
                "s": NEIS_SIDO_SHORT.get(s["sido"], s["sido"]),
                "h": s.get("hsType") or "", "f": s.get("founding") or "",
                "a": s.get("address") or "",
            }
            if is_meister(s):
                rec["m"] = 1
            elif s.get("hsType") == "특목고":
                rec["d"] = s.get("hsDetail") or ""
            school_index.append(rec)
print(f"전국 학교 인덱스: {len(school_index)}개교")

meta = {
    "asOf": "2026-07-20",
    "total": len(records),
    "schools": len({rec["school"] for rec in records}),
    "coveragePeriod": "2023.1 ~ 2026.7",
    "pilot": pilot_count,
}
# --- 신규 태그 검증 리포트 ---------------------------------------------------
# 직전 빌드에 없던 태그마다 계약명 원문을 무작위로 뽑아 tag_review.md에 남긴다.
# 브랜드명이 보통명사와 겹쳐 엉뚱한 계약에 붙는 일을 커밋 전에 사람이 확인하기 위한 장치.
import random as _random
_snap_path = ".tag_snapshot.json"
_prev = set(json.load(open(_snap_path))) if os.path.exists(_snap_path) else set()
_by_tag = collections.defaultdict(list)
for _r in deduped:
    for _t in _r["tags"]:
        _by_tag[_t].append(_r)
_now = set(_by_tag)
_new_tags = sorted(_now - _prev)
if _new_tags:
    _random.seed(0)
    _lines = [f"# 신규 태그 검증 — {len(_new_tags)}종", "",
              "직전 빌드에 없던 태그입니다. 계약명 원문이 실제로 그 제품을 가리키는지 확인하세요.",
              "보통명사와 겹치는 이름(그라운드=운동장 등)이 엉뚱한 계약에 붙지 않았는지 특히 주의.", ""]
    for _t in _new_tags:
        _recs = _by_tag[_t]
        _schools = len({_x["school"] for _x in _recs})
        _edu = [_x for _x in _recs if EDU_TRAINING.search(_x["product"])]
        _warn = f"  ⚠️ 교육 용역 신호 {len(_edu)}건 포함 — 제품 도입인지 확인" if _edu else ""
        _lines.append(f"## {_t} — {len(_recs)}건 / {_schools}개교{_warn}")
        for _x in _random.sample(_recs, min(5, len(_recs))):
            _amt = f"{_x['amt']:,}원" if _x.get("amt") else "금액 미상"
            _flag = " ⚠️" if EDU_TRAINING.search(_x["product"]) else ""
            _lines.append(f"- [{_x['school']}] {_x['product']}  ({_amt} · {_x['sourceType']}){_flag}")
        _lines.append("")
    open("tag_review.md", "w", encoding="utf-8").write("\n".join(_lines))
    print(f"신규 태그 {len(_new_tags)}종 → tag_review.md (커밋 전 확인 필요)")
elif os.path.exists("tag_review.md"):
    os.remove("tag_review.md")
json.dump(sorted(_now), open(_snap_path, "w"), ensure_ascii=False)

# --- content 조립화 ---
# '내용'의 대부분은 출처·구분·금액·업체로 기계적으로 만든 문구다(같은 문장이 8만 6천 번 반복된다).
# 조각만 싣고 화면에서 조립한다. 조립 결과가 원문과 한 글자라도 다르면 원문을 그대로 남긴다.
def _amt_txt(a):
    if not a:
        return ""
    return f"({a/10000:,.0f}만원)" if a >= 10000 else f"({a:,}원)"

_ctpl_n = 0
for r in records:
    c = r.get("content") or ""
    m = re.search(r"계약업체[:：]\s*(.+?)\s*$", c)
    vend = m.group(1).strip() if m else ""
    head = c[:m.start()].rstrip(" ·") if m else c
    # 머리말에서 금액 표기를 떼어 내면 '출처 + 구분'만 남는다
    head2 = re.sub(r"\s*\([\d,]+(?:만)?원\)\s*$", "", head).strip()
    built = head2 + (" " + _amt_txt(r.get("amt")) if r.get("amt") else "")
    if vend:
        built += " · 계약업체: " + vend
    if built == c and c:
        r["vendor"] = vend
        r["ctpl"] = head2                 # 출처·구분 머리말 (사전으로 압축된다)
        r["content"] = None
        _ctpl_n += 1
print(f"내용 문구 조립화: {_ctpl_n:,}건 (원문 유지 {len(records)-_ctpl_n:,}건)")

# --- 저장: 키 이름 반복과 되풀이되는 문자열을 걷어낸 압축 형식 ---
# 레코드마다 키 이름을 적으면 그것만으로 파일의 3분의 1이 된다. 열 이름을 한 번만 적고
# 값은 배열로 늘어놓되, 되풀이되는 문자열(출처·비고·지역 등)은 사전으로 치환한다.
# 화면 쪽 코드는 그대로 두기 위해 index.html이 읽는 시점에 원래 모양으로 되돌린다.
# 화면에서 안 쓰는 열(id)은 싣지 않고, 값이 거의 없는 표시 열(dup·feeOnly)은
# 행마다 null을 적는 대신 '해당하는 행 번호 목록'으로 따로 넘긴다.
_DROP_COLS = {"id"}
_SPARSE_COLS = ["dup", "feeOnly"]
_cols = sorted({k for r in records for k in r} - _DROP_COLS - set(_SPARSE_COLS))
_DICT_COLS = ["note", "sourceType", "category", "type", "region", "sido",
              "vendor", "ctpl",
              "hsType", "founding", "confidence", "period",
              # 학교 관련 값은 그 학교의 기록 수만큼 되풀이된다
              "neisAddress", "school", "schoolName", "schoolCode"]
_dicts = {}
for c in _DICT_COLS:
    vals = sorted({r.get(c) for r in records if isinstance(r.get(c), str)})
    if len(vals) < len(records) / 4:            # 되풀이가 뚜렷할 때만 사전으로 바꾼다
        _dicts[c] = {v: i for i, v in enumerate(vals)}
_URL_PRE = "https://www.g2b.go.kr/link/FIUA027_01/single/?ctrtNo="
# 태그는 278종뿐인데 행마다 문자열로 적히고 있었다 — 번호로 바꾸고 표를 한 번만 싣는다
_tag_list = sorted({t for r in records for t in r["tags"]})
_tag_no = {t: i for i, t in enumerate(_tag_list)}
_sparse = {c: [i for i, r in enumerate(records) if r.get(c)] for c in _SPARSE_COLS}
_rows = []
for r in records:
    row = []
    for c in _cols:
        v = r.get(c)
        if c == "tags":
            v = [_tag_no[t] for t in v]
        elif c in _dicts and isinstance(v, str):
            v = _dicts[c][v]
        elif c == "url" and isinstance(v, str) and v.startswith(_URL_PRE):
            v = "~" + v[len(_URL_PRE):]
        row.append(v)
    _rows.append(row)

# 첫 화면과 검색에 필요한 열만 먼저 싣고, 상세 표시용 열은 뒤이어 받도록 나눈다.
# (모바일에서 첫 로딩이 실용 한계를 넘어선 데 대한 대응 — 전송량은 같지만 첫 화면이 빨라진다)
_DETAIL_COLS = ["url", "note", "neisAddress", "category", "hsType",
                "founding", "region", "schoolName", "content"]
_core_cols = [c for c in _cols if c not in _DETAIL_COLS]
_det_cols = [c for c in _cols if c in _DETAIL_COLS]
_ci = [_cols.index(c) for c in _core_cols]
_di = [_cols.index(c) for c in _det_cols]
_core_rows = [[r[i] for i in _ci] for r in _rows]
_det_rows = [[r[i] for i in _di] for r in _rows]
_core_dict = {c: v for c, v in _dicts.items() if c in _core_cols}
_det_dict = {c: v for c, v in _dicts.items() if c in _det_cols}

# 자료를 자바스크립트 문법으로 적으면 브라우저가 19MB짜리 소스를 통째로 해석하느라
# 첫 화면이 3초 넘게 늦어진다. 같은 내용을 문자열에 담아 JSON.parse로 넘기면
# 전용 파서가 처리해 10배 가까이 빠르다(측정: 2.9초 → 0.26초).
def _js_literal(obj):
    """JSON 본문을 작은따옴표 문자열로 감싼다 — 큰따옴표를 escape하지 않아 크기가 늘지 않는다"""
    t = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    t = t.replace("\\", "\\\\").replace("'", "\\'")
    t = t.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")   # JS에서 줄바꿈으로 취급되는 문자
    return "'" + t + "'"

# 제품 국적 — product_origin.csv(제품·구분·근거)를 화면에서 쓸 수 있게 실어 보낸다
_origin = {}
if os.path.exists("product_origin.csv"):
    for _r in csv.DictReader(open("product_origin.csv", encoding="utf-8-sig")):
        _origin[_r["제품"]] = _r["구분"]

with open(OUT, "w", encoding="utf-8") as f:
    f.write("// build_data.py가 생성한 파일 — 직접 수정 금지\n")
    f.write("const DB_RAW = JSON.parse(")
    f.write(_js_literal({"meta": meta, "cols": _core_cols,
                         "dict": {c: sorted(d, key=d.get) for c, d in _core_dict.items()},
                         "tagList": _tag_list, "origin": _origin, "sparse": _sparse, "rows": _core_rows,
                         "schoolIndex": school_index}))
    f.write(");\n")
with open("data_detail.js", "w", encoding="utf-8") as f:
    f.write("// build_data.py가 생성한 파일 — 직접 수정 금지 (첫 화면 뒤에 따로 읽는다)\n")
    f.write("const DB_DETAIL = JSON.parse(")
    f.write(_js_literal({"cols": _det_cols,
                         "dict": {c: sorted(d, key=d.get) for c, d in _det_dict.items()},
                         "urlPrefix": _URL_PRE, "rows": _det_rows}))
    f.write(");\n")
_a = os.path.getsize(OUT) / 1024 / 1024
_b = os.path.getsize("data_detail.js") / 1024 / 1024
print(f"\n{OUT} {_a:.1f}MB (첫 화면·검색용 {len(_core_cols)}열) + "
      f"data_detail.js {_b:.1f}MB (상세 {len(_det_cols)}열)")

# 첫 화면용 요약 파일 — 홈 화면 수치만 미리 계산해 두면 원자료를 기다리지 않고 그릴 수 있다
import shutil as _sh, subprocess as _sp
if _sh.which("node"):
    _sp.run(["node", "make_summary.js"], check=False)
else:
    print("! node가 없어 data_summary.js를 만들지 못했습니다 — 첫 화면이 원자료를 기다리게 됩니다")
