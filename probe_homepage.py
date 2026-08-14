# 학교 홈페이지에서 에듀테크 제품 이름을 찾을 수 있는지 시험한다 (표본 조사).
# 사용: python3 probe_homepage.py [--n 100] [--seed 1]
#
# 왜: 조달 기록은 '학교가 예산으로 산 것'만 본다. 무료로 쓰거나 개인이 결제하는 제품은
# 통째로 안 보인다. 학교 홈페이지의 가정통신문·공지("○○ 활용 안내", "△△ 가입 안내")는
# 그 학교가 실제로 썼다는 직접 증거이고, 우리 자료와 같은 단위(학교 × 제품)로 나온다.
#
# 이 스크립트는 전면 수집기가 아니라 '건질 게 있는지' 재 보는 자다. 학교마다 홈페이지
# 구조가 달라 실제 수확률을 모르면 1만 개교를 훑는 일이 헛수고가 될 수 있다.
import argparse, csv, html, json, os, random, re, sys, time, urllib.parse, urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
TIMEOUT = 20
GENERIC = {"3D 프린팅/CAD", "AI 면접시스템", "AI·디지털 교육자료", "SW·플랫폼", "VR/XR 장비",
           "기기(PC·태블릿·전자칠판 등)", "드론", "로봇·교구·키트", "운영 부대구매",
           "인프라(교실·설비)", "코스웨어"}
# 알림 성격의 게시판으로 보이는 링크 (학교마다 이름이 다르다)
BOARD = re.compile(r"가정통신문|공지사항|알림장|알림마당|학교소식|일반소식|공지|소식")


def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko"})
        raw = urllib.request.urlopen(req, timeout=TIMEOUT).read()
        for enc in ("utf-8", "euc-kr", "cp949"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", "replace")
    except Exception:
        return ""


def text_of(h):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))


def links(base, h):
    out = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', h, re.S | re.I):
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))).strip()
        if BOARD.search(label):
            out.append((urllib.parse.urljoin(base, m.group(1)), label))
    return out


def product_names():
    s = open("data.js", encoding="utf-8").read()
    d = json.loads(s[s.index("'") + 1:s.rindex("'")].replace("\\'", "'").replace("\\\\", "\\"))
    names = [t for t in d["tagList"] if t not in GENERIC]
    if os.path.exists("edzip_blind.txt"):
        names += [l.strip() for l in open("edzip_blind.txt", encoding="utf-8") if l.strip()]
    # 두 글자 이하나 흔한 낱말은 우연히 걸린다 — 시험에서는 네 글자 이상만 본다
    return sorted({n for n in names if len(re.sub(r"\s", "", n)) >= 4}, key=len, reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--pages", type=int, default=3, help="학교마다 볼 게시판 수")
    a = ap.parse_args()

    schools = [s for s in json.load(open("school_master.json", encoding="utf-8"))["schools"]
               if (s.get("homepage") or "").startswith("http")]
    random.seed(a.seed)
    pick = random.sample(schools, min(a.n, len(schools)))
    names = product_names()
    print(f"홈페이지가 있는 학교 {len(schools):,}개교 중 {len(pick)}개교 시험 · 제품 이름 {len(names):,}종", flush=True)

    rows, hit_home, hit_board, err = [], 0, 0, 0
    for i, s in enumerate(pick, 1):
        home = get(s["homepage"])
        if not home:
            err += 1
            continue
        pages = [("(첫 화면)", text_of(home))]
        for url, label in links(s["homepage"], home)[:a.pages]:
            t = text_of(get(url))
            if t:
                pages.append((label, t))
            time.sleep(0.3)
        found = {}
        for label, t in pages:
            for n in names:
                if n in t:
                    found.setdefault(n, label)
        if found:
            (hit_home if len(pages) == 1 else hit_board)
            for n, label in found.items():
                rows.append({"학교": s["name"], "제품": n, "찾은 곳": label, "주소": s["homepage"]})
        if i % 10 == 0:
            print(f"  {i}개교 · 제품이 나온 학교 {len({r['학교'] for r in rows})}곳 · "
                  f"기록 {len(rows)}건 · 못 연 곳 {err}", flush=True)
        time.sleep(0.3)

    with open("homepage_probe.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["학교", "제품", "찾은 곳", "주소"])
        w.writeheader()
        w.writerows(rows)
    got = len({r["학교"] for r in rows})
    print(f"\n시험 끝 — {len(pick)}개교 중 {got}곳({got / len(pick) * 100:.0f}%)에서 제품 이름을 찾았다")
    print(f"   기록 {len(rows)}건 · 홈페이지를 못 연 곳 {err}곳 → homepage_probe.csv")
    import collections
    c = collections.Counter(r["제품"] for r in rows)
    print("\n자주 나온 제품:", c.most_common(15))


if __name__ == "__main__":
    main()
