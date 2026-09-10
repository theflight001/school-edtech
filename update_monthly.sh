#!/bin/bash
# 월 1회 자동 갱신 — 최근 석 달을 다시 받아 정제·병합하고 배포까지 한다.
# 사용: ./update_monthly.sh            (지난달 기준 최근 석 달)
#       ./update_monthly.sh 2026-06    (그달 기준)
#
# launchd가 매월 10일 새벽에 부른다(com.edtech.monthly.plist).
# 왜 10일인가: 시도교육청 계약공개는 그달이 끝나고 평균 6일, 늦어도 10일 안에 올라온다
#   (서울 게시물 1,300건을 재 본 값). 1일에 받으면 지난달 자료가 하나도 없다.
# 왜 석 달인가: 계약일과 공개일이 달라 지난달 목록에 그 앞 계약이 섞여 올라온다.
#   한 달만 보면 뒤늦게 올라온 것을 영영 놓친다.
# 원칙:
#   - 수집기는 저마다 체크포인트가 있어 중간에 끊겨도 다음 실행에서 이어 받는다.
#   - 한 곳이 실패해도 나머지는 계속한다. 실패는 로그에 남기고 마지막에 요약한다.
#   - 자료가 하나도 늘지 않으면 빌드·배포를 하지 않는다(빈 커밋 방지).
set -uo pipefail
cd "$(dirname "$0")" || exit 1
. ./collect_lock.sh
# 밀린 곳을 받는 중이면 최대 두 시간까지 기다린다. 그래도 안 놓으면 수집은 건너뛰고
# 정제·빌드·배포만 한다 — 이달 갱신을 통째로 거르는 것보다 낫다.
# 자물쇠는 서버별로 par_run이 알아서 잡는다. 어느 서버를 다른 수집이 잡고 있으면
# 그 곳만 건너뛰고 나머지는 그대로 받는다.
COLLECT=1

MONTH="${1:-$(date -v-1m +%Y-%m)}"          # 예: 2026-07
Y="${MONTH%%-*}"; M="${MONTH##*-}"
# 달 계산은 python으로 한다 — macOS의 date -v는 "20260801" 같은 형태를 받지 않아
# 조용히 빈 값을 내놓았다. 그 탓에 YEARS가 ",2026"이 되어 수집이 0건으로 끝났다.
eval "$(python3 monthspan.py "$MONTH")"
LOG="logs/update_${MONTH}.log"
mkdir -p logs
exec > >(tee -a "$LOG") 2>&1

