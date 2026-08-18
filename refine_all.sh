#!/bin/zsh
# 2020년 확장분 정제 — 자료원마다 정제기가 다르다. 판정 규칙은 build_data.py 하나뿐이고
# 각 정제기가 그것을 불러다 쓴다.
cd "$(dirname "$0")"
step() { echo "▶ $* ($(date +%H:%M))"; python3 "$@" || echo "!! 실패: $*"; }
step refine_office.py
step refine_s2b.py
step refine_nara_bid.py
step extract_edtech.py
echo "◀ 정제 끝 ($(date +%H:%M))"
