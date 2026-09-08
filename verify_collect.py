# 수집이 제대로 됐는지 원천과 대조한다.
# 사용: python3 verify_collect.py [--offices 인천,충북] [--years 2020,2021,...]
#
# 왜 필요한가: 수집기가 "완료"라고 해도 실제로는 빠뜨릴 수 있다. 실제로 세 번 그랬다.
#   · 오류로 못 받은 칸을 '완료'로 적어 다음 실행에서 영영 건너뜀
#   · --keyword-file이 기본 검색어를 덮어써 알짜가 통째로 빠짐
#   · 검색어 만드는 코드의 들여쓰기 오류로 표기 변형이 누락
# 셋 다 '완료'를 보고하면서 자료를 빠뜨렸다. 완료 메시지는 완료의 증거가 아니다.
#
# 그래서 원천 화면에 직접 물어 '전체 N건'을 받아, 우리가 가진 수와 견준다.
# 우리 것이 적으면 그 시도·그 해는 다시 받아야 한다.
import argparse, collections, csv, importlib.util, os, re, html, sys, time

# 대조에 쓸 검색어 — 어느 시도에나 흔히 나오고, 결과가 너무 많지 않은 것
PROBES = ["에듀테크", "소프트웨어", "구독", "코딩", "교육자료"]
RAW = {"인천": "ice_candidates.csv", "충북": "충북_candidates.csv", "전남": "전남_candidates.csv",
       "경기": "경기_candidates.csv", "세종": "세종_candidates.csv"}


def load(mod):
    spec = importlib.util.spec_from_file_location(mod, f"{mod}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def source_total(m, kw, year, half=False):
    """원천 화면이 알려 주는 전체 건수"""
    spans = [("0101", "0630"), ("0701", "1231")] if half else [("", "")]
    n = 0
    for s1, s2 in spans:
        st = f"{year}{s1}" if s1 else ""
        ed = f"{year}{s2}" if s2 else ""
        try:
            b = m.fetch(m.safe_kw(kw), 1, year, st, ed)
        except Exception as e:
            return None                      # 원천을 못 읽으면 판단하지 않는다
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", b)))
        g = re.search(r"전체\s*([\d,]+)", t)
        n += int(g.group(1).replace(",", "")) if g else 0
        time.sleep(1.0)
    return n


def mine(path, kw, year):
    if not os.path.exists(path):
        return 0
    csv.field_size_limit(10 ** 7)
    n = 0
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        if r.get("키워드") == kw and (r.get("계약일") or "").startswith(str(year)):
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offices", default="경기,인천,충북,전남,세종")
    ap.add_argument("--years", default="2020,2021,2022,2023,2024,2025,2026")
    a = ap.parse_args()
    m = load("collect_ice")
    bad = []
    print(f'{"시도":<6}{"해":<6}{"검색어":<10}{"원천":>8}{"우리":>8}   판정')
    for off in a.offices.split(","):
        if off not in m.OFFICES:
            continue
        m.URL, m.SYSID, m.MI = m.OFFICES[off]
        m.PAGE = 10 if off == "경기" else 100
        for year in a.years.split(","):
            for kw in PROBES:
                src = source_total(m, kw, year, half=(off == "경기"))
                if src is None:
                    print(f"{off:<6}{year:<6}{kw:<10}{'?':>8}{'':>8}   원천을 못 읽음")
                    continue
                ours = mine(RAW.get(off, ""), kw, year)
                ok = ours >= src * 0.9 or src == 0
                if not ok:
                    bad.append((off, year, kw, src, ours))
                print(f"{off:<6}{year:<6}{kw:<10}{src:>8,}{ours:>8,}   {'✓' if ok else '✗ 모자람'}")
    print()
    if bad:
        print(f"※ 다시 받아야 하는 칸 {len(bad)}개")
        for off, y, kw, s, o in bad[:20]:
            print(f"   {off} {y} '{kw}' — 원천 {s:,} · 우리 {o:,}")
        sys.exit(1)
    print("모든 칸이 원천과 맞는다")


if __name__ == "__main__":
    main()
