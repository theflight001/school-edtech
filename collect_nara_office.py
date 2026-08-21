# 나라장터 시도교육청·교육지원청 계약 수집 — 학교가 아니라 교육청이 산 것.
# 사용: NARA_KEY=<인증키> python3 collect_nara_office.py [--begin 20200101] [--end 20260731]
#
# 왜 따로 모으나: 이 서비스는 '학교 × 제품'을 보여 주므로 수집기가 처음부터 학교만 남긴다.
# 그런데 AI 디지털 교육자료·다채움처럼 시도 전체에 한꺼번에 보급하는 제품은 교육청이 사고
# 학교에는 계약이 남지 않는다. 그래서 화면에서 통째로 안 보인다.
#
# 조심할 것: 이 기록으로는 '어느 학교가 쓰는가'를 알 수 없다. 계약명에 학교 이름이 없다
# (표본 31건 중 0건). 그래서 학교 수에 섞지 않고 제품 화면에 따로 놓는다.
# 교육청 계약의 3분의 1은 냉난방기·전기공사 같은 시설 관급자재다 — 정제 단계에서 걸러진다.
import argparse, csv, json, os, re, sys, time, urllib.request, urllib.parse
from datetime import date, timedelta

BASE = "https://apis.data.go.kr/1230000/ao/CntrctInfoService/getCntrctInfoList"
KEY = os.environ.get("NARA_KEY")
if not KEY:
    sys.exit("NARA_KEY 환경변수에 인증키를 넣어 실행할 것 (코드에 하드코딩 금지)")

OUT, CKPT = "nara_office.csv", ".ckpt_nara_office.json"
FIELDS = ["계약번호", "구분", "계약명", "계약일", "금액", "수요기관", "시도", "업체명", "상세URL"]
OFFICE = re.compile(r"교육청$|교육지원청$")
# 수요기관 이름 앞머리로 시도를 정한다 ('경기도교육청 경기도수원교육지원청' → 경기)
SIDO = [("서울", "서울"), ("부산", "부산"), ("대구", "대구"), ("인천", "인천"), ("광주", "광주"),
        ("대전", "대전"), ("울산", "울산"), ("세종", "세종"), ("경기", "경기"), ("강원", "강원"),
        ("충청북도", "충북"), ("충북", "충북"), ("충청남도", "충남"), ("충남", "충남"),
        ("전라북", "전북"), ("전북", "전북"), ("전라남도", "전남"), ("전남", "전남"),
        ("경상북도", "경북"), ("경북", "경북"), ("경상남도", "경남"), ("경남", "경남"),
        ("제주", "제주")]


def sido_of(name):
    for kw, lab in SIDO:
        if name.startswith(kw):
            return lab
    return ""


def fetch(op, begin, end, page):
    # serviceKey는 인코딩하지 않는다 — urlencode를 거치면 이중 인코딩돼 403이 난다
    params = {"inqryDiv": 1, "inqryBgnDt": begin + "0000", "inqryEndDt": end + "2359",
              "numOfRows": 999, "pageNo": page, "type": "json"}
    url = f"{BASE}{op}?serviceKey={KEY}&" + urllib.parse.urlencode(params)
    for wait in [10, 30, 60, 120, 240, None]:
        try:
            with urllib.request.urlopen(url, timeout=90) as res:
                d = json.load(res)
            b = d["response"]["body"]
            return b.get("items") or [], int(b.get("totalCount", 0))
        except Exception as e:
            if wait is None:
                raise
            print(f"    재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)


def orgs(it):
    """수요기관 목록 — ^로 이어 붙어 오므로 통째로 쪼갠다"""
    raw = (it.get("dminsttList") or "").strip("[]")
    out = [x.strip() for x in re.split(r"[\^,\[\]]", raw) if x.strip()]
    return out or [(it.get("cntrctInsttNm") or "").strip()]


def windows(begin, end):
    b = date(int(begin[:4]), int(begin[4:6]), int(begin[6:]))
    e = date(int(end[:4]), int(end[4:6]), int(end[6:]))
    out = []
    while b <= e:
        nxt = min(b + timedelta(days=89), e)
        out.append((b.strftime("%Y%m%d"), nxt.strftime("%Y%m%d")))
        b = nxt + timedelta(days=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", default="20200101")
    ap.add_argument("--end", default=date.today().strftime("%Y%m%d"))
    a = ap.parse_args()

    ck = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "seen": []}
    done, seen = set(ck["done"]), set(tuple(k) for k in ck["seen"])
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    wins = windows(a.begin, a.end)
    print(f"창 {len(wins)}개 ({a.begin}~{a.end}) × 업무 2종", flush=True)
    kept = calls = 0
    for bg, ed in wins:
        for op, div in (("Thng", "물품"), ("Servc", "용역")):
            if f"{bg}|{op}" in done:
                continue
            page = 1
            while True:
                items, total = fetch(op, bg, ed, page)
                calls += 1
                for it in items:
                    for org in set(orgs(it)):
                        if not OFFICE.search(org):
                            continue
                        key = (it.get("untyCntrctNo"), org)
                        if key in seen:
                            continue
                        seen.add(key)
                        corp = (it.get("corpList") or "").strip("[]").split("^")
                        w.writerow({
                            "계약번호": it.get("untyCntrctNo"),
                            "구분": it.get("bsnsDivNm") or div,
                            "계약명": (it.get("cntrctNm") or "").strip(),
                            "계약일": it.get("cntrctDate"), "금액": it.get("thtmCntrctAmt"),
                            "수요기관": org, "시도": sido_of(org),
                            "업체명": corp[3] if len(corp) > 3 else "",
                            "상세URL": it.get("cntrctDtlInfoUrl") or ""})
                        kept += 1
                f.flush()
                if page * 999 >= total or not items:
                    break
                page += 1
                time.sleep(1.2)
            done.add(f"{bg}|{op}")
            json.dump({"done": sorted(done), "seen": [list(k) for k in seen]},
                      open(CKPT, "w"), ensure_ascii=False)
            print(f"  {bg}~{ed} {div}: 전체 {total:,}건 · 교육청 누적 {kept:,}건 (API {calls:,}회)", flush=True)
    f.close()
    print(f"\n완료 — 교육청 계약 {kept:,}건 (API {calls:,}회) → {OUT}")


if __name__ == "__main__":
    main()
