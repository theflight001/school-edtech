# -*- coding: utf-8 -*-
# 강원특별자치도교육청 '수의계약공개' 게시판 수집기 — 학교가 달마다 올리는 수의계약(100만원 이상) 공개 글의 PDF를 읽는다.
# 사용: python3 collect_gwe_board.py [--from 2023-10 --to 2025-09]
#
# 왜 또 만드나: K-에듀파인 연계 화면(수의계약내역공개·계약체결)에는 2023년 11월 ~ 2025년 9월 계약이 없다
# (2026-10-02 확인: 목록이 2025-09-26에서 2023-10-25로 건너뛴다). 그런데 같은 사이트의 게시판에는
# 기관별 월간 공개 글(2020년 9월~, 8,600여 건)이 PDF 첨부로 남아 있다. 그 PDF는 K-에듀파인 '수의계약 공개내역'
# 양식이라 계약명·계약일자·계약금액·업체명을 읽을 수 있다. 다만 글을 올린 기관만 있어 전수는 아니다.
#
# 결과는 강원_candidates.csv와 같은 열로 강원_board_candidates.csv에 적는다(키워드 칸은 '(게시판)'). 정제는
# refine_office.py '강원'이 두 파일을 합쳐 읽도록 한다. 간격은 다른 수집기와 같이 EDTECH_SPACING(기본 10초).
import argparse, csv, html, io, json, os, re, sys, time, urllib.parse, urllib.request, random

BASE = "https://www.gwe.go.kr"
KEY = "bTIzMDUzMTA3NjgwMDM="
LIST = f"{BASE}/open/bbs/list.do?key={KEY}"
VIEW = f"{BASE}/open/bbs/view.do"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
OUT, CKPT = "강원_board_candidates.csv", ".ckpt_강원_board.json"
FIELDS = ["회계연도", "기관명", "계약명", "계약일", "계약금액", "계약방법", "계약상대자", "키워드"]
SPACING = float(os.environ.get("EDTECH_SPACING", "10"))
MAXREQ = int(os.environ.get("EDTECH_MAXREQ", "5000"))
_used = [0]

class BudgetOut(Exception):
    pass

def polite():
    _used[0] += 1
    if _used[0] > MAXREQ:
        raise BudgetOut(f"이번 실행 상한 {MAXREQ:,}회를 다 썼다")
    time.sleep(SPACING * random.uniform(0.8, 1.4))

def get(url, data=None, referer=LIST, binary=False):
    req = urllib.request.Request(url, data=(urllib.parse.urlencode(data).encode() if data else None),
                                 headers={"User-Agent": UA, "Referer": referer})
    for wait in [30, 120, None]:
        try:
            b = urllib.request.urlopen(req, timeout=120).read()
            return b if binary else b.decode("utf-8", "replace")
        except Exception as e:
            if wait is None:
                raise
            print(f"  재시도({e}) → {wait}초", flush=True)
            time.sleep(wait)

TITLE_RE = re.compile(r"(\d{4})\s*년\s*(\d{1,2})\s*월")

def list_posts(page):
    """목록 한 쪽 → [{sn, title, date}]"""
    h = get(f"{LIST}&pageIndex={page}")
    rows = []
    for m in re.finditer(r'goView\(\'(\d+)\'[^>]*title="([^"]*)".*?<td[^>]*>\s*(\d{4}-\d{2}-\d{2})\s*</td>', h, re.S):
        rows.append({"sn": m.group(1), "title": html.unescape(m.group(2)).strip(), "date": m.group(3)})
    return rows

def post_files(sn, page):
    h = get(VIEW, {"bbsSn": sn, "key": KEY, "referer": "", "pageIndex": str(page), "menuSn": KEY})
    files = re.findall(r'href="(/cmm/fileDown\.do\?encKey=[^"&]+&(?:amp;)?type=bbs)"', h)
    names = re.findall(r'([^">/\s][^">/]{1,80}\.(?:pdf|PDF|hwpx?|HWPX?|xlsx?|XLSX?))', html.unescape(h))
    return [f.replace("&amp;", "&") for f in files], names

AMT_RE = re.compile(r"(\d{4}\.\d{2}\.\d{2})\s+([\d,]+)\s+([\d,]+)\s+[\d.]+")

