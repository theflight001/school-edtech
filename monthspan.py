# 월 갱신이 훑을 기간을 셸 변수 꼴로 찍어 준다.
# 쓰기:  eval "$(python3 monthspan.py 2026-08)"
#
# 왜 따로 두는가: macOS의 date는 `date -v20260801 -v-2m` 같은 형태를 받지 않는다.
# 예전 update_monthly.sh가 그렇게 쓰고 실패를 2>/dev/null로 삼켜, FROM3가 빈 값이 되고
# YEARS가 ",2026"이 되어 수집이 0건으로 끝났다(2026-09-10에 발견).
# GNU date(-d)를 쓰는 리눅스와 macOS를 함께 지원하려다 양쪽 다 안 되던 코드다.
import calendar
import sys

if len(sys.argv) != 2:
    sys.exit("쓰기: monthspan.py YYYY-MM")
try:
    year, month = map(int, sys.argv[1].split("-"))
    calendar.monthrange(year, month)
except ValueError:
    sys.exit(f"기간을 알아볼 수 없다: {sys.argv[1]!r} (YYYY-MM 꼴이어야 한다)")

# 최근 석 달: 계약일과 공개일이 달라 지난달 목록에 그 앞 계약이 섞여 올라온다
from_year, from_month = (year, month - 2) if month > 2 else (year - 1, month + 10)
last_day = calendar.monthrange(year, month)[1]

print(f"FROM3={from_year}-{from_month:02d}")
print(f"BEGIN={from_year}{from_month:02d}01")
print(f"END={year}{month:02d}{last_day:02d}")
print("YEARS=" + ",".join(sorted({str(from_year), str(year)})))
