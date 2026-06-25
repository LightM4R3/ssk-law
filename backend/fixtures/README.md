# 기본 법안 데이터 fixture

`basic_bills.json`은 2026-06-22 기준 국회 OpenAPI에서 수집한 개발용 기본 데이터입니다.

포함 범위:

- 실제 법안 398건
- AI 요약 239건
- 카테고리와 법안-카테고리 연결
- 유사 법안 데이터

제외 범위:

- `BillProcessingTask` 처리 큐
- `SyncRun` 실행 이력
- 검색 세션과 채팅 데이터

새 DB에 마이그레이션을 적용한 뒤 다음 명령으로 불러옵니다.

```bash
python manage.py migrate
python manage.py loaddata fixtures/basic_bills.json
```

요약이 없는 법안의 처리 작업은 다음 명령으로 생성합니다.

```bash
python manage.py enqueue_bill_processing --processor summary
```

기본 데이터를 갱신할 때는 worker를 종료하고 DB 쓰기가 멈춘 상태에서 fixture를 다시 생성합니다.

```bash
python manage.py dumpdata \
  bills.category \
  bills.bill \
  bills.billcategory \
  bills.billsummary \
  bills.similarbill \
  --indent 2 \
  --output fixtures/basic_bills.json
```
