#!/bin/bash
# 월 1회 자동 갱신 — 지난달치를 받아 정제·병합하고 배포까지 한다.
# 사용: ./update_monthly.sh            (지난달분)
#       ./update_monthly.sh 2026-06    (특정 달)
#
# launchd가 매월 1일 새벽에 부른다(com.edtech.monthly.plist).
# 원칙:
#   - 수집기는 저마다 체크포인트가 있어 중간에 끊겨도 다음 실행에서 이어 받는다.
#   - 한 곳이 실패해도 나머지는 계속한다. 실패는 로그에 남기고 마지막에 요약한다.
#   - 자료가 하나도 늘지 않으면 빌드·배포를 하지 않는다(빈 커밋 방지).
set -uo pipefail
cd "$(dirname "$0")" || exit 1

MONTH="${1:-$(date -v-1m +%Y-%m)}"          # 예: 2026-07
Y="${MONTH%%-*}"; M="${MONTH##*-}"
BEGIN="${Y}${M}01"
END=$(date -v"${Y}${M}01" -v+1m -v-1d +%Y%m%d 2>/dev/null || date -d "${Y}-${M}-01 +1 month -1 day" +%Y%m%d)
LOG="logs/update_${MONTH}.log"
mkdir -p logs
exec > >(tee -a "$LOG") 2>&1

echo "══ 갱신 시작 $(date '+%Y-%m-%d %H:%M') · 대상 ${MONTH} (${BEGIN}~${END})"
[ -f "$HOME/.edtech_env" ] && { set -a; . "$HOME/.edtech_env"; set +a; }

FAILED=()
run() {                                      # run <이름> <명령…>
  local name="$1"; shift
  echo "── $name"
  if timeout 7200 "$@"; then echo "   ✓ $name"; else echo "   ✗ $name (건너뜀)"; FAILED+=("$name"); fi
}

before=$(wc -l < data.js 2>/dev/null || echo 0)

# ── 1. 수집 (저마다 체크포인트로 이어 받는다)
run "나라장터 계약"   python3 collect_nara_full.py --begin "$BEGIN" --end "$END"
run "나라장터 입찰"   python3 collect_nara_bid.py  --begin "$BEGIN" --end "$END"
run "서울"           python3 collect_sen.py --relist --years "$Y"
run "경기"           python3 collect_ice.py --office 경기 --years "$Y" --half --page-size 10
run "인천"           python3 collect_ice.py --office 인천 --years "$Y"
run "충북"           python3 collect_ice.py --office 충북 --years "$Y"
run "전남"           python3 collect_ice.py --office 전남 --years "$Y"
run "세종"           python3 collect_ice.py --office 세종 --years "$Y"
run "부산"           python3 collect_pen.py --office 부산 --years "$Y"
run "경북"           python3 collect_pen.py --office 경북 --years "$Y"
run "대전"           python3 collect_dje.py --office 대전 --years "$Y" --keyword-file edzip_brand_keywords.txt
run "충남"           python3 collect_dje.py --office 충남 --years "$Y" --keyword-file edzip_brand_keywords.txt
run "경남"           python3 collect_gne.py --years "$Y" --keyword-file edzip_brand_keywords.txt
run "제주"           python3 collect_jje.py --years "$Y"
run "강원"           python3 collect_gwe.py --keyword-file edzip_brand_keywords.txt
run "대구"           python3 collect_dge.py --begin "$BEGIN" --end "$END" --keyword-file edzip_brand_keywords.txt
run "광주"           python3 collect_gen.py --years "$Y" --keyword-file edzip_brand_keywords.txt
run "울산"           python3 collect_use.py --keyword-file edzip_brand_keywords.txt
# S2B는 접근 제한이 잦아 마지막에 둔다 — 실패해도 나머지는 이미 반영된다
run "S2B 학교장터"   python3 collect_s2b_excel.py --begin "$MONTH" --end "$MONTH"

# ── 2. 정제
run "시도 정제"      python3 refine_office.py
run "S2B 정제"       python3 refine_s2b.py
run "입찰 정제"      python3 refine_nara_bid.py

# ── 3. 빌드 (규칙 정본은 build_data.py 하나뿐이다)
if ! python3 build_data.py; then
  echo "✗ 빌드 실패 — 배포하지 않고 멈춘다"; exit 1
fi

# ── 4. 캐시 파라미터를 올리고 배포 (data.js가 바뀐 때만)
if git diff --quiet -- data.js data_detail.js data_summary.js; then
  echo "── 자료에 변화가 없어 배포하지 않는다"
else
  STAMP=$(date +%Y%m%d)
  python3 - "$STAMP" <<'PY'
import re, sys
stamp = sys.argv[1]
for path in ("index.html", "app.js"):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r'(data\.js|data_detail\.js|data_summary\.js|app\.js)\?b=[0-9a-z]+',
               lambda m: f"{m.group(1)}?b={stamp}", s)
    open(path, "w", encoding="utf-8").write(s)
print(f"   캐시 파라미터 → {stamp}")
PY
  git add -A data.js data_detail.js data_summary.js index.html app.js \
           mined_rules.csv tag_review.md product_origin.csv *_refined.csv 2>/dev/null
  git commit -q -m "월 갱신 ${MONTH} — 자동 수집·정제·빌드

$( [ ${#FAILED[@]} -gt 0 ] && echo "실패한 곳: ${FAILED[*]}" || echo "모든 자료원 정상" )

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>" && git push -q origin main && echo "   ✓ 배포 완료"
fi

echo "══ 끝 $(date '+%H:%M')  실패 ${#FAILED[@]}곳 ${FAILED[*]:-없음}"
[ -s tag_review.md ] && echo "※ tag_review.md에 신규 태그가 있다 — 사람이 확인할 것"
