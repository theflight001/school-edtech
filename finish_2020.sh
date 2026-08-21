#!/bin/zsh
# 수집이 끝난 뒤: 서울 상세 채우기 → 정제 → 빌드 까지 한 번에.
cd "$(dirname "$0")"
set -a; . ~/.edtech_env 2>/dev/null; set +a
step() { echo "▶ $* ($(date +%H:%M))"; python3 "$@" || echo "!! 실패: $*"; }
# 두 수집기가 끝날 때까지 기다린다
while pgrep -f "collect_sen_edufine.py|collect_nara_office.py" > /dev/null; do sleep 120; done
echo "== 수집 끝 ($(date +%H:%M)) =="
step fill_sen_edufine.py            # 에듀테크로 잡힌 것만 계약일·계약상대자 채우기
step refine_office.py 서울에듀파인   # 학교 매칭 + 에듀테크 판정
step refine_office_buy.py           # 교육청 일괄 도입
step build_data.py
echo "== 끝 ($(date +%H:%M)) =="
