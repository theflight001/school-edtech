# 제품별 '구매의도 검색' 수집기 — 네이버 검색광고 키워드도구에
# '제품명+가격', '제품명+구독' 같은 조합어를 직접 물어 값을 찾아보는 검색량을 잰다.
# 사용: NAVER_AD_* 를 환경변수에 두고  python3 collect_buyintent.py
#
# 왜 이걸 재는가: 조달 기록은 '학교가 예산으로 산 것'만 본다. 교사·학생·학부모가 개인 돈으로
# 사는 제품은 통째로 안 보인다. 앱스토어 매출 순위로는 못 메운다 — 웹 전용 제품이 빠지고,
# 애플은 순위를 공개하지 않으며, 무엇보다 한국 B2C 에듀테크 상당수(밀크티·아이스크림홈런·
# 웅진스마트올 등)는 앱 안에서 결제하지 않고 전화 상담·방문 계약으로 판다. 스토어를 다 모아도
# 안 잡힌다.
#
# 값을 찾아보는 행동은 그 셋을 다 지나간다. 웹이든 앱이든 전화 상담이든, 사기 전에 값을 묻는다.
# 그래서 '제품명+가격/결제/해지/환불' 검색량은 결제가 어디서 일어나든 남는 흔적이다.
#
# 연관검색어 목록으로는 못 잰다. 네이버는 제품에 따라 연관어를 1개만 돌려주기도 한다
# (ChatGPT·클래스카드가 그랬다). 그러면 '아무도 값을 안 묻는다'와 '네이버가 목록을 안 줬다'가
# 똑같이 0으로 보인다. 실제로 조합어를 직접 물으니 ChatGPT구독 1,270회, 클래스카드가격 100회가
# 있었다. 그래서 '제품명+가격', '제품명+구독' 같은 조합어를 하나하나 직접 묻는다 — 물은 것에는
# 반드시 답이 오므로 0이 진짜 0이다.
#
# 조심할 것:
#   - 비중은 '개인이 사는 제품인가'를 가르는 자이지 '얼마나 팔리나'가 아니다.
#     구매의도 검색 100회가 매출 100건이 아니다.
#   - 이름이 짧거나 흔하면 딴 것이 섞인다 — 밀크티는 음료이기도 하다. 글자수를 함께 적어
#     사람이 걸러 낼 수 있게 한다.
#   - '가입·신청'은 넣지 않았다. 무료 가입도 그렇게 부른다 — 돈을 가리키는 말만 센다.
#   - 이름 검색이 적으면(수십 회) 비중은 흔들린다. 이름 검색도 함께 남긴다.
import argparse, base64, csv, hashlib, hmac, json, os, re, sys, time, urllib.parse, urllib.request

BASE = "https://api.searchad.naver.com"
OUT = "buy_intent.csv"
CKPT = ".ckpt_buyintent.json"
SPACING = 1.2

# 돈을 가리키는 말만 붙인다. '가입·신청·다운로드'는 무료도 그렇게 부르므로 넣지 않는다.
# 해지·환불은 이미 돈을 낸 사람이 쓰는 말이라 특히 세다.
SUFFIX = ["가격", "요금제", "결제", "구독", "해지", "환불", "무료체험", "할인"]
FIELDS = (["제품", "조회어", "글자수", "이름검색", "구매의도", "비중", "응답수"]
          + SUFFIX + ["확인일"])

K = os.environ.get("NAVER_AD_KEY")
S = os.environ.get("NAVER_AD_SECRET")
C = os.environ.get("NAVER_AD_CUSTOMER")
if not (K and S and C):
    sys.exit("NAVER_AD_KEY / NAVER_AD_SECRET / NAVER_AD_CUSTOMER 환경변수가 필요하다 (코드에 넣지 말 것)")


class BadRequest(Exception):
    """검색어가 규칙에 안 맞는다 — 다시 물어도 같은 답이라 기다리지 않는다"""


def call(path, params):
    for wait in [5, 20, 60, None]:
        try:
            ts = str(int(time.time() * 1000))
            sig = base64.b64encode(hmac.new(S.encode(), f"{ts}.GET.{path}".encode(),
                                            hashlib.sha256).digest()).decode()
            req = urllib.request.Request(BASE + path + "?" + urllib.parse.urlencode(params),
                headers={"X-Timestamp": ts, "X-API-KEY": K, "X-Customer": C, "X-Signature": sig})
            return json.loads(urllib.request.urlopen(req, timeout=40).read().decode())
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500 and e.code != 429:
                raise BadRequest(str(e.code))
            if wait is None:
                raise
            print(f"  재시도(HTTP {e.code}) → {wait}초", flush=True)
            time.sleep(wait)
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({type(e).__name__}) → {wait}초", flush=True)
            time.sleep(wait)


