# 홈페이지의 학교 12,543곳 모두에 좌표를 붙인다 — 지도에 쓰려고.
# 사용: python3 make_coords.py            (주소 변환 없이, 원천 자료로 맞출 수 있는 만큼)
#       python3 make_coords.py --geocode  (남은 곳을 OSM Nominatim 주소 변환으로 채운다 — 1초에 한 번)
#
# 원천 (geo/ 의 *_src.* 는 받은 그대로 두는 원본이다 — 읽기만 한다)
#   school_locations_official_20260320_src.zip  한국교육시설안전원 초중등학교 위치(2026.3.20.) 12,011곳
#   osm_schools_20260911_src.json               OpenStreetMap amenity=school (Overpass, 2026.9.11.)
#   geocode_cache.json                          주소 변환 결과를 쌓아 둔다(같은 주소를 두 번 묻지 않게)
# 결과
#   geo/school_coords.json         학교 열쇠(학교코드, 없으면 local-…) → [위도, 경도, 등급, 방법]
#   geo/school_coords_review.csv   확인이 필요한 곳(등급 C 이하·못 찾은 곳)
#
# 등급
#   A  공식 자료와 시도·이름·학교급·도로명·건물번호가 다 맞음
#   B  공식 자료와 시도·이름·학교급이 맞음(주소는 다름 — 이전·표기 차이)
#   R  공식 자료와 도로명·건물번호·학교급이 맞음(이름만 다름 — 3월 이후 개명)
#   S  색인의 다른 학교와 주소가 똑같음(같은 캠퍼스) — 그 학교 좌표를 쓴다
#   H  '○○고등학교부설방송통신고등학교'처럼 본교에 딸림 — 본교 좌표를 쓴다
#   O  OSM에 같은 이름의 학교가 전국에 하나뿐
#   G  주소 변환(OSM Nominatim)
#   X  못 찾음
import argparse, csv, hashlib, io, json, math, subprocess, os, re, sys, time, urllib.parse, urllib.request, zipfile, collections

GEO = "geo"
EXCLUDE = ("재외한국학교", "외국인학교", "국제학교", "공동실습소")   # build_data.py INDEX_EXCLUDE와 같다
SIDO = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주",
        "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기", "강원특별자치도": "강원",
        "강원도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북",
        "전라남도": "전남", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주"}


def sido(x):
    x = (x or "").replace("교육청", "").replace("전남광주통합특별시(광주)", "광주광역시").replace("전남광주통합특별시(전남)", "전라남도")
    for a, b in SIDO.items():
        if x.startswith(a):
            return b
    return x[:2]


def norm(s):
    return re.sub(r"[\s·・ㆍ()（）\[\]\-]", "", s or "")


def road(a):
    """도로명주소에서 (도로명, 건물번호)만 — 표기가 조금 달라도 같은 건물이면 같다"""
    a = re.split(r"[,（(]", a or "")[0].strip()
    a = re.sub(r"(로|길)\s+(\d+(?:번)?길)", r"\1\2", a)
    m = re.search(r"([^\s]+(?:로|길))\s*(\d+(?:-\d+)?)\s*$", a)
    return (m.group(1), m.group(2)) if m else None


def full_addr(a):
    return norm(re.split(r"[,（(]", a or "")[0])


