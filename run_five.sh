#!/bin/zsh
# 아직 넓힌 검색어(4,493종)로 받지 못한 여섯 곳 — 대전·충남·경남·강원·광주·울산.
# 전남이 우리 IP를 막은 뒤로 예의 있게 받는다: 10초 간격, 한 실행에 5,000회에서 멈춤.
# 상한에 걸리면 체크포인트를 남기고 곱게 끝나므로, 다음 실행에서 이어 받는다.
cd "$(dirname "$0")"
. ./collect_lock.sh
# 월 갱신이 돌고 있으면 오늘은 물러선다 — 같은 체크포인트를 둘이 만지면 받은 것을 잃는다.
if ! lock_acquire "five" 0; then
  echo "다른 수집이 도는 중이라 오늘은 건너뛴다: $(cat .collect.lock/owner 2>/dev/null)"
  exit 0
fi
set -a; . ~/.edtech_env 2>/dev/null; set +a
# 간격 10초는 그대로 둔다(초당 0.1회 — 막혔을 때의 10분의 1). 하루에 도는 양만 늘린다.
# 5,000회면 14시간쯤 걸려 사실상 밤새 한 곳을 도는 셈이다.
export EDTECH_SPACING=10 EDTECH_MAXREQ=5000
KF=edzip_brand_keywords.txt
Y=2020,2021,2022,2023,2024,2025,2026
step() { echo "▶ $* ($(date '+%m-%d %H:%M'))"; "$@" || echo "  ✗ 실패: $*"; }

step python3 collect_dje.py --office 대전 --years $Y --keyword-file $KF
step python3 collect_dje.py --office 충남 --years $Y --keyword-file $KF
step python3 collect_gne.py --years $Y --keyword-file $KF
step python3 collect_gwe.py --keyword-file $KF --refresh
step python3 collect_gen.py --years $Y --keyword-file $KF
step python3 collect_use.py --keyword-file $KF
echo "== 이번 몫 끝 ($(date '+%m-%d %H:%M')) =="
