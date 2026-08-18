#!/bin/zsh
# 2020~2022년 조달 기록 확장 — 2023년부터 쓰던 수집기를 그대로 옛 기간에 돌린다.
# 자료원마다 서버가 다르므로 세 갈래로 나눠 동시에 돌리고, 갈래 안에서는 차례로 간다.
cd "$(dirname "$0")"
set -a; . ~/.edtech_env 2>/dev/null; set +a
Y="2020,2021,2022"
run() { echo "▶ $* ($(date +%H:%M))" >&2; python3 "$@"; echo "◀ 끝 ($(date +%H:%M))" >&2; }

case "$1" in
나라장터)
  run collect_nara_full.py --begin 20200101 --end 20221231
  run collect_nara_bid.py  --begin 20200101 --end 20221231 ;;
s2b)
  run collect_s2b_excel.py --begin 2020-01 --end 2022-12 ;;
교육청)
  # 부산은 뺀다 — 원천에 2023년 이전 자료가 없다. 검색어 없이 훑어도
  # 2020/06·2021/06·2022/06·2022/12 모두 0건이고 2023/03부터 나온다.
  run collect_pen.py --office 경북 --begin 2020-01 --end 2022-12
  run collect_dge.py --begin 2020-01 --end 2022-12
  run collect_gen.py --years $Y
  run collect_gne.py --years $Y
  run collect_jbe.py --years $Y
  run collect_jje.py --years $Y
  run collect_dje.py --office 대전 --years $Y
  run collect_dje.py --office 충남 --years $Y ;;
esac