def key_of(s):
    c = (s.get("code") or "").strip()
    return c or "local-" + hashlib.sha1(f"{s['sido']}|{s['name']}|{s['address']}".encode()).hexdigest()[:12]


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geocode", action="store_true")
    a = ap.parse_args()

    M = [s for s in json.load(open("school_master.json", encoding="utf-8"))["schools"]
         if s["level"] and not any(e in s["level"] for e in EXCLUDE)]

    # 명단에 주소가 없는 학교는 사람이 찾아 적어 둔 주소를 쓴다(geo/위치미확인_학교.csv의 명단주소 칸).
    # 부산 학력인정 계열 네 곳처럼 NEIS 명단에 주소가 통째로 비어 있는 곳이 있다(2026-09-12).
    _fix = "geo/위치미확인_학교.csv"
    if os.path.exists(_fix):
        _add = {}
        for r in csv.DictReader(open(_fix, encoding="utf-8-sig")):
            k, a = (r.get("학교코드") or "").strip(), (r.get("명단주소") or "").strip()
            if k and a:
                _add[k] = a
        _n = 0
        for s in M:
            if not (s.get("address") or "").strip() and key_of(s) in _add:
                s["address"] = _add[key_of(s)]
                _n += 1
        if _n:
            print(f"  손으로 찾은 주소로 채운 학교 {_n}곳")
    assert len(M) == 12543, f"색인이 12,543곳이 아니다: {len(M)}"

    z = zipfile.ZipFile(os.path.join(GEO, "school_locations_official_20260320_src.zip"))
    O = list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8-sig"))))
    off = collections.defaultdict(list)
    for r in O:
        off[(sido(r["시도교육청명"]), norm(r["학교명"]), r["학교급구분"])].append(r)

    osm = collections.defaultdict(list)
    for e in json.load(open(os.path.join(GEO, "osm_schools_20260911_src.json"), encoding="utf-8"))["elements"]:
        t = e.get("tags", {}); c = e.get("center") or e
        if "lat" not in c:
            continue
        for nm in {t.get("name"), t.get("name:ko")} - {None}:
            osm[norm(nm)].append((float(c["lat"]), float(c["lon"])))

    out, why = {}, {}
    # 1) 공식 자료
    for s in M:
        k = key_of(s)
        cands = off.get((sido(s["sido"]), norm(s["name"]), s["level"]), [])
        rk = road(s["address"])
        hit = [r for r in cands if rk and road(r["소재지도로명주소"]) == rk]
        if hit:
            r = hit[0]; out[k] = [float(r["위도"]), float(r["경도"]), "A", "공식·주소일치"]
        elif len(cands) == 1:
            r = cands[0]; out[k] = [float(r["위도"]), float(r["경도"]), "B", "공식·이름일치(주소 다름)"]
    # 1-2) 개명 — 공식 자료(3월 기준)에 옛 이름으로 남은 학교. 도로명·건물번호·학교급이 같고
    #      그 공식 학교가 이름으로 이미 다른 학교에 쓰이지 않았을 때만.
    #      (서울디지털콘텐츠고=옛 강서공업고, 서울반도체고=옛 휘경공업고, 한양과학기술고=옛 한양공업고)
    used = {(sido(s["sido"]), norm(s["name"]), s["level"]) for s in M}
    by_road = collections.defaultdict(list)
    for r in O:
        rk = road(r["소재지도로명주소"])
        if rk:
            by_road[(sido(r["시도교육청명"]), rk, r["학교급구분"])].append(r)
    for s in M:
        k = key_of(s)
        if k in out or not road(s["address"]):
            continue
        cands = [r for r in by_road.get((sido(s["sido"]), road(s["address"]), s["level"]), [])
                 if (sido(r["시도교육청명"]), norm(r["학교명"]), r["학교급구분"]) not in used]
        if len(cands) == 1:
            r = cands[0]; out[k] = [float(r["위도"]), float(r["경도"]), "R", f"공식·같은주소(옛 이름 {r['학교명']})"]
    # 2) 같은 주소의 다른 학교 (같은 캠퍼스)
    by_addr = collections.defaultdict(list)
    for s in M:
        by_addr[(sido(s["sido"]), full_addr(s["address"]))].append(s)
    for s in M:
        k = key_of(s)
        if k in out or not full_addr(s["address"]):
            continue
        mates = [key_of(x) for x in by_addr[(sido(s["sido"]), full_addr(s["address"]))] if key_of(x) in out and out[key_of(x)][2] in "ABR"]
        if mates:
            p = out[mates[0]]; out[k] = [p[0], p[1], "S", "같은주소 학교 좌표"]
    # 3) 본교에 딸린 학교 (부설·병설)
    by_name = {(sido(s["sido"]), norm(s["name"])): s for s in M}
    for s in M:
        k = key_of(s)
        if k in out:
            continue
        m = re.match(r"(.+?(?:고등학교|중학교|초등학교|학교))(?:부설|병설)", s["name"])
        host = by_name.get((sido(s["sido"]), norm(m.group(1)))) if m else None
        if host and key_of(host) in out:
            p = out[key_of(host)]; out[k] = [p[0], p[1], "H", f"본교({host['name']}) 좌표"]
    # 4) OSM에 같은 이름이 전국에 하나뿐
    for s in M:
        k = key_of(s)
        if k in out:
            continue
        pts = osm.get(norm(s["name"]), [])
        if len(pts) == 1:
            out[k] = [pts[0][0], pts[0][1], "O", "OSM 같은이름(유일)"]

    # 4-2) 시도 밖 검사 — 공식 자료로 시도마다 좌표 상자(여유 0.05도)를 잡는다. 벗어난 좌표는
    #      다른 지역의 같은 이름 학교를 잡은 것이니 걷어내고 주소로 다시 찾게 한다.
    box = {}
    for r in O:
        sd, la, lo = sido(r["시도교육청명"]), float(r["위도"]), float(r["경도"])
        b = box.setdefault(sd, [la, la, lo, lo])
        b[0], b[1], b[2], b[3] = min(b[0], la), max(b[1], la), min(b[2], lo), max(b[3], lo)
    def inside(sd, p):
        b = box.get(sd)
        return not b or (b[0] - .05 <= p[0] <= b[1] + .05 and b[2] - .05 <= p[1] <= b[3] + .05)
    outside = [s for s in M if key_of(s) in out and not inside(sido(s["sido"]), out[key_of(s)])]
    for s in outside:
        print(f"  시도 밖이라 걷어냄: {s['name']}({sido(s['sido'])}) {out[key_of(s)][2]} {out[key_of(s)][3]}")
        del out[key_of(s)]
    # 4-3) OSM 이름 변형 — 공식 자료에 없는 특수·각종학교·분교장은 OSM에 지역 이름을 뗀 채로
    #      올라 있는 일이 많다(울산고운고등학교 → 고운고등학교, 인천주안남초등학교승봉분교장 →
    #      주안남초등학교 승봉분교장, …분교장 → …분교). 같은 시도 상자 안에 딱 하나일 때만 쓴다.
    def vkey(n):
        return norm(n).replace("분교장", "분교")
    osm_v = collections.defaultdict(list)
    for nm, pts in osm.items():
        osm_v[vkey(nm)].extend(pts)
    for s in M:
        k = key_of(s)
        if k in out:
            continue
        sd = sido(s["sido"])
        stems = {sd} | {m[:-1] for m in re.findall(r"(\S+?[시군구])(?=\s)", s["address"] or "") if len(m) >= 3}
        names = {vkey(s["name"])} | {vkey(s["name"][len(t):]) for t in stems if s["name"].startswith(t) and len(s["name"]) - len(t) >= 4}
        pts = {p for n in names for p in osm_v.get(n, []) if inside(sd, p)}
        if len(pts) == 1:
            p = pts.pop(); out[k] = [p[0], p[1], "O", "OSM 이름 변형(지역명·분교장 표기 차이)"]
    # 5) 주소 변환 — 남은 곳만, 1초에 한 번
    cache_path = os.path.join(GEO, "geocode_cache.json")
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    # 남은 곳과 함께 B·O도 주소로 한 번 더 찍어 본다 — O는 같은 도 안의 다른 학교일 수 있고
    # (시도 밖 검사가 다른 도의 같은 이름 학교 넷을 잡았다), B는 학교가 이사했을 수 있다.
    left = [s for s in M if key_of(s) not in out or out[key_of(s)][2] in "BO"]
    if a.geocode:
        done = [0]
        def nom(q):
            """Nominatim 한 번(캐시). curl로 부른다 — 파이썬 3.9 기본 ssl은 이 서버와 악수하다
            timeout을 무시하고 몇 분씩 멈췄다(2026-09-11). curl은 -m으로 끝을 확실히 자른다."""
            if q not in cache:
                url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": q, "format": "json", "limit": 1, "countrycodes": "kr"})
                try:
                    res = subprocess.run(["curl", "-s", "-f", "-m", "20", "-A", "school-edtech.kr school map (research)", url],
                                         capture_output=True, timeout=30)
                    if res.returncode:
                        raise RuntimeError(f"curl {res.returncode}")
                    r = json.loads(res.stdout)
                    cache[q] = [float(r[0]["lat"]), float(r[0]["lon"]), r[0].get("display_name", "")[:80]] if r else None
                except Exception as e:
                    print(f"  주소 변환 실패({type(e).__name__}): {q}", flush=True)
                    return None
                time.sleep(1.1)
                done[0] += 1
                if done[0] % 25 == 0:
                    json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
                    print(f"  새로 물은 것 {done[0]}건", flush=True)
            return cache.get(q)
        pcache_path = os.path.join(GEO, "photon_cache.json")
        pcache = json.load(open(pcache_path, encoding="utf-8")) if os.path.exists(pcache_path) else {}
        def photon(q):
            if q not in pcache:
                url = "https://photon.komoot.io/api/?" + urllib.parse.urlencode({"q": q, "limit": 1})
                try:
                    res = subprocess.run(["curl", "-s", "-f", "-m", "20", "-A", "school-edtech.kr school map (research)", url],
                                         capture_output=True, timeout=30)
                    f = json.loads(res.stdout)["features"] if not res.returncode else None
                except Exception:
                    f = None
                if f is None:
                    return None
                pr = f[0]["properties"] if f else {}
                pcache[q] = ([f[0]["geometry"]["coordinates"][1], f[0]["geometry"]["coordinates"][0], pr.get("name") or "",
                              pr.get("street") or "", pr.get("housenumber") or ""] if f and pr.get("type") == "house" else None)
                time.sleep(1.1)
                json.dump(pcache, open(pcache_path, "w", encoding="utf-8"), ensure_ascii=False)
            return pcache.get(q)
        p2_path = os.path.join(GEO, "photon_cache2.json")
        p2 = json.load(open(p2_path, encoding="utf-8")) if os.path.exists(p2_path) else {}
        def photon_all(q):
            """Photon 후보 다섯까지 [위도, 경도, 종류, 이름, 도로, 번호, 시군구] — 판단은 부르는 쪽이 한다"""
            if q not in p2:
                url = "https://photon.komoot.io/api/?" + urllib.parse.urlencode({"q": q, "limit": 5})
                try:
                    res = subprocess.run(["curl", "-s", "-f", "-m", "20", "-A", "school-edtech.kr school map (research)", url],
                                         capture_output=True, timeout=30)
                    feats = json.loads(res.stdout)["features"] if not res.returncode else None
                except Exception:
                    feats = None
                if feats is None:
                    return []
                p2[q] = [[f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0], f["properties"].get("type"),
                          f["properties"].get("name") or "", f["properties"].get("street") or "", f["properties"].get("housenumber") or "",
                          " ".join(filter(None, (f["properties"].get(x) for x in ("city", "county", "district", "locality"))))]
                         for f in feats]
                time.sleep(1.1)
                json.dump(p2, open(p2_path, "w", encoding="utf-8"), ensure_ascii=False)
            return p2[q]
        for s in left:
            k, sd = key_of(s), sido(s["sido"])
            # "(본교) 서울특별시 …"처럼 괄호로 시작하는 주소가 있다 — 앞 괄호를 떼야 빈 검색어가 안 된다
            q = re.split(r"[,（(]", re.sub(r"^\s*[（(][^)）]*[)）]\s*", "", s["address"] or ""))[0].strip()
            g, tier, how = (nom(q) if q else None), "G", "주소변환(Nominatim)"
            if g and not inside(sd, g):
                g = None
            if not g and k not in out and road(q):
                # Photon(OSM의 다른 검색기) — 느슨하게 찾아 딴 길을 내놓기도 한다
                # (수영로123번길 54 → 수영로219번길 54). 도로명·건물번호가 똑같을 때만 받는다.
                rd, no = road(q)
                gp = photon(q)
                if gp and norm(gp[3]) == norm(rd) and gp[4] == no and inside(sd, gp):
                    g, how = gp, "주소변환(Photon, 도로명·번호 일치)"
            if not g and k not in out:
                # 주소 표기를 못 읽는 곳이 많다(부산의 '○○번길 9-55' 꼴 등) — 학교 이름으로 한 번 더
                g2 = nom(f"{s['name']} {s['sido']}")
                if g2 and inside(sd, g2):
                    g, how = g2, "학교이름 검색(Nominatim)"
                elif q:
                    # 마지막으로 건물번호를 떼고 도로만 — 수백 m~몇 km 어긋날 수 있어 등급을 따로 둔다
                    rq = re.sub(r"\s*\d+(?:-\d+)?\s*(?:번지|호)?\s*$", "", q)
                    g3 = nom(rq) if rq and rq != q else None
                    if g3 and inside(sd, g3):
                        g, tier, how = g3, "D", "도로 수준(근사) — 건물번호를 못 찾아 도로 위치"
            if not g and k not in out and road(q):
                # 마지막 — 건물도 이름도 못 찾으면 도로 위치(Photon). 같은 이름의 길이 다른 시군구에도
                # 있으니(중앙로 등) 시군구가 맞고 도로명이 똑같을 때만 받는다. 등급 D(근사)로 둔다.
                rd = road(q)[0]
                sgg = re.findall(r"(\S+?[시군구])(?=\s)", q)[:2]
                for c in photon_all(" ".join(sgg + [rd])) if sgg else []:
                    if c[2] == "street" and norm(c[3]) == norm(rd) and inside(sd, c) and any(t[:-1] in c[6] for t in sgg):
                        g, tier, how = c, "D", "도로 수준(근사, Photon) — 건물을 못 찾아 도로 위치"
                        break
            if not g:
                continue
            if k not in out:
                out[k] = [g[0], g[1], tier, how]
            else:
                d = km(out[k], g)
                if out[k][2] == "O" and d > 3:
                    out[k] = [g[0], g[1], "G", f"주소변환 — OSM 같은이름은 {d:.1f}km 떨어져 버림"]
                elif out[k][2] == "B" and d > 3:
                    out[k][3] += f" · 주소변환과 {d:.1f}km 어긋남(이전 여부 확인)"
                else:
                    out[k][3] += f" · 주소변환과 {d:.1f}km"
        json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)

    # 5-2) 손으로 채운 좌표 — 자동으로 못 찾은 곳은 사람이 적어 넣는다.
    #      geo/위치미확인_학교.csv(또는 geo/manual_coords.csv)의 위도·경도 칸을 채우면 그대로 쓴다.
    #      사람이 확인한 값이므로 시도 상자 검사나 주소 변환보다 앞선다.
    for mp in ("geo/위치미확인_학교.csv", "geo/manual_coords.csv"):
        if not os.path.exists(mp):
            continue
        n_man = 0
        for r in csv.DictReader(open(mp, encoding="utf-8-sig")):
            k, la, lo = (r.get("학교코드") or "").strip(), (r.get("위도") or "").strip(), (r.get("경도") or "").strip()
            if not (k and la and lo):
                continue
            try:
                out[k] = [float(la), float(lo), "M", f"손으로 넣음({os.path.basename(mp)})"]
                n_man += 1
            except ValueError:
                print(f"  좌표를 읽지 못했다: {r.get('학교명')} {la},{lo}")
        if n_man:
            print(f"  손으로 넣은 좌표 {n_man}곳 ({mp})")

    # 6) 검산 — A·B는 OSM 같은 이름이 1km 안에 있으면 한 번 더 확인된 것으로 센다
    osm_ok = sum(1 for s in M if key_of(s) in out and out[key_of(s)][2] in "AB"
                 and any(km(out[key_of(s)], p) <= 1.0 for p in osm.get(norm(s["name"]), [])))
    json.dump(out, open(os.path.join(GEO, "school_coords.json"), "w", encoding="utf-8"), ensure_ascii=False)
    with open(os.path.join(GEO, "school_coords_review.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["학교열쇠", "학교명", "학교급", "시도", "주소", "등급", "방법", "위도", "경도"])
        for s in M:
            k = key_of(s); p = out.get(k)
            if not p or p[2] not in "ARSM":
                w.writerow([k, s["name"], s["level"], sido(s["sido"]), s["address"], p[2] if p else "X", p[3] if p else "못 찾음", p[0] if p else "", p[1] if p else ""])
    g = collections.Counter(p[2] for p in out.values())
    print(f"학교 {len(M):,}곳 · 좌표 {len(out):,}곳 · 못 찾음 {len(M) - len(out):,}곳")
    print("등급:", " · ".join(f"{k} {g[k]:,}" for k in "ABRSHOGDM" if g[k]))
    print(f"검산: A·B 중 OSM 같은 이름이 1km 안에 있는 곳 {osm_ok:,}곳")


if __name__ == "__main__":
    main()
