# 강원·경남 특수학교·각종학교 계약 보충 수집 — 학교 이름으로 직접 조회한다.
# 사용: python3 collect_special.py [강원|경남]
# 왜: 두 수집기는 학교 이름이 초·중·고·영재·특수학교로 끝날 때만 남겨 '강릉오성학교'·'거창애광학교' 같은
#     특수학교·각종학교(강원 11·경남 15곳)의 계약을 버렸다(2026-09-15 외부 검증). 규칙은 고쳤지만 검색어×연도 조합이
#     이미 '끝냄'으로 적혀 있어 다시 훑지 않는다. 그래서 이 학교들만 기관명 검색(강원 sc=INST_NM, 경남 q_cntrInstNm)으로 받는다.
# 결과는 각 시도의 후보 파일(강원_candidates.csv·경남_candidates.csv)에 같은 열로 이어 붙이고, 체크포인트 seen에도 넣는다.
import csv, importlib.util, json, os, re, sys, time, urllib.parse

def load(name):
    spec = importlib.util.spec_from_file_location(name, f"collect_{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

OLD = re.compile(r"(초등학교|중학교|고등학교|영재학교|특수학교)$")
NEW = re.compile(r"(?<!대)학교$")
def targets(sido_prefix):
    ms = json.load(open("school_master.json", encoding="utf-8"))["schools"]
    return [s["name"] for s in ms if s["sido"].startswith(sido_prefix) and NEW.search(s["name"])
            and not OLD.search(s["name"]) and "외국인" not in s["name"]]

def run_gwe(names):
    m = load("gwe")
    ckpt = json.load(open(m.CKPT)) if os.path.exists(m.CKPT) else {"done": [], "seen": []}
    seen = set(tuple(k) for k in ckpt["seen"])
    f = open(m.OUT, "a", encoding="utf-8-sig", newline=""); w = csv.DictWriter(f, fieldnames=m.FIELDS)
    kept = req = 0
    for nm in names:
        page = 1
        while page <= 50:
            q = {"key": m.KEY, "menuSn": m.KEY, "pageIndex": str(page), "sc": "INST_NM", "sw": nm}
            rows = m.parse(m.get(m.BASE + "?" + urllib.parse.urlencode(q))); req += 1
            for r in rows:
                if r["기관명"] != nm or m.EXCLUDE.search(r["계약명"]):
                    continue
                key = (r["기관명"], r["계약명"], r["계약일"])
                if key in seen:
                    continue
                seen.add(key); r["키워드"] = "기관명:" + nm; w.writerow(r); kept += 1
            f.flush()
            if len(rows) < 10:
                break
            page += 1
            m.polite()
        print(f"[강원 {nm}] {page}쪽 · 누적 {kept}건 (요청 {req}회)", flush=True)
        m.polite()
    ckpt["seen"] = [list(k) for k in seen]
    json.dump(ckpt, open(m.CKPT + ".tmp", "w"), ensure_ascii=False); os.replace(m.CKPT + ".tmp", m.CKPT)
    f.close(); print(f"강원 끝 · {kept}건 추가", flush=True)

def run_gne(names, years=("2020", "2021", "2022", "2023", "2024", "2025", "2026")):
    m = load("gne")
    ckpt = json.load(open(m.CKPT)) if os.path.exists(m.CKPT) else {"done": [], "seen": []}
    seen = set(tuple(k) for k in ckpt["seen"])
    f = open(m.OUT, "a", encoding="utf-8-sig", newline=""); w = csv.DictWriter(f, fieldnames=m.FIELDS)
    kept = req = 0
    for nm in names:
        for y in years:
            page = 1
            while page <= 50:
                q = {"q_fsclY": y, "q_cntrStDt": "", "q_cntrEdDt": "", "q_cntrInstNm": nm, "q_cntrNm": "",
                     "q_cntrMthdDivNm": "", "q_currPage": str(page), "q_rowPerPage": "100"}
                url = m.LIST + "?" + urllib.parse.urlencode(q)
                html_ = m.opener().open(url, timeout=150).read().decode("utf-8", "replace"); req += 1
                rows = m.parse(html_)
                for r in rows:
                    if r["기관명"] != nm or m.EXCLUDE.search(r["계약명"]):
                        continue
                    key = (r["기관명"], r["계약명"], r["계약일"])
                    if key in seen:
                        continue
                    seen.add(key)
                    vendor = ""
                    if r.get("_seq"):
                        try:
                            m.polite(); vendor = m.vendor_of(r["_seq"]); req += 1
                        except Exception as e:
                            print(f"  상세 실패({e})", flush=True)
                    r.pop("_seq", None); r["계약상대자"] = vendor; r["키워드"] = "기관명:" + nm
                    w.writerow(r); kept += 1
                f.flush()
                if len(rows) < 100:
                    break
                page += 1
                m.polite()
            m.polite()
        print(f"[경남 {nm}] 누적 {kept}건 (요청 {req}회)", flush=True)
    ckpt["seen"] = [list(k) for k in seen]
    json.dump(ckpt, open(m.CKPT + ".tmp", "w"), ensure_ascii=False); os.replace(m.CKPT + ".tmp", m.CKPT)
    f.close(); print(f"경남 끝 · {kept}건 추가", flush=True)

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "강원"
    if which == "강원":
        run_gwe(targets("강원"))
    else:
        run_gne(targets("경상남"))
