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
  # EDTECH_SKIP="대전 전남" — 차단당해 쉬게 둔 서버는 건너뛴다
  case " ${EDTECH_SKIP:-} " in *" $key "*) echo "▷ $key — 쉬게 둔 서버라 건너뜀(EDTECH_SKIP)"; return 0 ;; esac
  if ! lock_acquire "$key" 0; then
    echo "▷ $key — 다른 수집이 잡고 있어 건너뜀"
    return 0
  fi
  trap "lock_release $key" EXIT
  # 결과는 표지 파일로 남긴다 — par_run은 뒤(&)에서 돌아 부모의 FAILED 배열을 고칠 수 없다.
  # 그 탓에 수집 ✗가 한 번도 배포를 막지 못했다(2026-11-09 발견). update_monthly.sh가 wait 뒤에 .locks/fail.* 를 거둬 간다.
  rm -f "$LOCKROOT/fail.$key"
  echo "▶ $key 시작 $(date '+%m-%d %H:%M')" | tee -a "$log"
  # 멈춤 감시: 로그가 EDTECH_STALL초(기본 15분) 넘게 안 움직이면 끊는다.
  # urllib의 timeout은 바이트가 오가는 사이 간격만 재서, 서버가 찔끔찔끔 보내거나 TLS가
  # 중간에 걸리면 총 시간은 끝없이 늘어난다(2026-09-11 경기가 연결 하나를 붙잡고 18분 멈췄다).
  # 요청 간격 10초·재시도 대기 최대 5분이라 정상이면 15분씩 조용할 일이 없다.
  # 파이썬 출력이 파일로 갈 때 뭉쳐 쓰이면 진척이 있어도 조용해 보이므로 버퍼를 끈다.
  # 멈춰 끊긴 것은 체크포인트에서 다시 건다(기본 세 번까지) — 한 연결이 걸려 멈춘 것이지
  # 서버가 막은 것이 아니다. 실패(차단 등)는 다시 걸지 않는다.
  #
  # 종료 코드 약속(수집기 공통):
  #   0  끝 — 맡은 칸을 다 받았다
  #   2  막힘·끊김 — 다시 걸어도 소용없다(.pause_until에 쉴 시간을 적는다). 실패로 적는다
  #   3  상한에 닿았거나 못 받은 칸이 남았다 — 끝이 아니다. 체크포인트에서 이어 받으면 끝난다
  #   그 밖  오류 — 실패로 적는다
  # 상한은 한 번 실행의 숨 고르기일 뿐이고 수집은 끝나야 끝난다(2026-11-09 사용자 지적 — 그 전에는
  # 상한에 닿아 절반만 받은 곳도 ✓로 적혀 그대로 배포됐다: 11/7 광주). 3이 나오면 EDTECH_RESUME_PAUSE초
  # (기본 300) 쉬고 같은 명령을 다시 건다. EDTECH_RESUME_RETRY번(기본 6) 안에 0이 안 나오면 — 사이트가
  # 바뀌어 헛도는 것일 수 있으니 — 실패로 적어 배포를 막는다. 요청 간격은 그대로다.
  local pid rc stalled attempt=0 tries="${EDTECH_STALL_RETRY:-3}" stall="${EDTECH_STALL:-900}"
  local resumed=0 resume_max="${EDTECH_RESUME_RETRY:-6}" resume_pause="${EDTECH_RESUME_PAUSE:-300}"
  while :; do
    attempt=$((attempt + 1))
    PYTHONUNBUFFERED=1 "$@" >> "$log" 2>&1 &
    pid=$!; stalled=0
    while kill -0 "$pid" 2>/dev/null; do
      sleep 60
      local age=$(( $(date +%s) - $(stat -f %m "$log" 2>/dev/null || date +%s) ))
      if [ "$age" -ge "$stall" ]; then
        echo "⏸ $key — $((stall / 60))분 동안 진척이 없어 끊는다(체크포인트에서 이어 받는다)" | tee -a "$log"
        kill "$pid" 2>/dev/null; sleep 5; kill -9 "$pid" 2>/dev/null
        stalled=1; break
      fi
    done
    wait "$pid" 2>/dev/null; rc=$?
    if [ "$stalled" = "1" ] && [ "$attempt" -lt "$tries" ]; then
      echo "↻ $key — 멈춰서 체크포인트에서 다시 건다 ($((attempt + 1))/$tries)" | tee -a "$log"
      continue
    fi
    if [ "$stalled" = "0" ] && [ "$rc" = "3" ] && [ "$resumed" -lt "$resume_max" ]; then
      resumed=$((resumed + 1)); attempt=0
      echo "↻ $key — 상한에 닿았거나 못 받은 칸이 남았다. ${resume_pause}초 쉬고 이어 받는다 ($resumed/$resume_max) $(date '+%m-%d %H:%M')" | tee -a "$log"
      sleep "$resume_pause"
      continue
    fi
    break
  done
  if [ "$stalled" = "1" ]; then
    echo "✗ $key 멈춤 $(date '+%m-%d %H:%M') — $log 를 보라" | tee -a "$log"
    echo "멈춤" > "$LOCKROOT/fail.$key"
  elif [ "$rc" = "0" ]; then
    echo "✓ $key 끝 $(date '+%m-%d %H:%M')$( [ "$resumed" -gt 0 ] && echo " (이어 받기 ${resumed}번)")" | tee -a "$log"
  elif [ "$rc" = "3" ]; then
    echo "✗ $key ${resume_max}번 이어 받고도 안 끝남 $(date '+%m-%d %H:%M') — 사이트가 바뀌었는지 $log 를 보라" | tee -a "$log"
    echo "${resume_max}번 이어 받고도 안 끝남" > "$LOCKROOT/fail.$key"
  elif [ "$rc" = "2" ]; then
    echo "✗ $key 막힘·끊김 $(date '+%m-%d %H:%M') — $log 와 .pause_until 을 보라" | tee -a "$log"
    echo "막힘·끊김" > "$LOCKROOT/fail.$key"
  else
    echo "✗ $key 실패(코드 $rc) $(date '+%m-%d %H:%M') — $log 를 보라" | tee -a "$log"
    echo "실패 코드 $rc" > "$LOCKROOT/fail.$key"
  fi
  lock_release "$key"
}
