# 제품별 앱 지표 수집기 — 구글플레이 공개 페이지에서 설치 수·평점·리뷰 수를 받아 온다.
# 사용: python3 collect_appstore.py [--names data.js] [--limit 0]
#
# 왜 필요한가: 조달 기록은 '학교가 예산으로 산 것'만 보여 준다. 무료이거나 교사·학생이
# 개인으로 쓰는 제품은 계약이 없어 통째로 안 보인다(에듀집 2,606종 중 84%가 그렇다).
# 앱 지표는 그 사각지대의 일부를 비춘다 — 표본 조사에서 사각지대의 15%가 앱을 갖고 있었다.
#
# 조심할 것:
#   - 이름이 겹치는 앱이 많다(캔바/캔바스, 디딤, 레서 …). 그래서 고른 앱 이름을 그대로 적어
#     사람이 나중에 훑어볼 수 있게 한다. 애매하면 비워 둔다.
#   - 설치 수는 구간값('100만+')이고 나라별로 갈라지지 않는다. 도입 학교 수와 같은 칸에
#     놓으면 안 된다 — 성격이 다른 숫자다.
import argparse, csv, json, os, re, sys, time, urllib.parse, urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
OUT = "app_metrics.csv"
CKPT = ".ckpt_appstore.json"
FIELDS = ["제품", "앱이름", "패키지", "개발사", "홈페이지", "설치수", "평점", "리뷰수", "일치도", "확인일"]
SPACING = 1.2
GENERIC = {"3D 프린팅/CAD", "AI 면접시스템", "AI·디지털 교육자료", "SW·플랫폼", "VR/XR 장비",
           "기기(PC·태블릿·전자칠판 등)", "드론", "로봇·교구·키트", "운영 부대구매",
           "인프라(교실·설비)", "코스웨어"}


def get(url):
    for wait in [5, 20, 60, None]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko"})
            return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            time.sleep(wait)


def norm(x):
    return re.sub(r"[\s·ㆍ\-_()\[\]!:,.]+", "", (x or "")).lower()


def bigrams(x):
    t = norm(x)
    return {t[i:i + 2] for i in range(len(t) - 1)} or {t}


def sim(a, b):
    A, B = bigrams(a), bigrams(b)
    return 2 * len(A & B) / (len(A) + len(B)) if A and B else 0


def search(name):
    """검색 결과에서 패키지 아이디를 순서대로 (앞쪽이 더 잘 맞는다)"""
    q = urllib.parse.urlencode({"q": name, "c": "apps", "hl": "ko", "gl": "KR"})
    h = get(f"https://play.google.com/store/search?{q}")
    return list(dict.fromkeys(re.findall(r"/store/apps/details\?id=([A-Za-z0-9_.]+)", h)))[:4]


def detail(pkg):
    """앱 상세 — 이름·개발사·평점·리뷰수는 ld+json에, 설치 수는 '다운로드' 라벨 옆에 있다"""
    d = get(f"https://play.google.com/store/apps/details?id={pkg}&hl=ko&gl=KR")
    out = {"패키지": pkg, "앱이름": "", "개발사": "", "홈페이지": "", "평점": "", "리뷰수": "", "설치수": ""}
    for m in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', d, re.S):
        try:
            j = json.loads(m)
        except Exception:
            continue
        if j.get("@type") not in ("SoftwareApplication", None) and "aggregateRating" not in j:
            continue
        out["앱이름"] = j.get("name") or out["앱이름"]
        out["개발사"] = (j.get("author") or {}).get("name", "")
        out["홈페이지"] = (j.get("author") or {}).get("url", "")   # 개발사가 적어 둔 제품 홈페이지
        ar = j.get("aggregateRating") or {}
        if ar.get("ratingValue"):
            out["평점"] = f'{float(ar["ratingValue"]):.2f}'
        out["리뷰수"] = str(ar.get("ratingCount") or "")
        break
    i = d.find("다운로드")
    if i > 0:
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", d[max(0, i - 120):i]))
        m = re.findall(r"([\d.,]+\s*[만천억]?\+)", txt)
        if m:
            out["설치수"] = m[-1].strip()
    return out


def product_names(path):
    """data.js의 제품 태그 (제품군은 뺀다)"""
    s = open(path, encoding="utf-8").read()
    d = json.loads(s[s.index("'") + 1:s.rindex("'")].replace("\\'", "'").replace("\\\\", "\\"))
    return [t for t in d["tagList"] if t not in GENERIC]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", default="data.js")
    ap.add_argument("--extra", help="추가로 볼 이름 목록 파일 (줄 단위)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-sim", type=float, default=0.5, help="이 밑이면 다른 앱으로 보고 비워 둔다")
    a = ap.parse_args()

    names = product_names(a.names)
    if a.extra and os.path.exists(a.extra):
        names += [l.strip() for l in open(a.extra, encoding="utf-8") if l.strip()]
    names = list(dict.fromkeys(names))
    if a.limit:
        names = names[:a.limit]

    done = set(json.load(open(CKPT))["done"]) if os.path.exists(CKPT) else set()
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    today = time.strftime("%Y-%m-%d")
    hit = miss = 0
    print(f"제품 {len(names)}종 (이미 본 것 {len(done)}종)", flush=True)
    for i, n in enumerate(names, 1):
        if n in done:
            continue
        # 닮은 정도만으로 고르면 'AI 한자몬'이 'AI 한자쓰기연습'에 붙는다.
        # 한쪽 이름이 다른 쪽에 통째로 들어 있는 후보만 남기고, 그중 가장 닮은 것을 고른다.
        # 제품 이름이 앱 이름 안에 들어 있어야 한다(반대 방향은 안 된다 —
        # 'ALC 학습분석 시스템'이 'ALC'라는 딴 앱에 붙는다). 검색 순위가 앞선 것을 먼저 쓴다:
        # 'AI 펭톡'은 정식 앱('인공지능 학습 메이트 AI 펭톡')이 1등이고 홍보관 앱이 2등이다.
        def inside(prod, app):
            a1, a2 = norm(prod), norm(app)
            return bool(len(a1) >= 4 and a2 and a1 in a2)
        best = None
        try:
            for pkg in search(n):
                time.sleep(SPACING)
                d = detail(pkg)
                if inside(n, d["앱이름"]):
                    best = (d, sim(n, d["앱이름"]))
                    break
        except Exception as e:
            print(f"  [{n}] 건너뜀 ({type(e).__name__})", flush=True)
        row = {"제품": n, "확인일": today, "일치도": ""}
        # 이름이 통째로 들어 있으면 그것으로 충분하다 — 'AI 펭톡'의 정식 앱 이름은
        # '인공지능 학습 메이트 AI 펭톡'이라 닮은 정도로만 재면 0.40밖에 안 나온다.
        # 다만 두 글자 이하 이름은 우연히 들어갈 수 있어 닮은 정도까지 본다.
        if best:
            row.update(best[0]); row["일치도"] = f"{best[1]:.2f}"; hit += 1
        else:
            miss += 1
        w.writerow({k: row.get(k, "") for k in FIELDS})
        f.flush()
        done.add(n)
        json.dump({"done": sorted(done)}, open(CKPT, "w"), ensure_ascii=False)
        if i % 20 == 0:
            print(f"  {i}종 · 앱 있음 {hit} · 없음 {miss}", flush=True)
        time.sleep(SPACING)
    f.close()
    print(f"\n완료 — 앱 있음 {hit} · 없음 {miss} → {OUT}")


if __name__ == "__main__":
    main()
