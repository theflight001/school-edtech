# 서울 에듀파인연계 후보의 상세를 채운다 — 계약일자·계약대상자·계약방법·목적물.
# 사용: python3 fill_sen_edufine.py
#
# 목록 화면은 회계연도까지만 준다. 상세(view0010v.do)에는 계약일자와 계약대상자명이 있지만
# 25만 건을 하나씩 열 수는 없다. 그래서 판정 규칙을 먼저 돌려 에듀테크로 잡힌 것만 연다.
# 판정 규칙은 build_data.py의 정본을 그대로 불러 쓴다(이중 관리 금지).
import csv, http.cookiejar, html, json, os, re, sys, time, urllib.parse, urllib.request

SRC, OUT, CKPT = "서울에듀파인_candidates.csv", "서울에듀파인_full.csv", ".ckpt_서울에듀파인_상세.json"
VIEW = "https://open.sen.go.kr/fus/MI000000000000000539/cntr/view0010v.do"
LIST = "https://open.sen.go.kr/fus/MI000000000000000539/cntr/list0010v.do"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SPACING = 0.7
FIELDS = ["계약번호", "회계연도", "기관명", "계약명", "계약금액", "진행상태",
          "계약일", "구분", "계약상대자", "키워드"]

_op = None
def opener():
    global _op
    if _op is None:
        cj = http.cookiejar.CookieJar()
        _op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _op.addheaders = [("User-Agent", UA)]
        _op.open(LIST, timeout=60).read()
    return _op


def detail(no, year):
    d = {"cntr_targ_no": no, "ordr_fscl_y": year, "pageIndex": "1"}
    for wait in [5, 20, 60, None]:
        try:
            r = urllib.request.Request(VIEW, data=urllib.parse.urlencode(d).encode(),
                                       headers={"User-Agent": UA, "Referer": LIST})
            h = opener().open(r, timeout=90).read().decode("utf-8", "replace")
            break
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)
    # 표는 <th>라벨</th><td>값</td> 짝으로 이어진다
    cells = re.findall(r"<t([hd])[^>]*>(.*?)</t\1>", h, re.S)
    flat = [(k, html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", v))).strip())
            for k, v in cells]
    out = {}
    for i, (k, v) in enumerate(flat):
        if k != "h" or i + 1 >= len(flat) or flat[i + 1][0] != "d":
            continue
        val = flat[i + 1][1]
        if "계약일자" in v and not out.get("계약일"):
            m = re.search(r"\d{4}-\d{2}-\d{2}", val)
            if m:
                out["계약일"] = m.group(0)
        elif "계약대상자명" in v:
            out["계약상대자"] = val
        elif v.strip() == "목적물":
            out["구분"] = val
    return out


def load_rules():
    src = open("build_data.py", encoding="utf-8").read()
    ns = {"__name__": "rules"}
    exec(compile(src[:src.index("rows = list(csv.reader(open(SRC")], "rules", "exec"), ns)
    return ns


def main():
    R = load_rules()
    tags_of, strip_school = R["tags_of"], R["strip_school"]
    EXCLUDE_EVENT = R["EXCLUDE_EVENT"]

    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    todo = []
    for r in rows:
        name = (r["계약명"] or "").strip()
        if EXCLUDE_EVENT.search(name):
            continue
        if tags_of(strip_school(name, r["기관명"]), ""):
            todo.append(r)
    print(f"후보 {len(rows):,}건 중 에듀테크로 잡힌 것 {len(todo):,}건 — 이것만 상세를 연다", flush=True)

    done = set(json.load(open(CKPT))["done"]) if os.path.exists(CKPT) else set()
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()
    got = 0
    for i, r in enumerate(todo, 1):
        if r["계약번호"] in done or not r["계약번호"]:
            continue
        try:
            d = detail(r["계약번호"], r["회계연도"])
        except Exception as e:
            print(f"  [{r['계약번호']}] 건너뜀 ({type(e).__name__})", flush=True)
            d = {}
        r.update({k: d.get(k, "") for k in ("계약일", "계약상대자", "구분")})
        w.writerow({k: r.get(k, "") for k in FIELDS})
        f.flush()
        done.add(r["계약번호"])
        if d.get("계약일"):
            got += 1
        if i % 100 == 0:
            json.dump({"done": sorted(done)}, open(CKPT, "w"), ensure_ascii=False)
            print(f"  {i:,}/{len(todo):,} · 계약일 확보 {got:,}", flush=True)
        time.sleep(SPACING)
    json.dump({"done": sorted(done)}, open(CKPT, "w"), ensure_ascii=False)
    f.close()
    print(f"\n완료 — {len(done):,}건 · 계약일 확보 {got:,}건 → {OUT}")


if __name__ == "__main__":
    main()
