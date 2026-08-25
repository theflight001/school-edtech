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

MONTH="${1:-$(date -v-1m +%Y-%m)}"          # 예: 2026-07
Y="${MONTH%%-*}"; M="${MONTH##*-}"
FROM3=$(date -v"${Y}${M}01" -v-2m +%Y-%m 2>/dev/null || date -d "${Y}-${M}-01 -2 month" +%Y-%m)
BEGIN="${FROM3%%-*}${FROM3##*-}01"
YEARS=$(python3 -c "import sys;a,b=sys.argv[1:3];print(','.join(sorted({a[:4],b[:4]})))" "$FROM3" "$MONTH")
END=$(date -v"${Y}${M}01" -v+1m -v-1d +%Y%m%d 2>/dev/null || date -d "${Y}-${M}-01 +1 month -1 day" +%Y%m%d)
LOG="logs/update_${MONTH}.log"
mkdir -p logs
exec > >(tee -a "$LOG") 2>&1

echo "══ 갱신 시작 $(date '+%Y-%m-%d %H:%M') · 최근 석 달 ${FROM3}~${MONTH} (${BEGIN}~${END})"
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
run "서울"           python3 collect_sen.py --relist --years "$YEARS"
run "경기"           python3 collect_ice.py --office 경기 --years "$YEARS" --half --page-size 10
run "인천"           python3 collect_ice.py --office 인천 --years "$YEARS"
run "충북"           python3 collect_ice.py --office 충북 --years "$YEARS"
run "전남"           python3 collect_ice.py --office 전남 --years "$YEARS"
run "세종"           python3 collect_ice.py --office 세종 --years "$YEARS"
run "부산"           python3 collect_pen.py --office 부산 --years "$YEARS"
run "경북"           python3 collect_pen.py --office 경북 --years "$YEARS"
run "대전"           python3 collect_dje.py --office 대전 --years "$YEARS" --keyword-file edzip_brand_keywords.txt
run "충남"           python3 collect_dje.py --office 충남 --years "$YEARS" --keyword-file edzip_brand_keywords.txt
run "경남"           python3 collect_gne.py --years "$YEARS" --keyword-file edzip_brand_keywords.txt
run "제주"           python3 collect_jje.py --years "$YEARS"
run "강원"           python3 collect_gwe.py --keyword-file edzip_brand_keywords.txt
run "대구"           python3 collect_dge.py --begin "$FROM3" --end "$MONTH" --keyword-file edzip_brand_keywords.txt
run "광주"           python3 collect_gen.py --years "$YEARS" --keyword-file edzip_brand_keywords.txt
run "울산"           python3 collect_use.py --keyword-file edzip_brand_keywords.txt
# S2B는 접근 제한이 잦아 마지막에 둔다 — 실패해도 나머지는 이미 반영된다
run "S2B 학교장터"   python3 collect_s2b_excel.py --begin "$FROM3" --end "$MONTH"

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
  git add -A data.js data_old.js data_detail.js data_detail_old.js data_summary.js \
           index.html app.js mined_rules.csv tag_review.md product_origin.csv \
           수집현황.csv office_refined.csv *_refined.csv 2>/dev/null
  git commit -q -m "월 갱신 ${MONTH} — 자동 수집·정제·빌드

$( [ ${#FAILED[@]} -gt 0 ] && echo "실패한 곳: ${FAILED[*]}" || echo "모든 자료원 정상" )

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>" && git push -q origin main && echo "   ✓ 배포 완료"
fi

echo "══ 끝 $(date '+%H:%M')  실패 ${#FAILED[@]}곳 ${FAILED[*]:-없음}"
[ -s tag_review.md ] && echo "※ tag_review.md에 신규 태그가 있다 — 사람이 확인할 것"
