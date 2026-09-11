#!/bin/zsh
# 아직 넓힌 검색어(4,493종)로 다 받지 못한 곳들을 서버별로 동시에 받는다.
#
# 예전에는 한 줄로 세워 하나씩 받았다. 그런데 이 일곱은 서로 다른 교육청 서버라
# 동시에 받아도 서버마다 걸리는 부담은 그대로다. 한 줄로 세울 이유가 없었다.
# (같은 서버를 둘이 두드리는 것만 막으면 된다 — collect_lock.sh의 서버별 자물쇠가 그 몫이다)
#
# 간격 10초·하루 5,000회 상한은 그대로다. 상한에 걸리면 체크포인트를 남기고 곱게 끝나
# 다음 실행에서 이어 받는다.
cd "$(dirname "$0")"
. ./collect_lock.sh
set -a; . ~/.edtech_env 2>/dev/null; set +a
export EDTECH_SPACING=10 EDTECH_MAXREQ=5000
KF=edzip_brand_keywords.txt
Y=2020,2021,2022,2023,2024,2025,2026

echo "══ 지역 수집 시작 $(date '+%Y-%m-%d %H:%M') — 서버별 동시"

# 대전은 2026-09-11 하루에 여러 번 두드린 뒤로 새 세션까지 곧바로 409로 거부한다 — 전남이 막혔을
# 때와 같은 모양이다. 9월 13일까지는 건드리지 않고, 그 뒤로도 30초 간격·하루 300회로만 받는다.
if [ "$(date +%Y%m%d)" -ge 20260913 ]; then
  ( export EDTECH_SPACING=30 EDTECH_MAXREQ=300; par_run 대전 region_대전 python3 collect_dje.py --office 대전 --years $Y --keyword-file $KF ) &
else
  echo "▷ 대전 — 9월 13일까지 쉰다(거부 응답이 이어져 차단 위험)"
fi
par_run 충남 region_충남 python3 collect_dje.py --office 충남 --years $Y --keyword-file $KF &
par_run 경남 region_경남 python3 collect_gne.py --years $Y --keyword-file $KF &
par_run 강원 region_강원 python3 collect_gwe.py --keyword-file $KF --refresh &
par_run 광주 region_광주 python3 collect_gen.py --years $Y --keyword-file $KF &
par_run 울산 region_울산 python3 collect_use.py --keyword-file $KF &
par_run 대구 region_대구 python3 collect_dge.py --keyword-file $KF &

wait
echo "══ 이번 몫 끝 $(date '+%Y-%m-%d %H:%M')"
