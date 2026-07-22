# CSV → data.js 변환 스크립트 (정적 프로토타입용)
# 사용: python3 build_data.py  → data.js 생성
import csv, json, re, collections, os

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
}

SIDO_PREFIX = {"서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천", "광주": "광주",
               "대전": "대전", "울산": "울산", "세종": "세종", "경기": "경기", "강원": "강원",
               "충북": "충청북", "충남": "충청남", "전북": "전라북|전북", "전남": "전라남",
               "경북": "경상북", "경남": "경상남", "제주": "제주"}

master_by_name = collections.defaultdict(list)
if os.path.exists(MASTER):
    for s in json.load(open(MASTER, encoding="utf-8"))["schools"]:
        master_by_name[s["name"]].append(s)

def find_school(name, region):
    cands = master_by_name.get(ALIAS.get(name, name), [])
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

# 주요 브랜드/제품군 태깅 규칙: (태그명, 정규식) — 제품/서비스명 + 내용 필드에서 탐지
# 제품명 태그 (제품/서비스명 + 내용에서 탐지) — 제품명을 그대로 태그로, 회사명 괄호 없이
SPECIFIC_RULES = [
    ("ChatGPT",            r"ChatGPT|챗GPT|GPT[- ]?[45]|OpenAI"),
    ("Gemini",             r"Gemini|제미나이"),
    ("Claude",             r"Claude|클로드"),
    ("Replit",             r"Replit|리플릿"),
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
    ("클래스팅",            r"클래스팅|Classting"),
    ("코디마스터",          r"코디마스터"),
    ("아이스크림",          r"아이스크림|i-?Scream"),
    ("젭(ZEP)",            r"젭|\bZEP\b"),
    ("매쓰플랫",            r"매쓰플랫"),
    ("스쿨플랫",            r"스쿨플랫"),
    ("퀴즈앤",             r"퀴즈앤|QuizN"),
    ("Cursor",             r"\bCursor\b|커서 ?(AI|프로|Pro)"),
    ("엘리스",             r"엘리스|\belice\b"),
    ("니어팟",             r"니어팟|Nearpod"),
    ("밀크T",              r"밀크티|밀크T"),
    ("넷클래스",            r"넷클래스|NetClass"),
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
]

