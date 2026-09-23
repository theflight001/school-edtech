# 대구광역시교육청 수의계약내역공개 — 검색어 없이 월별 전체 목록을 받는 수집기(전수 스윕)
# 사용: EDTECH_MAXREQ=5000 python3 collect_dge_sweep.py [--begin 2020-01] [--end 2026-09]
#
# 왜 따로 만드나: 대구는 연 단위 조회가 안 되고 월 단위만 되어(collect_dge.py 참고), 검색어 방식이면
# 확정 목록 1,445종 × 81개월 = 약 10만 조합(약 20일)이다. 검색어를 비우고 한 쪽 1,000건씩 받으면
# 한 달(약 3만 건)이 31쪽이라 81개월이 2,500회 안팎이다(2026-09-23 확인: pageIndex=1000이 먹힌다).
# 목록에는 금액·업체가 없어 상세를 따로 불러야 하는데, 판정 규칙(build_data.py)을 목록 단계에서 먼저 돌려
# 에듀테크로 볼 만한 계약만 상세를 부른다 — 규칙에 안 걸리는 계약은 어차피 정제에서 빠진다.
# 결과는 dge_candidates.csv에 '(전수)' 키워드로 이어 붙인다(refine_office.py 대구가 그대로 읽는다).
# 검색어 방식으로 이미 받은 행(기관·계약명·계약일이 같은 것)은 다시 받지 않는다.
import argparse, csv, json, os, re, sys, time
import importlib.util

spec = importlib.util.spec_from_file_location("dge", "collect_dge.py")
dge = importlib.util.module_from_spec(spec); spec.loader.exec_module(dge)
OUT, CKPT, FIELDS = dge.OUT, ".ckpt_dge_sweep.json", dge.FIELDS
PAGE = 1000

def load_rules():
    src = open("build_data.py", encoding="utf-8").read()
    ns = {"__name__": "rules"}
    exec(compile(src[:src.index('rows = list(csv.reader(open(SRC')], "rules", "exec"), ns)
    return ns

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", default="2020-01")
    ap.add_argument("--end", default="2026-09")
    a = ap.parse_args()
    R = load_rules()
    tags_of, refine_aidt, strip_school = R["tags_of"], R["refine_aidt"], R["strip_school"]
    EXCLUDE_EVENT, EDU_SERVICE, HARD_SERVICE, SVC_KEEP = R["EXCLUDE_EVENT"], R["EDU_SERVICE"], R["HARD_SERVICE"], R["SVC_KEEP"]
    SPECIFIC = {t for t, _ in R["SPECIFIC_RULES"]} | {f"{lab} {R['AIDT_TAG']}" for lab, _ in R["AIDT_PUBLISHERS"]}
    SW_BUY = re.compile(r"(?:소프트웨어|플랫폼|라이선스|라이센스|S/?W|구독권?)\s*구[입매]")
    CTX = re.compile(r"에듀테크|코스웨어|인공지능|\bAI\b|디지털|스마트|\bSW\b|S/W|소프트웨어|정보화|메타버스|\bVR\b|\bXR\b|증강현실|가상현실|"
                     r"로봇|코딩|드론|3D ?프린|이러닝|e-?러닝|온라인 ?수업|원격 ?수업|미래교실|스마트교실|전자칠판|태블릿|크롬북|노트북|컴퓨터실", re.I)

    def wanted(name, inst):
        """정제(refine_office.py)와 같은 기준으로 '상세를 받을 가치가 있는' 계약인지 본다"""
        if not re.search(r"(?<!대)학교$", inst) or "외국인" in inst or EXCLUDE_EVENT.search(name) or dge.EXCLUDE.search(name):
            return False
        tags = refine_aidt(tags_of(strip_school(name, inst), ""), name, "")
        if not tags:
            return False
        spec_ = bool(SPECIFIC & set(tags))
        if not spec_ and not CTX.search(name):
            return False
        if EDU_SERVICE.search(name) and not spec_ and not SW_BUY.search(name):
            return False
        if HARD_SERVICE.search(name) and not spec_ and not SW_BUY.search(name) and not re.search(r"플랫폼|시스템", name):
            return False
        if "용역" in name and not SVC_KEEP.search(name) and not spec_:
            return False
        return True

    ck = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "pos": {}}
    done, pos = set(ck["done"]), ck["pos"]
    seen = set()
    if os.path.exists(OUT):
        csv.field_size_limit(10 ** 7)
        for r in csv.DictReader(open(OUT, encoding="utf-8-sig")):
            seen.add((r["기관명"], r["계약명"], r["계약일"]))
    print(f"이미 받은 행 {len(seen):,} · 끝난 달 {len(done)}", flush=True)
    wins = list(reversed(dge.months(a.begin, a.end)))       # 최근 달부터
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()
    def save():
        ck["done"], ck["pos"] = sorted(done), pos
        with open(CKPT + ".tmp", "w") as cf:
            json.dump(ck, cf, ensure_ascii=False)
        os.replace(CKPT + ".tmp", CKPT)
    kept = looked = req_n = 0
    for y, m in wins:
        key = f"{y}|{m}"
        if key in done:
            continue
        page = int(pos.get(key, 0)) + 1
        while True:
            body = dge.post(dge.LIST, dge.form(currPage=str(page), srchY=y, srchM=m, inpSrchwrd="", pageIndex=str(PAGE)))
            req_n += 1
            rows = dge.parse_list(body)
            for name, inst, dt, targ, seq in rows:
                k = (inst, name, dt)
                if k in seen or not wanted(name, inst):
                    continue
                seen.add(k)
                looked += 1
                amt, vendor = "", ""
                try:
                    dge.polite()
                    amt, vendor = dge.parse_view(dge.post(dge.VIEW, dge.form(cntrTargNo=targ, cmSeqNo=seq, srchY=y, srchM=m)))
                    req_n += 1
                except dge.BudgetOut:
                    raise
                except Exception as e:
                    print(f"  상세 실패({e}) — 금액·업체 없이 저장", flush=True)
                w.writerow({"기관명": inst, "계약명": name, "계약일": dt, "계약금액": amt, "계약상대자": vendor, "키워드": "(전수)"})
                kept += 1
                if kept % 20 == 0:
                    f.flush()
                    print(f"  {key} {page}쪽 · 상세 {looked:,} · 저장 {kept:,} (요청 {req_n:,}회)", flush=True)
            f.flush()
            pos[key] = page
            save()
            if len(rows) < PAGE:
                break
            page += 1
            dge.polite()
        done.add(key); pos.pop(key, None); save()
        print(f"[{key}] {page}쪽까지 · 누적 저장 {kept:,}건 (요청 {req_n:,}회)", flush=True)
        dge.polite()
    f.close()
    print(f"\n완료 — 상세 {looked:,}건 · 저장 {kept:,}건 (요청 {req_n:,}회) → {OUT}")

if __name__ == "__main__":
    try:
        main()
    except dge.BudgetOut as e:
        print(f"\n■ {e} — 여기서 멈춘다. 다음 실행에서 이어 받는다.")
