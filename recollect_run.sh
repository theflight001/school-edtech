#!/bin/zsh
# 며칠짜리 재수집 실행기 — 하루 상한(EDTECH_MAXREQ)에 닿으면 다음 날 같은 명령을 다시 건다.
# 사용: ./recollect_run.sh <자물쇠 이름> <로그 이름> <명령…>
# 실패(차단·오류)나 멈춤이면 다시 걸지 않고 끝낸다 — 막힌 서버를 계속 두드리지 않는다.
cd /Users/keollim/Claude/Projects/edtech
. ./collect_lock.sh
key="$1"; logname="$2"; shift 2
log="logs/${logname}.log"
export EDTECH_SPACING="${EDTECH_SPACING:-10}" EDTECH_MAXREQ="${EDTECH_MAXREQ:-5000}"
while :; do
  # 다른 수집이 자물쇠를 잡고 있으면 풀릴 때까지 기다린다(최대 이틀)
  waited=0
  while [ -d ".locks/$key.lock" ] && [ $waited -lt 172800 ]; do sleep 300; waited=$((waited + 300)); done
  start=$(date +%s); mark=$(wc -l < "$log" 2>/dev/null || echo 0)
  caffeinate -i zsh -c ". ./collect_lock.sh; par_run \"$key\" \"$logname\" $(printf '%q ' "$@")"
  new=$(tail -n +$((mark + 1)) "$log")
  if echo "$new" | grep -q "^■ .*상한"; then
    nap=$(( 86400 - ($(date +%s) - start) )); [ $nap -lt 600 ] && nap=600
    echo "… 하루 상한 — $((nap / 3600))시간 뒤에 이어 받는다 $(date '+%m-%d %H:%M')" >> "$log"
    sleep $nap; continue
  fi
  echo "■■ 실행기 끝 $(date '+%m-%d %H:%M')" >> "$log"; break
done
