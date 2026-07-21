# 학교 에듀테크 활용현황 (가칭)

전국 초·중·고등학교의 에듀테크 도입 기록을 조달·공개자료 기반으로 검색·열람하는 공공 정보 서비스 프로토타입.

## 구조

- `index.html` + `data.js` — 정적 단일 페이지 앱 (배포 대상은 이 두 파일)
- `build_data.py` — `db_export.csv`(심층조사 DB) + `refined_*.csv`(자동수집분)를 `data.js`로 변환·병합
- `collect_nara.py` — 나라장터 계약정보 OpenAPI 수집 배치 (`NARA_KEY` 환경변수 필요)
- `refine_candidates.py` — 수집분 정제(수요기관명 정리, NEIS 학교코드 매칭)
- `fetch_schools.py` — NEIS 개방포털에서 전국 학교 마스터(`school_master.json`) 갱신
- `서비스개발_핸드오프.md` — 기획·아키텍처 문서

## 데이터 갱신 절차

```bash
NARA_KEY=<키> python3 collect_nara.py --begin YYYYMMDD --end YYYYMMDD
python3 refine_candidates.py candidates_<begin>_<end>.csv
python3 build_data.py
```

API 키는 환경변수로만 전달하고 저장소에 커밋하지 않는다.

## 수동 제품 보정

조달 기록에 브랜드가 없는 계약("교육용소프트웨어, 수요기관규격" 등)은 실제 제품을 확인한 뒤
`manual_overrides.csv`에 한 줄 추가하면 다음 빌드부터 반영된다 (태그 부여·신뢰도 상 승격·근거 표기):

```
계약번호,실제제품명,근거,메모
2024070213193,매쓰플랫,학교 공고문 URL,사양서에서 확인
```