# 행사·캠프 용역, 비제품 계약(버스 임대 등)은 수록 제외 — 제품 도입이 아닌 활동성 계약
EXCLUDE_EVENT = re.compile(r"전세버스|버스 ?임차|차량 ?임차|차량 ?렌트|임대차|숙박|수송|캠프|위탁용역|위탁 ?운영|여행|정기간행물|간행물|설계 ?용역|감리|도시락|급식|체험학습|물류|청소|방역|소독|경비 ?용역|인쇄")
# "○○ 프로그램 운영"의 '프로그램'은 소프트웨어가 아니라 교육·연수 과정 — 특정 제품명이 없으면 비제품 용역
EDU_SERVICE = re.compile(r"프로그램 ?운영|운영 ?용역|특강|연수|강사")
# 범주형 태그 — 제품명이 특정되지 않는 계약용. 오분류 방지를 위해 제품/서비스명 필드에서만 탐지
GENERIC_RULES = [
    ("AI 면접시스템",        r"AI ?면접|AI ?비대면 ?면접|면접기"),
    ("코스웨어(기타)",       r"코스웨어"),
    ("VR/XR 장비",          r"\bVR\b|\bXR\b|가상현실|메타버스"),
    ("로봇·교구·키트",       r"로봇|자율주행|교구|키트|블록코딩"),
    ("드론",                r"드론"),
    ("3D 프린팅/CAD",       r"3D ?프린|3D ?CAD|\bCAD\b|\bCAM\b|인벤터|Inventor"),
    ("인프라(교실·설비)",    r"냉난방|에어컨|공기청정|환경개선|리모델링|배선|전기 ?공사|구축 ?공사|책상|의자|가구|커튼|블라인드|바닥 ?공사|도색|칸막이|이전 ?설치|증축|전면장|교실 ?구축|실습실|기자재|팩토리|미래교실|스튜디오|구축"),
    ("기기(PC·태블릿·전자칠판 등)", r"컴퓨터|노트북|태블릿|전자칠판|모니터|충전함|크롬북|\bPC\b|프린터|디스플레이|디지털 ?기기|서버"),
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

def tags_of(name, content):
    hay = f"{name} {content}"
    tags = []
    aux = False
    for t, pat in SPECIFIC_RULES:
        if not re.search(pat, hay, re.I):
            continue
        # "○○(선도학교) 운영/활용/수업용 물품 구입"처럼 브랜드가 맥락으로만 등장하면 그 브랜드 사용 기록이 아님
        CTX = r"\s*(?:프로그램|플랫폼|집중|선도)*\s*(?:선도학교|운영|연계|활용|수업|주간|에듀테크)"
        ctx = re.search(f"(?:{pat})" + CTX, hay, re.I)
        plain = re.search(f"(?:{pat})" + f"(?!{CTX})", hay, re.I)
        if ctx and not plain:
            aux = True
            continue
        tags.append(t)
    tags += [t for t, pat in GENERIC_RULES if re.search(pat, name, re.I)]
    if "GPT킬러" in tags and "ChatGPT" in tags:
        name_wo = re.sub(r"GPT ?킬러", "", name)
        if not re.search(r"ChatGPT|챗GPT|GPT[- ]?[45]|OpenAI", name_wo, re.I):
            tags.remove("ChatGPT")
    if aux and not tags:
        tags.append("운영 부대구매(제품 미상)")
    if not tags and re.search(r"소프트웨어|SW|S/W|플랫폼|프로그램|라이선스|라이센스|구독|시스템|어플|앱", name, re.I):
        tags.append("SW·플랫폼(제품명 미상)")
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
        "tags": tags_of(r[4], r[7]),
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

pilot_count = 0
seen_pilot = set()
for path in sorted(glob.glob("refined_*.csv")):
    for row in csv.DictReader(open(path, encoding="utf-8-sig")):
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
            stype = level or "미확정"
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
            "tags": sorted(set(tags_of(row["계약명"], "") + ov_tags)),
            "schoolCode": row["학교코드"] or None,
            "schoolName": m["name"] if m else row["학교명"],
            "hsType": (m.get("hsType") or "") if m else "",
            "founding": (m.get("founding") or "") if m else "",
            "neisAddress": (m.get("address") or "") if m else "",
        })
        pilot_count += 1
print(f"파일럿 자동수집분 병합: {pilot_count}건")

# 행사·캠프 용역 등 비제품 계약 제외
before = len(records)
records = [r for r in records if not EXCLUDE_EVENT.search(r["product"])]
# 교육·연수 운영 용역 제외 — 단, 특정 제품명 태그나 명시적 SW 구입 문구가 있으면 유지
SPECIFIC_TAGS = {t for t, _ in SPECIFIC_RULES}
SW_BUY = re.compile(r"(?:소프트웨어|플랫폼|라이선스|라이센스|S/?W|구독권?)\s*구[입매]")
records = [r for r in records
           if not (EDU_SERVICE.search(r["product"])
                   and not (SPECIFIC_TAGS & set(r["tags"]))
                   and not SW_BUY.search(r["product"]))]
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
            c = AI_CLS.get((r["school"], r["product"]))
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

# 전국 학교 검색 인덱스(초·중·고) — 기록 없는 학교도 검색·열람 가능하게
school_index = []
for cands in master_by_name.values():
    for s in cands:
        if s["level"] in ("초등학교", "중학교", "고등학교"):
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
with open(OUT, "w", encoding="utf-8") as f:
    f.write("// build_data.py가 생성한 파일 — 직접 수정 금지\n")
    f.write("const DB = ")
    json.dump({"meta": meta, "records": records, "schoolIndex": school_index}, f, ensure_ascii=False)
    f.write(";\n")
print(f"\n{OUT} 생성 완료")