echo "══ 갱신 시작 $(date '+%Y-%m-%d %H:%M') · 최근 석 달 ${FROM3}~${MONTH} (${BEGIN}~${END})"
[ -f "$HOME/.edtech_env" ] && { set -a; . "$HOME/.edtech_env"; set +a; }
# launchd는 로그인 셸의 PATH를 물려받지 않는다 — node(nvm)를 직접 찾아 붙인다
if ! command -v node >/dev/null; then
  NODEBIN=$(ls -d "$HOME"/.nvm/versions/node/*/bin 2>/dev/null | tail -1)
  [ -n "$NODEBIN" ] && export PATH="$NODEBIN:$PATH"
fi
command -v node >/dev/null || echo "! node를 찾지 못했다 — data_summary.js를 못 만든다"

# 검색어를 전부 쓰면 한 곳에 5천 번 안팎을 물어야 한다. 기본 상한(1,200회)으로는
# 중간에 끊겨 매달 같은 앞부분만 다시 받게 된다. 간격 10초는 그대로 지킨다.
export EDTECH_SPACING=${EDTECH_SPACING:-10} EDTECH_MAXREQ=${EDTECH_MAXREQ:-8000}

FAILED=()
run() {                                      # run <이름> <명령…>
  local name="$1"; shift
  [ "$COLLECT" = "0" ] && { echo "── $name (자물쇠 때문에 건너뜀)"; return 0; }
  echo "── $name"
  # macOS에는 timeout 명령이 없다. 뒤에서 돌리고 지켜보다 두 시간이 넘으면 끊는다.
  "$@" & local pid=$!
  ( sleep 7200; kill -0 $pid 2>/dev/null && { echo "   ⏱ $name 두 시간 넘어 끊는다"; kill $pid; } ) & local watch=$!
  if wait $pid; then echo "   ✓ $name"; else echo "   ✗ $name (건너뜀)"; FAILED+=("$name"); fi
  kill $watch 2>/dev/null; wait $watch 2>/dev/null
}

before=$(wc -l < data.js 2>/dev/null || echo 0)

# ── 1. 수집 (저마다 체크포인트로 이어 받는다)
run "나라장터 계약"   python3 collect_nara_full.py --begin "$BEGIN" --end "$END"
run "나라장터 입찰"   python3 collect_nara_bid.py  --begin "$BEGIN" --end "$END"
# 시도교육청은 저마다 다른 서버다 — 서버별 자물쇠를 잡고 동시에 받는다.
# (한 줄로 세우면 열여섯 곳이 차례를 기다리느라 하룻밤에 서너 곳밖에 못 받는다)
if [ "$COLLECT" = "1" ]; then
  KF=edzip_brand_keywords.txt
  par_run 서울 month_서울 python3 collect_sen.py --relist --years "$YEARS" &
  par_run 경기 month_경기 python3 collect_ice.py --office 경기 --years "$YEARS" --half --page-size 10 --keyword-file $KF &
  par_run 인천 month_인천 python3 collect_ice.py --office 인천 --years "$YEARS" --keyword-file $KF &
  par_run 충북 month_충북 python3 collect_ice.py --office 충북 --years "$YEARS" --keyword-file $KF &
  par_run 전남 month_전남 python3 collect_ice.py --office 전남 --years "$YEARS" --keyword-file $KF &
  par_run 세종 month_세종 python3 collect_ice.py --office 세종 --years "$YEARS" --keyword-file $KF &
  par_run 부산 month_부산 python3 collect_pen.py --office 부산 --begin "$FROM3" --end "$MONTH" --keyword-file $KF &
  par_run 경북 month_경북 python3 collect_pen.py --office 경북 --begin "$FROM3" --end "$MONTH" --keyword-file $KF &
  par_run 대전 month_대전 python3 collect_dje.py --office 대전 --years "$YEARS" --keyword-file $KF &
  par_run 충남 month_충남 python3 collect_dje.py --office 충남 --years "$YEARS" --keyword-file $KF &
  par_run 경남 month_경남 python3 collect_gne.py --years "$YEARS" --keyword-file $KF &
  par_run 제주 month_제주 python3 collect_jje.py --years "$YEARS" &
  par_run 강원 month_강원 python3 collect_gwe.py --keyword-file $KF &
  par_run 대구 month_대구 python3 collect_dge.py --begin "$FROM3" --end "$MONTH" --keyword-file $KF &
  par_run 광주 month_광주 python3 collect_gen.py --years "$YEARS" --keyword-file $KF &
  par_run 울산 month_울산 python3 collect_use.py --keyword-file $KF &
  wait
  echo "── 시도교육청 수집 끝 $(date '+%H:%M')"
else
  echo "── 시도교육청 수집 (자물쇠 때문에 건너뜀)"
fi
# S2B는 접근 제한이 잦아 마지막에 둔다 — 실패해도 나머지는 이미 반영된다
run "S2B 학교장터"   python3 collect_s2b_excel.py --begin "$FROM3" --end "$MONTH"

# 정제·빌드는 남의 서버를 두드리지 않으니 자물쇠와 상관없이 늘 한다
COLLECT=1

# ── 2. 정제
run "시도 정제"      python3 refine_office.py
run "S2B 정제"       python3 refine_s2b.py
run "교육청 일괄"    python3 collect_nara_office.py --begin "$BEGIN" --end "$END"
run "중복 걷어내기"  python3 dedup_office.py
run "입찰 정제"      python3 refine_nara_bid.py
run "교육청 정제"    python3 refine_office_buy.py

# ── 3. 빌드 (규칙 정본은 build_data.py 하나뿐이다)
if ! python3 build_data.py; then
  echo "✗ 빌드 실패 — 배포하지 않고 멈춘다"; exit 1
fi

python3 make_coverage.py || echo "   ✗ 수집현황.csv 생성 실패"

# ── 4. 캐시 파라미터를 올리고 배포 (data.js가 바뀐 때만)
if git diff --quiet -- data.js data_old.js data_detail.js data_summary.js; then
  echo "── 자료에 변화가 없어 배포하지 않는다"
else
  STAMP=$(date +%Y%m%d)
  python3 - "$STAMP" <<'PY'
import re, sys
stamp = sys.argv[1]
for path in ("index.html", "app.js"):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r'(data\.js|data_old\.js|data_detail\.js|data_detail_old\.js|data_summary\.js|app\.js)\?b=[0-9a-z]+',
               lambda m: f"{m.group(1)}?b={stamp}", s)
    open(path, "w", encoding="utf-8").write(s)
print(f"   캐시 파라미터 → {stamp}")
PY
  # 파일 하나가 없으면 git add가 통째로 실패해 아무것도 담기지 않는다 — 있는 것만 골라 담는다
  for f in data.js data_old.js data_detail.js data_detail_old.js data_summary.js \
           index.html app.js og_card.png mined_rules.csv tag_review.md product_origin.csv \
           수집현황.csv office_refined.csv *_refined.csv; do
    [ -e "$f" ] && git add "$f"
  done
  git commit -q -m "월 갱신 ${MONTH} — 자동 수집·정제·빌드

$( [ ${#FAILED[@]} -gt 0 ] && echo "실패한 곳: ${FAILED[*]}" || echo "모든 자료원 정상" )

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>" && git push -q origin main && echo "   ✓ 배포 완료"
fi

echo "══ 끝 $(date '+%H:%M')  실패 ${#FAILED[@]}곳 ${FAILED[*]:-없음}"
[ -s tag_review.md ] && echo "※ tag_review.md에 신규 태그가 있다 — 사람이 확인할 것"
