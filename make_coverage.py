# 자료원 × 월 수집 현황표 — 이용자가 내려받아 어디서 몇 건이 왔는지 직접 확인할 수 있게 한다.
# 사용: python3 make_coverage.py   (빌드 끝에 자동으로 부른다)
#
# 빈 칸이 왜 비었는지가 이 표의 핵심이다. 세 갈래를 갈라 적는다.
#   원천에 없음   그 시도 계약공개 시스템이 그 시기 자료를 갖고 있지 않다(직접 찔러 확인).
#   실제로 0건   원자료는 받았는데 그달에 에듀테크로 판정된 계약이 없었다(작은 시도의 1~2월).
#   수집 못 함    원자료조차 못 받았다 — 이건 우리 숙제다.
import collections, csv, json, os, re

OUT = "수집현황.csv"
FROM, TO = 202001, None            # TO는 자료에서 정한다

# 시도교육청 계약공개의 원자료 파일 (refine_office.py의 OFFICES와 같은 짝)
RAW = {"인천": "ice_candidates.csv", "부산": "pen_candidates.csv", "대구": "dge_candidates.csv",
       "광주": "gen_candidates.csv", "대전": "dje_candidates.csv", "울산": "use_candidates.csv",
       "충북": "충북_candidates.csv", "전남": "전남_candidates.csv", "경기": "경기_candidates.csv",
       "경북": "경북_candidates.csv", "강원": "강원_candidates.csv", "세종": "세종_candidates.csv",
       "제주": "제주_candidates.csv", "충남": "충남_candidates.csv", "경남": "경남_candidates.csv",
       "서울": "서울_candidates.csv"}


def load(p):
    s = open(p, encoding="utf-8").read()
    return json.loads(s[s.index("'") + 1:s.rindex("'")].replace("\\'", "'").replace("\\\\", "\\"))


def months(a, b):
    out = []
    y, m = a // 100, a % 100
    while y * 100 + m <= b:
        out.append(y * 100 + m)
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def main():
    csv.field_size_limit(10 ** 7)
    d, o = load("data.js"), load("data_old.js")
    C = {c: i for i, c in enumerate(d["cols"])}
    st, sd = d["dict"].get("sourceType"), d["dict"].get("sido")
    rows = d["rows"] + o["rows"]
    global TO
    TO = max((r[C["ym"]] for r in rows if r[C["ym"]]), default=202607)
    MS = months(FROM, TO)
    # 자료가 실제로 다 들어찬 마지막 달 — 그 뒤는 '아직 공개 전'이지 구멍이 아니다
    _tot = collections.Counter()
    for r in rows:
        if r[C["ym"]]:
            _tot[r[C["ym"]]] += 1
    _peak = max(_tot.values()) if _tot else 0
    LAST_SOLID = max((m for m in MS if _tot.get(m, 0) >= _peak * 0.3), default=TO)

    got = collections.defaultdict(collections.Counter)      # 자료원 → 달 → 에듀테크 건수
    for r in rows:
        ym = r[C["ym"]]
        if not ym or ym < FROM or ym > TO:
            continue
        s = r[C["sourceType"]]
        got[st[s] if isinstance(s, int) and st else s][ym] += 1

    # 원자료를 어느 달까지 받았는지 (에듀테크 판정 전)
    raw = {}
    for sido, f in RAW.items():
        if not os.path.exists(f):
            continue
        c = collections.Counter()
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            dt = (r.get("계약일") or "").strip()
            if len(dt) >= 7:
                c[int(dt[:7].replace("-", ""))] += 1
        raw[f"{sido}교육청 계약공개"] = c

    def why(src, m, c):
        """빈 칸에 붙일 주석 — 왜 비었는지가 이 표의 핵심이다"""
        if c.get(m, 0):
            return ""
        if m > LAST_SOLID:
            return "아직 공개 전(자료 기준일 이후)"
        rc = raw.get(src)
        if rc is None:
            return "원자료를 따로 두지 않는 자료원이라 사유를 가릴 수 없음"
        if rc.get(m, 0):
            return "원자료는 받았으나 그달 에듀테크 계약이 없었음"
        first, last = (min(rc), max(rc)) if rc else (None, None)
        if first and m < first:
            return f"원천이 그 시기 자료를 갖고 있지 않음(가장 이른 자료 {first//100}.{first%100:02d})"
        if last and m > last:
            return "아직 공개 전"
        # 받은 구간 한가운데인데 원자료도 0이면, 앞뒤 달과 견줘 판단한다
        i = MS.index(m)
        near = [rc.get(MS[j], 0) for j in range(max(0, i - 3), min(len(MS), i + 4)) if MS[j] != m]
        if near and max(near) >= 100:
            return "★ 수집 확인 필요 — 앞뒤 달은 자료가 있는데 이달만 비었음"
        return "원천에 그달 계약이 없음"

    srcs = sorted(got, key=lambda k: -sum(got[k].values()))
    srcs = [s for s in srcs if sum(got[s].values()) >= 20]
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"# 공교육 에듀테크 활용 현황 — 자료원별·월별 수집 현황 ({FROM//100}.{FROM%100:02d}~{TO//100}.{TO%100:02d})"])
        w.writerow(["# 숫자는 그달 그 자료원에서 '에듀테크로 판정된' 계약 건수입니다. 원자료 전체 건수가 아닙니다."])
        w.writerow(["# 빈 칸에는 왜 비었는지 아래 '비고'에 적었습니다."])
        w.writerow([])
        w.writerow(["자료원", "합계"] + [f"{m//100}.{m%100:02d}" for m in MS])
        for s in srcs:
            c = got[s]
            w.writerow([s, sum(c.values())] + [c.get(m, "") for m in MS])
        w.writerow([])
        w.writerow(["# 비고 — 빈 칸의 사유"])
        w.writerow(["자료원", "빈 구간", "달 수", "사유"])
        for s in srcs:
            c = got[s]
            empty = [m for m in MS if not c.get(m, 0)]
            runs = []
            for m in empty:
                if runs and MS.index(m) == MS.index(runs[-1][-1]) + 1:
                    runs[-1].append(m)
                else:
                    runs.append([m])
            for r in runs:
                span = (f"{r[0]//100}.{r[0]%100:02d}" if len(r) == 1
                        else f"{r[0]//100}.{r[0]%100:02d}~{r[-1]//100}.{r[-1]%100:02d}")
                w.writerow([s, span, len(r), why(s, r[0], c)])
    print(f"{OUT} — 자료원 {len(srcs)}종 × {len(MS)}개월")


if __name__ == "__main__":
    main()
