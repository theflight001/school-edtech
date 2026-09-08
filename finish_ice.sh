#!/bin/zsh
# 네 시도 재수집이 끝나면 정제 → 빌드 → 배포까지 이어서 한다.
cd "$(dirname "$0")"
set -a; . ~/.edtech_env 2>/dev/null; set +a
while pgrep -f "check_ice_offices|collect_ice.py" > /dev/null; do sleep 180; done
echo "== 재수집 끝 ($(date +%H:%M)) =="
python3 refine_office.py    || echo "!! 정제 실패"
python3 refine_s2b.py       || echo "!! S2B 정제 실패"
python3 build_data.py       || { echo "!! 빌드 실패"; exit 1; }
node make_summary.js
python3 make_coverage.py
echo "== 끝 ($(date +%H:%M)) =="
