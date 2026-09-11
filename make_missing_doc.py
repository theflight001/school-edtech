# 좌표를 못 찾은 학교를 사람이 채워 넣을 수 있게 표로 만든다.
#   python3 make_missing_doc.py
#   → geo/위치미확인_학교.csv  (없을 때만 새로 만든다 — 이미 채운 좌표를 지우지 않는다)
#   → geo/위치미확인_학교.docx (늘 다시 만든다)
# make_coords.py가 CSV의 위도·경도 칸을 읽어 그대로 쓴다(등급 M, 자동 추정보다 앞선다).
#
# 왜 직접 만드는가: 이 컴퓨터엔 pandoc·리브레오피스가 없고, macOS textutil은 표를 버리고
# 칸마다 한 줄씩 풀어 놓는다(2026-09-12 확인).
import os

if not os.path.exists("geo/위치미확인_학교.csv"):
    import csv as _csv
    rows = [r for r in _csv.DictReader(open("geo/school_coords_review.csv", encoding="utf-8-sig")) if r["등급"] == "X"]
    with open("geo/위치미확인_학교.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["학교코드", "학교명", "학교급", "시도", "명단주소", "위도", "경도", "메모"])
        for r in sorted(rows, key=lambda r: (r["시도"], r["학교명"])):
            w.writerow([r["학교열쇠"], r["학교명"], r["학교급"], r["시도"], r["주소"], "", "", ""])
    print(f"geo/위치미확인_학교.csv 새로 만듦 — {len(rows)}곳")

import csv, collections, zipfile, html

ROWS = list(csv.DictReader(open("geo/위치미확인_학교.csv", encoding="utf-8-sig")))
by = collections.defaultdict(list)
for r in ROWS:
    by[r["시도"]].append(r)
order = sorted(by, key=lambda k: (-len(by[k]), k))
E = lambda x: html.escape(x or "", quote=False)

def para(text, size=22, bold=False, after=120, color=None):
    rpr = f'<w:rPr>{"<w:b/>" if bold else ""}<w:sz w:val="{size}"/>' \
          f'{f"<w:color w:val={chr(34)}{color}{chr(34)}/>" if color else ""}</w:rPr>'
    return (f'<w:p><w:pPr><w:spacing w:after="{after}"/></w:pPr>'
            f'<w:r>{rpr}<w:t xml:space="preserve">{E(text)}</w:t></w:r></w:p>')

def cell(text, w, bold=False, shade=None):
    sh = f'<w:shd w:val="clear" w:fill="{shade}"/>' if shade else ""
    return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{sh}</w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>'
            f'<w:r><w:rPr>{"<w:b/>" if bold else ""}<w:sz w:val="18"/></w:rPr>'
            f'<w:t xml:space="preserve">{E(text)}</w:t></w:r></w:p></w:tc>')

WID = [2400, 1500, 3300, 1200, 900, 900]
HEAD = ["학교명", "학교급", "명단 주소", "학교코드", "위도", "경도"]
body = [para("위치를 찾지 못한 학교 54곳", 32, True, 200),
        para("전국 학교 12,543곳 가운데 지도에 올릴 좌표를 찾지 못한 곳입니다(2026년 9월 12일 기준). "
             "공식 학교위치 자료(한국교육시설안전원)가 초·중·고만 담고 있어 특수학교·각종학교·평생학교·분교장은 "
             "OpenStreetMap과 주소 검색으로 찾아야 하는데, 그마저 실패한 곳입니다."),
        para("노란 칸(위도·경도)을 채워 주시면 다음 빌드부터 그 값을 그대로 씁니다. 자동 추정보다 우선합니다. "
             "학교코드는 좌표를 붙일 때 쓰는 열쇠이니 그대로 두세요."),
        para("지도에서 위치를 찾아 마우스 오른쪽 단추로 좌표를 복사하면 '37.5665, 126.9780' 꼴로 나옵니다 — "
             "앞이 위도, 뒤가 경도입니다. 주소가 비어 있는 9곳은 학교 명단에 주소 자체가 없습니다.", 20, False, 240)]
for sd in order:
    body.append(para(f"{sd} · {len(by[sd])}곳", 26, True, 80))
    rows = ['<w:tr><w:trPr><w:tblHeader/></w:trPr>'
            + "".join(cell(h, w, True, "EEF2F6") for h, w in zip(HEAD, WID)) + '</w:tr>']
    for r in sorted(by[sd], key=lambda r: r["학교명"]):
        vals = [r["학교명"], r["학교급"], r["명단주소"] or "(주소 없음)", r["학교코드"], "", ""]
        rows.append("<w:tr>" + "".join(
            cell(v, w, False, "FFFBE6" if i >= 4 else None) for i, (v, w) in enumerate(zip(vals, WID))) + "</w:tr>")
    body.append('<w:tbl><w:tblPr><w:tblW w:w="10200" w:type="dxa"/>'
                '<w:tblBorders>' + "".join(
                    f'<w:{s} w:val="single" w:sz="4" w:color="999999"/>'
                    for s in ("top", "left", "bottom", "right", "insideH", "insideV")) +
                '</w:tblBorders></w:tblPr>' + "".join(rows) + '</w:tbl>' + para("", 18, False, 160))

doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
       f'<w:body>{"".join(body)}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
       '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>')
CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
      '</Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>')
with zipfile.ZipFile("geo/위치미확인_학교.docx", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", CT)
    z.writestr("_rels/.rels", RELS)
    z.writestr("word/document.xml", doc)
print(f"geo/위치미확인_학교.docx — 시도 {len(order)}개 · {len(ROWS)}곳")
