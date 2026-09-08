#!/bin/zsh
# 남은 시도를 넓힌 검색어로 훑는다. 전남은 서버가 막혀 맨 뒤로 미룬다.
#
# 전남(jge.go.kr)은 2026-09-04부터 응답이 없다 — 295초를 기다려도 타임아웃이다.
# 이미 32,655건을 받아 뒀고(전 21,206건) 체크포인트가 9,016칸이라 나중에 이어 받을 수 있다.
cd "$(dirname "$0")"
set -a; . ~/.edtech_env 2>/dev/null; set +a
KF=edzip_brand_keywords.txt
Y=2020,2021,2022,2023,2024,2025,2026
step() { echo "▶ $* ($(date '+%m-%d %H:%M'))"; "$@" || echo "  ✗ 실패/시간초과: $*"; }

step python3 collect_ice.py --office 세종 --years $Y --keyword-file $KF
step python3 collect_pen.py --office 부산 --begin 2020-01 --end 2026-09
step python3 collect_pen.py --office 경북 --begin 2020-01 --end 2026-09
step python3 collect_dge.py --begin 2020-01 --end 2026-09 --keyword-file $KF
step python3 collect_dje.py --office 대전 --years $Y --keyword-file $KF
step python3 collect_dje.py --office 충남 --years $Y --keyword-file $KF
step python3 collect_gne.py --years $Y --keyword-file $KF
step python3 collect_gwe.py --keyword-file $KF --refresh
step python3 collect_gen.py --years $Y --keyword-file $KF
step python3 collect_use.py --keyword-file $KF
echo "== 열 시도 끝 ($(date '+%m-%d %H:%M')) =="

# 전남을 마지막에 한 번 더 — 그 사이 서버가 풀렸을 수 있다
step python3 collect_ice.py --office 전남 --years $Y --keyword-file $KF
echo "== 전남까지 끝 ($(date '+%m-%d %H:%M')) =="
