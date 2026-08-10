# 나라장터 입찰공고 수집 — 학교가 발주한 공고만 남긴다.
# 사용: NARA_BID_KEY=<인증키> python3 collect_nara_bid.py --begin 20260701 --end 20260731
#
# 계약정보(collect_nara_full.py)와 다른 API다. 활용신청도 따로 받아야 하고 인증키도 다르다
# (계약정보는 NARA_KEY, 입찰공고는 NARA_BID_KEY).
# serviceKey는 urlencode에 넣지 않는다 — 이중 인코딩되면 '등록되지 않은 서비스키'로 거부된다.
#
# 학교 판별: 수요기관명(dminsttNm)이 학교로 끝나는 것. 없으면 공고기관명(ntceInsttNm)을 본다.
import argparse, csv, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import date, timedelta

BASE = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfo"
KEY = os.environ.get("NARA_BID_KEY")
if not KEY:
    sys.exit("NARA_BID_KEY 환경변수에 입찰공고용 인증키를 넣어 실행할 것 (코드에 하드코딩 금지)")
OPS = [("ThngPPSSrch", "물품"), ("ServcPPSSrch", "용역"), ("CnstwkPPSSrch", "공사")]
OUT = "nara_bid.csv"
CKPT = ".ckpt_nara_bid.json"
FIELDS = ["공고번호", "구분", "공고명", "공고일", "기초금액", "수요기관", "학교명", "공고기관", "입찰방식"]
SCHOOL_END = re.compile(r"(초등학교|중학교|고등학교|영재학교|특수학교)$")
SPACING = 0.4

def fetch(op, begin, end, page):
    q = {"inqryDiv": 1, "inqryBgnDt": begin + "0000", "inqryEndDt": end + "2359",
         "numOfRows": 999, "pageNo": page, "type": "json"}
    url = f"{BASE}{op}?serviceKey={KEY}&" + urllib.parse.urlencode(q)
    # 서버가 붐빌 때 JSON 대신 오류 XML을 돌려준다 — 그때는 재시도한다(예전엔 여기서 죽었다)
    for wait in [10, 30, 60, 180, 600, None]:
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                raw = r.read().decode("utf-8", "replace")
            d = json.loads(raw)
            b = d["response"]["body"]
            return b.get("items") or [], int(b.get("totalCount", 0))
        except Exception as e:
            if wait is None:
                print(f"  끝내 실패 — 이 창은 건너뛴다 ({e})", flush=True)
                return [], 0
            print(f"  재시도({type(e).__name__}) → {wait}초", flush=True)
            time.sleep(wait)

def school_of(item):
    for k in ("dminsttNm", "ntceInsttNm"):
        n = (item.get(k) or "").strip()
        if SCHOOL_END.search(n):
            return n
    return ""

def windows(begin, end, days=30):
    b = date(int(begin[:4]), int(begin[4:6]), int(begin[6:]))
    e = date(int(end[:4]), int(end[4:6]), int(end[6:]))
    while b <= e:
        stop = min(b + timedelta(days=days - 1), e)
        yield b.strftime("%Y%m%d"), stop.strftime("%Y%m%d")
        b = stop + timedelta(days=1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", default="20230101")
    ap.add_argument("--end", default=date.today().strftime("%Y%m%d"))
    ap.add_argument("--days", type=int, default=30, help="한 창의 길이(일)")
    a = ap.parse_args()

    ckpt = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": []}
    done = set(ckpt["done"])
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    wins = list(windows(a.begin, a.end, a.days))
    print(f"창 {len(wins)}개 ({a.begin}~{a.end}) × 업무 {len(OPS)}종", flush=True)
    kept = api = 0
    for bdt, edt in wins:
        for op, label in OPS:
            tag = f"{bdt}|{op}"
            if tag in done:
                continue
            page, total, seen_n = 1, None, 0
            while True:
                items, tot = fetch(op, bdt, edt, page)
                api += 1
                if total is None:
                    total = tot
                for it in items:
                    sc = school_of(it)
                    if not sc:
                        continue
                    w.writerow({"공고번호": f"{it.get('bidNtceNo','')}-{it.get('bidNtceOrd','')}",
                                "구분": label, "공고명": it.get("bidNtceNm", ""),
                                "공고일": (it.get("bidNtceDt") or "")[:10].replace("/", "-"),
                                "기초금액": re.sub(r"[^\d]", "", it.get("bssamt") or ""),
                                "수요기관": it.get("dminsttNm", ""), "학교명": sc,
                                "공고기관": it.get("ntceInsttNm", ""),
                                "입찰방식": it.get("bidMethdNm", "")})
                    kept += 1
                seen_n += len(items)
                f.flush()
                if not items or seen_n >= total:
                    break
                page += 1
                time.sleep(SPACING)
            done.add(tag)
            ckpt["done"] = sorted(done)
            with open(CKPT, "w") as cf:
                json.dump(ckpt, cf, ensure_ascii=False)
            print(f"[{bdt}~{edt} {label}] 전체 {total:,}건 중 학교 공고 누적 {kept:,}건 (API {api}회)", flush=True)
            time.sleep(SPACING)
    f.close()
    print(f"\n완료 — API {api}회, 학교 입찰공고 {kept:,}건 → {OUT}")

if __name__ == "__main__":
    main()