def key(s):
    """네이버가 돌려주는 형태 — 공백 없는 대문자"""
    return re.sub(r"\s+", "", (s or "")).upper()


def num(v):
    return 0 if v in (None, "", "< 10", "<10") else int(str(v).replace(",", ""))


def ask_form(n):
    """괄호 안 설명은 검색어가 아니고, 네이버는 공백이 든 검색어를 400으로 거부한다"""
    return re.sub(r"\s+", "", re.sub(r"\s*[\(（][^)）]*[)）]", "", n)) or re.sub(r"\s+", "", n)


def names_with_volume(paths):
    """검색수가 실제로 잡힌 제품만 본다 — 이름 검색이 0이면 비중을 낼 수 없다"""
    seen, out = set(), []
    for p in paths:
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            n, v = r["제품"], str(r.get("합계") or "")
            if v and n not in seen:
                seen.add(n)
                out.append((n, int(v)))
    return sorted(out, key=lambda x: -x[1])


def ask_many(words):
    """다섯씩 묶어 묻고 {공백없는대문자: 검색수}로 돌려준다.
    묶음 하나가 규칙에 안 맞으면 통째로 거부당하므로 그때만 하나씩 다시 묻는다."""
    got = {}
    for i in range(0, len(words), 5):
        chunk = words[i:i + 5]
        try:
            ks = call("/keywordstool", {"hintKeywords": ",".join(chunk),
                                        "showDetail": "1"}).get("keywordList", [])
        except BadRequest:
            ks = []
            for one in chunk:
                try:
                    ks += call("/keywordstool", {"hintKeywords": one,
                                                 "showDetail": "1"}).get("keywordList", [])
                except Exception:
                    pass
                time.sleep(SPACING / 2)
        except Exception as e:
            print(f"  묶음 건너뜀 ({type(e).__name__})", flush=True)
            ks = []
        for x in ks:
            got[key(x.get("relKeyword"))] = (num(x.get("monthlyPcQcCnt"))
                                             + num(x.get("monthlyMobileQcCnt")))
        time.sleep(SPACING)
    return got


def main():
    global SPACING
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-volume", nargs="*",
                    default=["search_volume.csv", "search_volume_blind.csv"])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--spacing", type=float, default=SPACING)
    a = ap.parse_args()
    SPACING = a.spacing

    pairs = names_with_volume(a.from_volume)
    if a.limit:
        pairs = pairs[:a.limit]

    done = set(json.load(open(CKPT))["done"]) if os.path.exists(CKPT) else set()
    new_file = not os.path.exists(a.out)
    f = open(a.out, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    today = time.strftime("%Y-%m-%d")
    hit = 0
    print(f"제품 {len(pairs):,}종 × 말 {len(SUFFIX)}가지 (이미 본 것 {len(done):,}종)", flush=True)
    for i, (n, base) in enumerate(pairs, 1):
        if n in done:
            continue
        ask = ask_form(n)
        got = ask_many([ask + sfx for sfx in SUFFIX])
        vals = {sfx: got.get(key(ask + sfx)) for sfx in SUFFIX}
        tot = sum(v for v in vals.values() if v)
        ans = sum(1 for v in vals.values() if v is not None)
        if tot:
            hit += 1
        row = {"제품": n, "조회어": ask, "글자수": len(key(ask)), "이름검색": base,
               "구매의도": tot, "비중": f"{tot / base:.4f}" if base else "",
               "응답수": ans, "확인일": today}
        row.update({sfx: ("" if vals[sfx] is None else vals[sfx]) for sfx in SUFFIX})
        w.writerow(row)
        f.flush()
        done.add(n)
        json.dump({"done": sorted(done)}, open(CKPT, "w"), ensure_ascii=False)
        if i % 25 == 0:
            print(f"  {i:,}종 · 구매의도 잡힌 제품 {hit:,}", flush=True)
    f.close()
    print(f"\n완료 — 구매의도 검색이 잡힌 제품 {hit:,}종 → {a.out}")


if __name__ == "__main__":
    main()
