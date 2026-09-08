#!/bin/zsh
# 연 단위로 훑는 시도를 먼저 끝낸다. 대구·전남은 맨 뒤로 미룬다.
#   대구: 검색어 × 월(80개월) = 359,440회 조회라 4분에 2개씩 나간다 — 한 달이 넘는다.
#   전남: 서버가 2026-09-04부터 응답하지 않는다.
# 둘 다 체크포인트가 있어 나중에 이어 받는다.
cd "$(dirname "$0")"
set -a; . ~/.edtech_env 2>/dev/null; set +a
KF=edzip_brand_keywords.txt
Y=2020,2021,2022,2023,2024,2025,2026
step() { echo "▶ $* ($(date '+%m-%d %H:%M'))"; "$@" || echo "  ✗ 실패: $*"; }

step python3 collect_dje.py --office 대전 --years $Y --keyword-file $KF
step python3 collect_dje.py --office 충남 --years $Y --keyword-file $KF
step python3 collect_gne.py --years $Y --keyword-file $KF
step python3 collect_gwe.py --keyword-file $KF --refresh
step python3 collect_gen.py --years $Y --keyword-file $KF
step python3 collect_use.py --keyword-file $KF
echo "== 여섯 시도 끝 ($(date '+%m-%d %H:%M')) =="

# 서버가 풀렸을 수 있으니 전남을 한 번 더
step python3 collect_ice.py --office 전남 --years $Y --keyword-file $KF
echo "== 전부 끝 ($(date '+%m-%d %H:%M')) =="
