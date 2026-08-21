#!/bin/zsh
# 나라장터가 504를 자주 뱉는다 — 죽으면 다시 띄운다. 체크포인트가 있어 이어서 간다.
cd "$(dirname "$0")"
set -a; . ~/.edtech_env 2>/dev/null; set +a
for i in {1..40}; do
  python3 collect_nara_office.py --begin 20241205 --end 20260819 && break
  echo "-- $i번째 재시작 ($(date +%H:%M))"
  sleep 60
done
echo "== 교육청 수집 끝 ($(date +%H:%M)) =="
