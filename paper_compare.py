# -*- coding: utf-8 -*-
"""논문용 비교표 — 사이트 빌드(data.js + data_old.js)를 스냅샷 CSV와 대조해 자료원별·연도별·시도별 건수와
'제품명 확인' 기록, 시도별 학교당 제품명 확인(표 2)을 적는다. 화면과 같이 중복(dup) 표시 기록은 뺀다.
쓰기: python3 paper_compare.py <이전 스냅샷 CSV> <결과 md>   (현재 빌드가 '후'다)"""
import csv, json, re, sys, collections, pathlib
GENERIC = set(['기기(PC·태블릿·전자칠판 등)', 'SW·플랫폼(제품명 미상)', 'SW·플랫폼', '인프라(교실·설비)', '로봇·교구·키트', '코스웨어(기타)', '코스웨어', 'VR/XR 장비', '드론', '3D 프린팅/CAD', '운영 부대구매(제품 미상)', '운영 부대구매', 'AI 면접시스템'])   # app.js GENERIC_TAGS와 같다 — 화면의 '미확인 제품' 기준
def load_js(f, name):
    src = pathlib.Path(f).read_text(encoding='utf-8')
    m = re.search(r"const %s = JSON\.parse\('([\s\S]*?)'\);" % name, src)
    return json.loads(m.group(1).replace("\\'", "'").replace('\\\\', '\\'))
def current():
    d = load_js('data.js', 'DB_RAW'); o = load_js('data_old.js', 'DB_OLD')
    cols = d['cols']; dic = d.get('dict', {}); tags = d['tagList']; ci = {c: i for i, c in enumerate(cols)}
    out = []
    for blk in (d, o):
        for r in blk['rows']:
            g = lambda k: (dic[k][r[ci[k]]] if k in dic and isinstance(r[ci[k]], int) else r[ci[k]]) if k in ci else None
            if ci.get('dup') is not None and r[ci['dup']]: continue
            ym = r[ci['ym']] or 0
            out.append({'year': str(ym // 100) if ym else '', 'sido': str(g('sido') or ''), 'schoolCode': str(g('schoolCode') or ''),
                        'sourceType': str(g('sourceType') or ''),
                        'tags': '|'.join(tags[i] if isinstance(i, int) else str(i) for i in (r[ci['tags']] or []))})
    return out
def named(r): return any(t and t not in GENERIC for t in r['tags'].split('|'))
def sd(r): return '광주·전남' if r['sido'] in ('광주', '전남') else r['sido']
A = list(csv.DictReader(open(sys.argv[1], encoding='utf-8-sig'))); B = current()
out = []
def table(title, key, keys=None):
    ca = collections.Counter(key(r) for r in A); cb = collections.Counter(key(r) for r in B)
    na = collections.Counter(key(r) for r in A if named(r)); nb = collections.Counter(key(r) for r in B if named(r))
    ks = keys or sorted(set(ca) | set(cb), key=lambda k: -cb[k])
    out.append(f"\n### {title}\n| 구분 | 건수(전) | 건수(후) | 제품명 확인(전) | 제품명 확인(후) |\n|---|---:|---:|---:|---:|")
    for k in ks: out.append(f"| {k} | {ca[k]:,} | {cb[k]:,} | {na[k]:,} | {nb[k]:,} |")
    out.append(f"| 계 | {len(A):,} | {len(B):,} | {sum(na.values()):,} | {sum(nb.values()):,} |")
table('시도별', sd); table('연도별', lambda r: r['year'], [str(y) for y in range(2020, 2027)]); table('자료원별', lambda r: r['sourceType'])
def per(rows):
    sch = collections.defaultdict(set); nm = collections.Counter()
    for r in rows:
        if r['schoolCode']:
            sch[sd(r)].add(r['schoolCode'])
            if named(r): nm[sd(r)] += 1
    return {k: (len(sch[k]), nm[k]) for k in sch}
pa, pb = per(A), per(B)
out.append("\n### 시도별 학교당 제품명 확인 기록(표 2)\n| 시도 | 학교 수(전→후) | 제품 확인(전→후) | 학교당(전→후) |\n|---|---|---|---|")
for k in sorted(set(pa) | set(pb), key=lambda k: -pb.get(k, (0, 0))[1]):
    a, b = pa.get(k, (0, 0)), pb.get(k, (0, 0))
    out.append(f"| {k} | {a[0]:,}→{b[0]:,} | {a[1]:,}→{b[1]:,} | {a[1]/a[0] if a[0] else 0:.1f}→{b[1]/b[0] if b[0] else 0:.1f} |")
pathlib.Path(sys.argv[2]).write_text('\n'.join(out) + '\n', encoding='utf-8'); print('written', sys.argv[2], len(A), len(B))
