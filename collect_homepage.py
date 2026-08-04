# 학교 홈페이지 외부 링크 수집기 — 조달 기록에 안 남는 무료·무상 제품을 찾기 위한 경로
# 사용: python3 collect_homepage.py --sido 서울 [--limit 200] [--workers 12]
# 배경: 무료 LMS·협업도구는 돈이 오가지 않아 조달 기록에 안 잡히지만,
#       학교 홈페이지에는 바로가기 배너·링크로 걸려 있는 경우가 많다.
# 결과: homepage_links.csv (학교, 도메인, 링크 문구, 원본 URL)
#       어떤 제품인지 판정하지 않고 '무엇이 걸려 있나'만 모은다. 판정은 사람이 목록을 보고 정한다.
import argparse, collections, concurrent.futures, csv, html, json, re, ssl, sys
import urllib.parse, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
OUT = "homepage_links.csv"
FIELDS = ["학교", "시도", "도메인", "링크문구", "링크URL"]

# 학교 홈페이지 자체와 공공 인프라·일반 포털은 제품이 아니다
SKIP_DOM = re.compile(
    r"(^|\.)(go\.kr|sen\.kr|sen\.hs\.kr|sen\.ms\.kr|sen\.es\.kr|ice\.kr|pen\.kr|"
    r"naver\.com|daum\.net|kakao\.com|google\.com|youtube\.com|youtu\.be|facebook\.com|"
    r"instagram\.com|twitter\.com|x\.com|adobe\.com|microsoft\.com|apple\.com|"
    r"hancom\.com|w3\.org|jquery\.com|bootstrapcdn\.com|jsdelivr\.net|gstatic\.com|"
    r"googleapis\.com|cloudflare\.com|kakaocdn\.net|pstatic\.net)$")

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE          # 학교 홈페이지는 인증서가 만료된 곳이 흔하다

def fetch(url):
    for u in ([url] if url.startswith("http") else ["http://" + url, "https://" + url]):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            raw = urllib.request.urlopen(req, timeout=15, context=_ctx).read()[:600_000]
            for enc in ("utf-8", "cp949", "euc-kr"):
                try:
                    return u, raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return u, raw.decode("utf-8", "replace")
        except Exception:
            continue
    return None, None

def links_of(page_url, page_html):
    """<a href> 와 링크 문구를 뽑아 외부 도메인만 남긴다"""
    host = urllib.parse.urlparse(page_url).hostname or ""
    base = ".".join(host.split(".")[-3:])          # 학교 자체 도메인은 제외하기 위한 기준
    out = {}
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page_html, re.S | re.I):
        href, text = m.group(1).strip(), m.group(2)
        if not href.startswith("http"):
            continue
        h = urllib.parse.urlparse(href).hostname or ""
        if not h or h == host or h.endswith(base) or SKIP_DOM.search(h):
            continue
        # 이미지 배너면 alt 문구를 쓴다
        alt = re.search(r'alt=["\']([^"\']{1,40})["\']', text)
        label = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text))).strip()
        if not label and alt:
            label = html.unescape(alt.group(1)).strip()
        out.setdefault(h, (label[:40], href[:200]))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sido", default="서울")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()

    schools = [s for s in json.load(open("school_master.json", encoding="utf-8"))["schools"]
               if s["sido"].startswith(a.sido) and (s.get("homepage") or "").strip()]
    if a.limit:
        schools = schools[:a.limit]
    print(f"{a.sido} 홈페이지 보유 {len(schools)}개교 · 동시 {a.workers}", flush=True)

    rows, fail = [], 0
    done = 0
    def work(s):
        u, page = fetch(s["homepage"].strip())
        if not page:
            return s, None
        return s, links_of(u, page)

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for s, found in ex.map(work, schools):
            done += 1
            if found is None:
                fail += 1
            else:
                for dom, (label, href) in found.items():
                    rows.append({"학교": s["name"], "시도": a.sido, "도메인": dom,
                                 "링크문구": label, "링크URL": href})
            if done % 100 == 0:
                print(f"  {done}/{len(schools)} · 링크 {len(rows)}건 · 실패 {fail}", flush=True)

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    dom = collections.Counter(r["도메인"] for r in rows)
    print(f"\n완료 — {len(schools)}개교 중 {len(schools)-fail}개교 응답, 외부 링크 {len(rows)}건 "
          f"/ 도메인 {len(dom)}종 → {OUT}")
    print("가장 많이 걸린 도메인 30개:")
    for d, n in dom.most_common(30):
        ex_label = next((r["링크문구"] for r in rows if r["도메인"] == d and r["링크문구"]), "")
        print(f"  {n:5}개교  {d:38} {ex_label[:24]}")

if __name__ == "__main__":
    main()
