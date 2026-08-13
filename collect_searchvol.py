# 제품별 월간 검색수 수집기 — 네이버 검색광고 키워드도구에서 받아 온다.
# 사용: NAVER_AD_* 를 환경변수에 두고  python3 collect_searchvol.py
#
# 왜 검색광고 API인가: 데이터랩(검색어트렌드)은 신규 등록이 막혔고, 열려 있어도 상대값(0~100)만
# 준다. 검색광고 키워드도구는 월간 검색수를 절대값으로 주고 PC·모바일이 나뉜다.
#
# 조심할 것:
#   - 네이버는 키워드를 '공백 없는 대문자'로 되돌려 준다(AI 펭톡 → AI펭톡). 맞대 볼 때 같게 만든다.
#   - '< 10'은 열 번 미만이라는 뜻이지 0이 아니다. 원문을 그대로 남기고 숫자는 따로 적는다.
#   - 이름이 짧거나 흔하면(마이클·레서·디딤) 그 검색수는 제품의 것이 아니다.
#     제품 이름 길이를 함께 적어 두어 나중에 사람이 걸러 낼 수 있게 한다.
import argparse, base64, csv, hashlib, hmac, json, os, re, sys, time, urllib.parse, urllib.request

BASE = "https://api.searchad.naver.com"
OUT = "search_volume.csv"
FIELDS = ["제품", "조회어", "PC", "모바일", "합계", "글자수", "확인일"]
GENERIC = {"3D 프린팅/CAD", "AI 면접시스템", "AI·디지털 교육자료", "SW·플랫폼", "VR/XR 장비",
           "기기(PC·태블릿·전자칠판 등)", "드론", "로봇·교구·키트", "운영 부대구매",
           "인프라(교실·설비)", "코스웨어"}
SPACING = 1.0

K = os.environ.get("NAVER_AD_KEY")
S = os.environ.get("NAVER_AD_SECRET")
C = os.environ.get("NAVER_AD_CUSTOMER")
if not (K and S and C):
    sys.exit("NAVER_AD_KEY / NAVER_AD_SECRET / NAVER_AD_CUSTOMER 환경변수가 필요하다 (코드에 넣지 말 것)")


def call(path, params):
    for wait in [5, 20, 60, None]:
        try:
            ts = str(int(time.time() * 1000))
            sig = base64.b64encode(hmac.new(S.encode(), f"{ts}.GET.{path}".encode(),
                                            hashlib.sha256).digest()).decode()
            req = urllib.request.Request(BASE + path + "?" + urllib.parse.urlencode(params),
                headers={"X-Timestamp": ts, "X-API-KEY": K, "X-Customer": C, "X-Signature": sig})
            return json.loads(urllib.request.urlopen(req, timeout=40).read().decode())
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({type(e).__name__}) → {wait}초", flush=True)
            time.sleep(wait)


def key(s):
    """네이버가 돌려주는 형태 — 공백 없는 대문자"""
    return re.sub(r"\s+", "", (s or "")).upper()


def num(v):
    return 0 if v in (None, "< 10", "<10") else int(str(v).replace(",", ""))


def product_names(path):
    s = open(path, encoding="utf-8").read()
    d = json.loads(s[s.index("'") + 1:s.rindex("'")].replace("\\'", "'").replace("\\\\", "\\"))
    return [t for t in d["tagList"] if t not in GENERIC]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", default="data.js")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    names = product_names(a.names)
    if a.limit:
        names = names[:a.limit]
    today = time.strftime("%Y-%m-%d")

    rows, got = [], 0
    print(f"제품 {len(names)}종 · 다섯씩 묶어 {-(-len(names)//5)}번 부른다", flush=True)
    for i in range(0, len(names), 5):
        chunk = names[i:i + 5]
        # 괄호 안 설명은 검색어가 아니다 — '젭(ZEP)'은 '젭'으로 묻는다
        asks = [re.sub(r"\s*[\(（][^)）]*[)）]", "", n).strip() or n for n in chunk]
        try:
            r = call("/keywordstool", {"hintKeywords": ",".join(asks), "showDetail": "1"})
        except Exception as e:
            print(f"  [{i}] 통째로 건너뜀 ({type(e).__name__})", flush=True)
            r = {}
        table = {key(x["relKeyword"]): x for x in r.get("keywordList", [])}
        for n, ask in zip(chunk, asks):
            x = table.get(key(ask))
            pc, mo = (x.get("monthlyPcQcCnt"), x.get("monthlyMobileQcCnt")) if x else ("", "")
            if x:
                got += 1
            rows.append({"제품": n, "조회어": ask, "PC": pc, "모바일": mo,
                         "합계": (num(pc) + num(mo)) if x else "",
                         "글자수": len(re.sub(r"\s", "", ask)), "확인일": today})
        if (i // 5 + 1) % 10 == 0:
            print(f"  {i + len(chunk)}종 · 값 있음 {got}", flush=True)
        time.sleep(SPACING)

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\n완료 — {len(rows)}종 중 값 있음 {got}종 → {OUT}")
    top = sorted([r for r in rows if r["합계"] != ""], key=lambda r: -r["합계"])[:15]
    print("\n검색수 상위 15:")
    for r in top:
        print(f"   {r['제품'][:22]:<24} {r['합계']:>10,}")


if __name__ == "__main__":
    main()
