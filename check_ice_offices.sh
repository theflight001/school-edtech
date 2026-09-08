#!/bin/zsh
# collect_ice.py가 담당하는 나머지 시도도 같은 피해가 있었는지 확인하고 다시 받는다.
# (오류를 '완료'로 적던 버릇 + --keyword-file이 기본 검색어를 덮어쓰던 버릇)
cd "$(dirname "$0")"
while pgrep -f "collect_ice.py --office 경기" > /dev/null; do sleep 120; done
echo "== 경기 끝 ($(date +%H:%M)) =="
for O in 인천 충북 전남 세종; do
  echo "▶ $O ($(date +%H:%M))"
  python3 collect_ice.py --office "$O" --years 2020,2021,2022,2023,2024,2025,2026 \
    --keyword-file edzip_brand_keywords.txt || echo "  ✗ $O 실패"
done
echo "== 네 시도 끝 ($(date +%H:%M)) =="