def parse_pdf(b, inst_hint):
    """K-에듀파인 '수의계약 공개내역' PDF — 한 쪽에 계약 하나"""
    import pdfplumber
    out = []
    with pdfplumber.open(io.BytesIO(b)) as pdf:
        for pg in pdf.pages:
            t = pg.extract_text() or ""
            if "수의계약" not in t or "계 약 명" not in t:
                continue
            fy = re.search(r"회계연도\s*:\s*(\d{4})", t)
            nm = re.search(r"계 약 명\s*(.+)", t)
            am = AMT_RE.search(t)
            vend = ""
            lines = t.splitlines()
            for i, ln in enumerate(lines):
                if "업 체 명" in ln:
                    # 머리줄 다음에 '계약상대자' 표식 줄이 오고 그 다음 줄이 '업체명 대표자' — 마지막 낱말(대표자)을 뗀다
                    for j in range(i + 1, min(i + 4, len(lines))):
                        toks = lines[j].split()
                        if toks and toks[0] != "계약상대자":
                            vend = " ".join(toks[:-1]) if len(toks) > 1 else toks[0]
                            break
                    break
            inst = ""
            for ln in reversed(lines):
                m2 = re.search(r"강원(?:특별자치)?도교육청\s+(\S+)", ln)
                if m2:
                    inst = m2.group(1); break
            if not nm or not am:
                continue
            out.append({"회계연도": fy.group(1) if fy else "", "기관명": inst or inst_hint,
                        "계약명": nm.group(1).strip(), "계약일": am.group(1).replace(".", "-"),
                        "계약금액": am.group(3).replace(",", ""), "계약방법": "수의계약(게시판)",
                        "계약상대자": vend, "키워드": "(게시판)"})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="ym_from", default="2023-10")
    ap.add_argument("--to", dest="ym_to", default="2025-09")
    ap.add_argument("--start-page", type=int, default=1)
    ap.add_argument("--max-pages", type=int, default=900)
    a = ap.parse_args()
    ck = json.load(open(CKPT)) if os.path.exists(CKPT) else {"done": [], "page": a.start_page, "skipped": []}
    done = set(ck["done"])
    new = not os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8-sig", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new:
        w.writeheader()
    kept = 0
    page = max(a.start_page, ck.get("page", 1))
    try:
        while page <= a.max_pages:
            polite()
            posts = list_posts(page)
            if not posts:
                print(f"{page}쪽: 글 없음 — 끝", flush=True); break
            oldest = min(p["date"] for p in posts)
            for p in posts:
                if p["sn"] in done:
                    continue
                m = TITLE_RE.search(p["title"])
                ym = f"{m.group(1)}-{int(m.group(2)):02d}" if m else p["date"][:7]
                if not (a.ym_from <= ym <= a.ym_to):
                    done.add(p["sn"]); continue
                inst = re.sub(r".*?\d{1,2}\s*월\s*", "", p["title"]).split("수의계약")[0].strip() if m else ""
                polite()
                files, names = post_files(p["sn"], page)
                rows = []
                if not files:
                    ck["skipped"].append([p["sn"], p["title"][:40], "첨부 없음"])
                for fu in files[:3]:
                    polite()
                    b = get(BASE + fu, referer=VIEW, binary=True)
                    if not b.startswith(b"%PDF"):
                        ck["skipped"].append([p["sn"], p["title"][:40], "PDF 아님"]); continue
                    try:
                        rows += parse_pdf(b, inst)
                    except Exception as e:
                        ck["skipped"].append([p["sn"], p["title"][:40], f"읽기 실패 {e}"[:60]])
                for r in rows:
                    w.writerow(r); kept += 1
                f.flush()
                done.add(p["sn"])
                print(f"[{ym}] {p['title'][:34]} → {len(rows)}건 (누적 {kept}, 요청 {_used[0]})", flush=True)
            ck["done"], ck["page"] = sorted(done), page + 1
            json.dump(ck, open(CKPT + ".tmp", "w"), ensure_ascii=False); os.replace(CKPT + ".tmp", CKPT)
            if oldest < a.ym_from + "-01":
                print(f"{page}쪽의 가장 오래된 글이 {oldest} — 범위 앞이라 끝", flush=True); break
            page += 1
    except BudgetOut as e:
        ck["done"], ck["page"] = sorted(done), page
        json.dump(ck, open(CKPT + ".tmp", "w"), ensure_ascii=False); os.replace(CKPT + ".tmp", CKPT)
        print(f"\n■ {e} — 여기서 멈춘다. 다음 실행에서 이어 받는다.", flush=True)
    f.close()
    print(f"\n완료 — 요청 {_used[0]}회, 계약 {kept}건 → {OUT}", flush=True)

if __name__ == "__main__":
    main()
