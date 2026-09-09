# 수집기가 겹쳐 돌지 않게 하는 자물쇠.
# 왜 필요한가: run_five.sh(밀린 여섯 곳)와 update_monthly.sh(월 갱신)가 같은 시도교육청을
# 동시에 두드리면 (1) 요청이 두 배가 되어 차단 위험이 커지고 (2) 무엇보다 같은 체크포인트
# 파일(.ckpt_충남.json 등)을 양쪽이 덮어써서 받은 것을 잃는다.
#
# mkdir은 원자적이라 자물쇠로 쓸 수 있다. 죽은 자물쇠(프로세스가 이미 없는 것)는 걷어낸다.
LOCKDIR=".collect.lock"

lock_acquire() {            # lock_acquire <이름> [기다릴 초]
  local who="$1" wait_max="${2:-0}" waited=0
  while :; do
    if mkdir "$LOCKDIR" 2>/dev/null; then
      echo "$who $$ $(date '+%Y-%m-%d %H:%M')" > "$LOCKDIR/owner"
      trap 'lock_release' EXIT INT TERM
      return 0
    fi
    local pid; pid=$(awk '{print $2}' "$LOCKDIR/owner" 2>/dev/null)
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
      echo "   (죽은 자물쇠를 걷어낸다: $(cat "$LOCKDIR/owner" 2>/dev/null))"
      rm -rf "$LOCKDIR"; continue
    fi
    [ "$waited" -ge "$wait_max" ] && return 1
    sleep 60; waited=$((waited + 60))
  done
}

lock_release() { rm -rf "$LOCKDIR"; }
