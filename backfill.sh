#!/bin/bash
# 나라장터 소급 수집 배치 — 2023.1 ~ 2026.6을 3개월 창으로 순차 수집·정제
# 사용: NARA_KEY=<키> nohup caffeinate -is bash backfill.sh > backfill.log 2>&1 &
# 22시 이전에 시작하면 22시까지 대기 후 실행 (야간 배치)
set -u
cd "$(dirname "$0")"

if [ -z "${NARA_KEY:-}" ]; then echo "NARA_KEY 필요"; exit 1; fi

H=$(date +%H)
if [ "$H" -ge 6 ] && [ "$H" -lt 22 ]; then
  echo "$(date '+%F %T') 야간 시작 대기 (22:00까지)"
  while [ "$(date +%H)" -ge 6 ] && [ "$(date +%H)" -lt 22 ]; do sleep 60; done
fi

WINDOWS=(
  "20230101 20230331" "20230401 20230630" "20230701 20230930" "20231001 20231231"
  "20240101 20240331" "20240401 20240630" "20240701 20240930" "20241001 20241231"
  "20250101 20250331" "20250401 20250630" "20250701 20250930" "20251001 20251231"
  "20260101 20260331" "20260401 20260619"
)

for w in "${WINDOWS[@]}"; do
  set -- $w
  B=$1; E=$2
  if [ -f "refined_${B}_${E}.csv" ]; then
    echo "$(date '+%F %T') [skip] ${B}~${E} 이미 완료"
    continue
  fi
  echo "$(date '+%F %T') [수집] ${B} ~ ${E}"
  python3 collect_nara.py --begin "$B" --end "$E"
  if [ $? -ne 0 ]; then
    echo "$(date '+%F %T') [오류] ${B}~${E} 수집 실패 — 5분 후 재시도"
    sleep 300
    python3 collect_nara.py --begin "$B" --end "$E" || { echo "[중단] ${B}~${E} 2회 실패"; continue; }
  fi
  python3 refine_candidates.py "candidates_${B}_${E}.csv"
  sleep 30
done

echo "$(date '+%F %T') 전체 창 완료 — data.js 빌드"
python3 build_data.py
echo "$(date '+%F %T') 배치 종료 (push는 검토 후 수동)"
