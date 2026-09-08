#!/bin/zsh
# 검색어에 좌우되는 14개 시도를 넓힌 검색어(4,493종)로 다시 훑는다.
# 그다음 원천과 대조해 모자란 곳이 없는지 확인하고, 정제·빌드까지 간다.
#
# 왜 다시 훑나: 검색어가 19종뿐이었다. 인천 한 곳에서만 13,000건이 더 나왔다.
# 서울·제주·S2B·나라장터는 계약을 통째로 받으므로 여기 없다(전체의 65%).
cd "$(dirname "$0")"
set -a; . ~/.edtech_env 2>/dev/null; set +a
KF=edzip_brand_keywords.txt
Y=2020,2021,2022,2023,2024,2025,2026
step() { echo "▶ $* ($(date '+%m-%d %H:%M'))"; "$@" || echo "  ✗ 실패: $*"; }

# 지금 돌고 있는 것이 끝나기를 기다린다
while pgrep -f "check_ice_offices|collect_ice.py" > /dev/null; do sleep 180; done
echo "== 인천·충북·전남·세종 끝 ($(date '+%m-%d %H:%M')) =="

step python3 collect_pen.py --office 부산 --begin 2020-01 --end 2026-08
step python3 collect_pen.py --office 경북 --begin 2020-01 --end 2026-08
step python3 collect_dge.py --begin 2020-01 --end 2026-08 --keyword-file $KF
step python3 collect_dje.py --office 대전 --years $Y --keyword-file $KF
step python3 collect_dje.py --office 충남 --years $Y --keyword-file $KF
step python3 collect_gne.py --years $Y --keyword-file $KF
step python3 collect_gwe.py --keyword-file $KF --refresh
step python3 collect_gen.py --years $Y --keyword-file $KF
step python3 collect_use.py --keyword-file $KF
echo "== 아홉 시도 끝 ($(date '+%m-%d %H:%M')) =="

# 원천과 대조 — 모자라면 남긴다(빌드는 그대로 진행하되 사람이 보게 한다)
python3 verify_collect.py > verify.txt 2>&1; echo "대조 결과 → verify.txt"
tail -5 verify.txt

step python3 refine_office.py
step python3 refine_s2b.py
step python3 build_data.py
node make_summary.js
python3 make_coverage.py
echo "== 전부 끝 ($(date '+%m-%d %H:%M')) =="
