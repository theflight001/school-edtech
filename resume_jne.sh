#!/bin/zsh
# 전남교육청 차단이 풀렸는지 조심스럽게 확인하고, 풀렸으면 이어 받는다.
#
# 2026-09-04 전남(jge.go.kr)이 우리 IP를 막았다. 초당 한 번씩 몇 시간을 두드린 탓이다.
# 그래서 이 스크립트는 세 가지를 지킨다.
#   1. 2026-09-12 전까지는 아예 건드리지 않는다 — 자동 차단이 풀릴 시간을 준다.
#   2. 확인은 여섯 시간에 한 번, 요청 한 번뿐이다.
#   3. 풀렸으면 10초 간격으로 하루 600회까지만 받고 멈춘다(체크포인트로 이어 받는다).
cd "$(dirname "$0")"
set -a; . ~/.edtech_env 2>/dev/null; set +a
NOTBEFORE=20260912
LOG=jne_resume.log

if [ "$(date +%Y%m%d)" -lt "$NOTBEFORE" ]; then
  echo "$(date '+%m-%d %H:%M') 아직 기다리는 중 (${NOTBEFORE}부터 확인)" >> $LOG
  exit 0
fi

# 딱 한 번만 찔러 본다
OK=$(python3 - <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("ice", "collect_ice.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.URL, m.SYSID, m.MI = m.OFFICES["전남"]
try:
    b = m.fetch("소프트웨어", 1, "2025", "", "")
    print("OK" if b and len(b) > 5000 else "SHORT")
except Exception as e:
    print("BLOCKED")
PY
)
echo "$(date '+%m-%d %H:%M') 확인 결과: $OK" >> $LOG
[ "$OK" = "OK" ] || exit 0

echo "$(date '+%m-%d %H:%M') 차단이 풀렸다 — 이어 받는다" >> $LOG
EDTECH_SPACING=10 EDTECH_MAXREQ=600 \
  python3 collect_ice.py --office 전남 \
    --years 2020,2021,2022,2023,2024,2025,2026 \
    --keyword-file edzip_brand_keywords.txt >> $LOG 2>&1
echo "$(date '+%m-%d %H:%M') 이번 몫 끝" >> $LOG
