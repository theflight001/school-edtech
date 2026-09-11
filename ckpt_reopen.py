# 월 갱신 전에, 다시 훑어야 할 기간의 '끝냄' 표식을 체크포인트에서 걷어낸다.
# 쓰기:  python3 ckpt_reopen.py --from 2026-06 --to 2026-08            (무엇이 걷히는지만 본다)
#        python3 ckpt_reopen.py --from 2026-06 --to 2026-08 --apply    (백업 뒤 걷어낸다)
#
# 왜: 수집기는 한 번 훑은 (검색어·기간)을 체크포인트에 '끝냄'으로 적고 다시는 부르지 않는다.
# 월 갱신이 이 표식을 지우지 않아, 기간이 끝나기 전에 한 번 훑은 곳은 그 뒤 올라온 계약을
# 영영 받지 못했다(2026-09-12 발견: 강원은 새 목록 3,964종이 모두 '끝냄'이라 8월 재수집이
# 427번만 부르고 끝났다. 광주 2026년 4,384종, 경기 2026 하반기 1,659종도 같은 처지).
# 받은 줄은 체크포인트의 seen이 막으므로 다시 훑어도 겹치지 않는다 — seen은 건드리지 않는다.
#
# 표식 꼴(수집기마다 다르다):
#   "검색어"                  강원·울산 — 기간이 없다. 목록이 최신순이라 모두 다시 훑는다
#   "검색어|YYYY"             인천·충북·전남·세종·대전·충남·경남·광주
#   "검색어|YYYY|H"           경기(--half: 0=1~6월, 1=7~12월)
#   ["검색어","YYYY/MM/01"]   부산·경북
#   ["검색어","YYYY","MM"]    대구
#   "YYYY"                    제주
#   "YYYYMMDD|…"              S2B·나라장터 입찰·교육청 일괄(창의 첫날)
import argparse, glob, json, os, re, shutil, time

MONTHLY = [".ckpt_강원.json", ".ckpt_use.json", ".ckpt_ice.json", ".ckpt_충북.json", ".ckpt_전남.json",
           ".ckpt_세종.json", ".ckpt_dje.json", ".ckpt_충남.json", ".ckpt_경남.json", ".ckpt_gen.json",
           ".ckpt_경기.json", ".ckpt_pen.json", ".ckpt_경북.json", ".ckpt_dge.json", ".ckpt_제주.json",
           ".ckpt_s2b_excel.json", ".ckpt_nara_bid.json", ".ckpt_nara_office.json"]
NO_PERIOD = {".ckpt_강원.json", ".ckpt_use.json"}


def span(x):
    """표식 하나 → (첫 달, 끝 달) YYYYMM. 기간이 없으면 None"""
    if isinstance(x, list):
        if len(x) == 3:
            return (int(x[1]) * 100 + int(x[2]),) * 2
        m = re.match(r"(\d{4})/(\d{2})", str(x[1]))
        return (int(m[1]) * 100 + int(m[2]),) * 2 if m else None
    s = str(x)
    if m := re.fullmatch(r"(\d{4})(\d{2})\d{2}\|.*", s):
        return (int(m[1]) * 100 + int(m[2]),) * 2
    if m := re.fullmatch(r".*\|(\d{4})\|([01])", s):
        y, h = int(m[1]), int(m[2])
        return (y * 100 + (7 if h else 1), y * 100 + (12 if h else 6))
    if m := re.fullmatch(r"(?:.*\|)?(\d{4})", s):
        return (int(m[1]) * 100 + 1, int(m[1]) * 100 + 12)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", required=True, help="YYYY-MM")
    ap.add_argument("--to", required=True, help="YYYY-MM")
    ap.add_argument("--only", help="이 체크포인트만(쉼표로) — 돌고 있는 수집기의 것은 빼야 한다")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    lo, hi = (int(v.replace("-", "")) for v in (a.frm, a.to))
    files = [f for f in MONTHLY if os.path.exists(f)]
    if a.only:
        want = {w if w.startswith(".ckpt_") else f".ckpt_{w}.json" for w in a.only.split(",")}
        files = [f for f in files if f in want]
    stamp = time.strftime("%Y%m%d_%H%M%S")
    for f in files:
        c = json.load(open(f, encoding="utf-8"))
        done = c.get("done", [])
        if f in NO_PERIOD:
            keep = []
        else:
            keep = [x for x in done if not ((s := span(x)) and s[0] <= hi and s[1] >= lo)]
        gone = len(done) - len(keep)
        print(f"{f:24s} 끝냄 {len(done):>6,} → {len(keep):>6,} (다시 훑을 것 {gone:,})")
        if a.apply and gone:
            os.makedirs("ckpt_backup", exist_ok=True)
            shutil.copy2(f, f"ckpt_backup/{f.lstrip('.')}.{stamp}")
            c["done"] = keep
            tmp = f + ".tmp"
            json.dump(c, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
            os.replace(tmp, f)
    if not a.apply:
        print("(보기만 했다 — 걷어내려면 --apply)")


if __name__ == "__main__":
    main()
