# 수집기가 겹쳐 돌지 않게 하는 자물쇠 — 서버별로 하나씩.
#
# 왜 서버별인가: 대전·충남·경남·강원·광주·울산·대구는 서로 다른 교육청 서버다.
# 한 서버에 두 프로세스가 붙으면 요청이 두 배가 되어 차단되고(전남에서 겪었다),
# 무엇보다 같은 체크포인트 파일을 양쪽이 덮어써 받은 것을 잃는다.
# 반대로 서로 다른 서버는 동시에 받아도 서버마다 걸리는 부담이 그대로다 — 그래서 병렬로 받는다.
#
# mkdir은 원자적이라 자물쇠로 쓸 수 있다. 주인이 이미 죽은 자물쇠는 걷어낸다.
LOCKROOT=".locks"

lock_acquire() {            # lock_acquire <서버이름> [기다릴 초]
  local key="$1" wait_max="${2:-0}" waited=0 dir
  mkdir -p "$LOCKROOT"
  dir="$LOCKROOT/$key.lock"
  while :; do
    if mkdir "$dir" 2>/dev/null; then
      echo "$$ $(date '+%Y-%m-%d %H:%M')" > "$dir/owner"
      return 0
    fi
    local pid; pid=$(awk '{print $1}' "$dir/owner" 2>/dev/null)
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
      echo "   ($key: 주인이 없는 자물쇠를 걷어낸다)"
      rm -rf "$dir"; continue
    fi
    [ "$waited" -ge "$wait_max" ] && return 1
    sleep 60; waited=$((waited + 60))
  done
}

lock_release() { rm -rf "$LOCKROOT/$1.lock"; }

# 서버 하나를 맡아 받는다. 자물쇠를 못 잡으면 조용히 물러선다.
# 쓰기: par_run <서버이름> <로그이름> <명령…>
par_run() {
  local key="$1" logname="$2"; shift 2
  local log="logs/${logname}.log"
  mkdir -p logs
  if ! lock_acquire "$key" 0; then
    echo "▷ $key — 다른 수집이 잡고 있어 건너뜀"
    return 0
  fi
  trap "lock_release $key" EXIT
  echo "▶ $key 시작 $(date '+%m-%d %H:%M')" | tee -a "$log"
  # 멈춤 감시: 로그가 EDTECH_STALL초(기본 15분) 넘게 안 움직이면 끊는다.
  # urllib의 timeout은 바이트가 오가는 사이 간격만 재서, 서버가 찔끔찔끔 보내거나 TLS가
  # 중간에 걸리면 총 시간은 끝없이 늘어난다(2026-09-11 경기가 연결 하나를 붙잡고 18분 멈췄다).
  # 요청 간격 10초·재시도 대기 최대 5분이라 정상이면 15분씩 조용할 일이 없다.
  # 파이썬 출력이 파일로 갈 때 뭉쳐 쓰이면 진척이 있어도 조용해 보이므로 버퍼를 끈다.
  PYTHONUNBUFFERED=1 "$@" >> "$log" 2>&1 &
  local pid=$! stall="${EDTECH_STALL:-900}" stalled=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 60
    local age=$(( $(date +%s) - $(stat -f %m "$log" 2>/dev/null || date +%s) ))
    if [ "$age" -ge "$stall" ]; then
      echo "⏸ $key — $((stall / 60))분 동안 진척이 없어 끊는다(체크포인트에서 이어 받는다)" | tee -a "$log"
      kill "$pid" 2>/dev/null; sleep 5; kill -9 "$pid" 2>/dev/null
      stalled=1; break
    fi
  done
  wait "$pid" 2>/dev/null; local rc=$?
  if [ "$stalled" = "1" ]; then
    echo "✗ $key 멈춤 $(date '+%m-%d %H:%M') — $log 를 보라" | tee -a "$log"
  elif [ "$rc" = "0" ]; then
    echo "✓ $key 끝 $(date '+%m-%d %H:%M')" | tee -a "$log"
  else
    echo "✗ $key 실패 $(date '+%m-%d %H:%M') — $log 를 보라" | tee -a "$log"
  fi
  lock_release "$key"
}
