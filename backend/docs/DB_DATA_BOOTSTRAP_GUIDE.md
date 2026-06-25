# DB 데이터 기초 작업 가이드

이 문서는 로컬 개발 DB에 국회 OpenAPI의 실제 법안을 적재하고, AI 요약 작업을 처리한 뒤 일일 자동 동기화로 전환하는 절차를 설명합니다.

## 1. 처리 구조

데이터 수집과 AI 처리는 서로 분리되어 있습니다.

```text
국회 OpenAPI 조회
→ 신규·변경 법안 DB 저장
→ BillProcessingTask 생성
→ 요약 전에도 REST API에서 법안 노출
→ worker가 상세 내용 조회
→ Ollama가 3줄 요약 및 카테고리 생성
→ 성공·재시도·실패 상태 기록
```

- `sync_bills`: OpenAPI 데이터를 로컬 DB에 저장합니다.
- `process_bill_tasks`: 저장된 법안의 AI 후처리 작업을 수행합니다.
- 일반 화면 API는 OpenAPI나 Ollama를 직접 호출하지 않습니다.

## 2. 실행 환경 준비

Git Bash에서 백엔드 가상환경을 활성화합니다.

```bash
cd ~/Documents/SSK-LAW/backend
source venv/Scripts/activate
```

환경과 Django 설정을 확인합니다.

```bash
python manage.py check
python -m pip check
```

데이터 수집에는 Django 서버나 Ollama가 실행 중일 필요가 없습니다. AI 요약 처리에는 Ollama가 필요합니다.

## 3. 샘플 데이터 제거

실제 데이터만 사용하려면 최초 한 번 샘플 법안 11건을 제거합니다. 해당 작업은 관련 요약과 카테고리 연결도 함께 삭제합니다.

```bash
python manage.py shell -c "from bills.models import Bill; ids=['PRC_P1','PRC_P2','PRC_P3','PRC_P4','PRC_P5','PRC_B3','PRC_B4','PRC_B7','PRC_B8','PRC_B9','PRC_B10']; print(Bill.objects.filter(bill_id__in=ids).delete())"
```

`PRC_` 접두사를 기준으로 일괄 삭제하면 실제 국회 법안까지 삭제될 수 있으므로 위의 정확한 ID 목록만 사용합니다.

## 4. 초기 실제 법안 적재

현재 시점부터 과거 방향으로 약 300건을 확보하려면 다음 명령을 실행합니다.

```bash
python manage.py sync_bills --target-count 300 --pages 50 --trigger manual
```

옵션의 의미는 다음과 같습니다.

- `--target-count 300`: 일반 법안 API에서 고유 의안번호 300건을 처리하면 조회를 종료합니다.
- `--pages 50`: API 오류나 정렬 문제에 대비해 최대 50페이지만 조회합니다.
- `--trigger manual`: 실행 이력을 수동 실행으로 기록합니다.

일반 법안 조회 이후 법사위·본회의 데이터도 동기화되므로 최종 생성 건수는 300건보다 많을 수 있습니다. 예를 들어 `fetched=500`, `created=398`은 일반 법안 300건과 단계 API 조회 결과가 합산된 정상적인 결과입니다.

현재 구현은 국회 API의 앞쪽 페이지가 최신순이라는 전제를 사용합니다. API 정렬 정책이 바뀌거나 최신순이 보장되지 않는 경우 OpenAPI가 지원하는 정렬 조건을 명시적으로 추가해야 합니다.

## 5. 적재 결과 확인

법안, 요약, 작업 상태와 마지막 동기화 결과를 확인합니다.

```bash
python manage.py shell -c "from django.db.models import Count; from bills.models import Bill,BillSummary,BillProcessingTask,SyncRun; print('법안:',Bill.objects.count()); print('요약:',BillSummary.objects.count()); print('작업:',list(BillProcessingTask.objects.values('processor','status').annotate(count=Count('id')))); print('동기화:',SyncRun.objects.order_by('-started_at').values('status','trigger','fetched_count','created_count','updated_count','failed_count','error_message').first())"
```

정상적인 초기 상태는 다음과 같습니다.

```text
법안: 약 300건 이상
요약: 0건 또는 일부 완료
summary 작업: 대부분 pending
마지막 동기화: success 또는 no_changes
```

## 6. AI 요약 처리

설치된 Ollama 모델을 확인합니다.

```bash
ollama list
```

먼저 소량을 처리해 요약 품질과 처리 시간을 확인합니다.

```bash
python manage.py process_bill_tasks --limit 5
```

정상 동작을 확인한 뒤 10건씩 처리합니다.

```bash
python manage.py process_bill_tasks --limit 10
```

현재 실행 가능한 작업이 모두 소진될 때까지 5건씩 자동 반복하려면 다음 명령을 사용합니다.

```bash
python manage.py process_bill_tasks --limit 5 --until-empty --sleep-seconds 3
```

`--until-empty`는 `pending` 또는 실행 시간이 된 `retry` 작업이 더 이상 없으면 종료합니다. 아직 재시도 시간이 되지 않은 작업을 기다리지는 않으므로 해당 작업은 이후 worker 실행에서 처리됩니다.

worker는 작업을 직렬로 처리합니다. 수백 건을 한 번에 지정하면 장시간 실행될 수 있으므로 소량 반복 또는 Windows 작업 스케줄러 사용을 권장합니다.

작업 상태는 다음 순서로 변합니다.

```text
pending → running → succeeded
                   ↘ retry → succeeded
                           ↘ failed
```

실패 시 최초 실행 후 1분, 5분, 30분 간격으로 재시도합니다. 최종 실패한 작업은 `last_error`를 유지합니다.

## 7. 누락된 작업 보정

법안은 존재하지만 처리 작업이 생성되지 않은 경우 다음 명령을 사용합니다. 이미 존재하는 작업은 중복 생성되지 않습니다.

```bash
python manage.py enqueue_bill_processing --processor summary
```

## 8. 처리 현황과 오류 확인

상태별 작업 수를 확인합니다.

```bash
python manage.py shell -c "from django.db.models import Count; from bills.models import BillProcessingTask; print(list(BillProcessingTask.objects.values('status').annotate(count=Count('id')).order_by('status')))"
```

최종 실패 작업과 오류를 확인합니다.

```bash
python manage.py shell -c "from bills.models import BillProcessingTask; print(list(BillProcessingTask.objects.filter(status='failed').values('bill__bill_no','bill__title','last_error')[:20]))"
```

원인을 해결한 후 실패 작업을 다시 대기열에 넣으려면 다음 명령을 사용합니다.

```bash
python manage.py shell -c "from django.utils import timezone; from bills.models import BillProcessingTask; print(BillProcessingTask.objects.filter(status='failed').update(status='retry',attempt_count=0,next_attempt_at=timezone.now(),finished_at=None))"
```

오류 원인을 확인하지 않은 상태에서 반복 초기화하지 않습니다.

## 9. 일일 증분 동기화

초기 적재 이후에는 매번 300건을 조회할 필요가 없습니다.

```bash
python manage.py sync_bills --pages 10 --known-page-limit 2 --trigger scheduled
```

- 최신 페이지부터 신규·변경 법안을 저장합니다.
- 신규나 변경이 없는 페이지가 2번 연속 나오면 조회를 종료합니다.
- 같은 법안은 의안번호 기준으로 중복 생성되지 않습니다.
- 기존 법안의 처리 단계는 이전 단계로 후퇴하지 않습니다.

법안 공개가 09시부터 10시 사이에 이어질 수 있으므로 09시 한 번보다 09:00~10:00 사이 10분 간격 조회를 사용합니다.

## 10. Windows 자동 작업 등록

관리자 PowerShell에서 다음 스크립트를 한 번 실행합니다.

```powershell
cd C:\Users\SSAFY\Documents\SSK-LAW\backend
powershell -ExecutionPolicy Bypass -File .\scripts\register_bill_tasks.ps1
```

등록되는 작업은 다음과 같습니다.

- 09:00~10:00: 10분 간격 법안 동기화
- 13:00: 오전 신규 법안이 없을 때 보정 동기화
- 매분: 대기 중인 AI 작업 1건 처리
- 동일 작업 중복 실행: `IgnoreNew`로 방지

등록 상태는 PowerShell에서 확인합니다.

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -like "SSKLaw*" }
```

## 11. API와 화면 확인

백엔드와 프론트엔드를 실행한 뒤 다음 항목을 확인합니다.

```text
http://127.0.0.1:8000/api/sync/status
http://127.0.0.1:8000/api/bills?page=1
http://127.0.0.1:5173
```

- 요약 전 법안도 목록에 표시되어야 합니다.
- 요약 대기 법안은 `summaryStatus=pending`이어야 합니다.
- 처리 완료 후 `summaryStatus=ready`로 변경되어야 합니다.
- 일반 목록 요청 중 OpenAPI나 Ollama가 호출되면 안 됩니다.

## 12. 운영 원칙

- 수집과 AI 처리를 하나의 명령으로 합치지 않습니다.
- 신규 법안은 요약 완료를 기다리지 않고 즉시 노출합니다.
- 초기 적재 이후에는 증분 동기화를 사용합니다.
- `seed_data`는 실제 데이터 운영 DB에서 다시 실행하지 않습니다.
- `sync_and_process_100_bills`보다 `sync_bills`와 `process_bill_tasks`를 분리해 사용합니다.
- `SyncRun`과 `BillProcessingTask`의 오류를 확인한 뒤 재실행합니다.
- SQLite를 사용하는 동안 여러 대량 쓰기 작업을 동시에 실행하지 않습니다.

## 13. 완료 기준

다음 조건을 만족하면 기초 데이터 구축이 완료된 것입니다.

- 샘플 법안이 제거되고 실제 국회 법안만 존재함
- 초기 목표 수 이상의 실제 법안이 저장됨
- 마지막 `SyncRun`이 `success` 또는 `no_changes`
- 요약 작업이 생성되고 worker가 정상 처리함
- `pending`과 `retry`가 지속적으로 감소함
- `failed` 작업의 원인이 확인됨
- 목록 API가 로컬 DB만 사용해 즉시 응답함
- Windows 일일 동기화와 worker 작업이 등록됨

## 14. 기본 데이터 fixture 보존

SQLite 파일 자체는 실행 이력과 임시 작업 상태까지 포함하므로 Git에 직접 커밋하지 않습니다. 공개 법안과 완성된 요약만 Django fixture로 내보냅니다.

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

새 로컬 DB에서는 다음 순서로 복원합니다.

```bash
python manage.py migrate
python manage.py loaddata fixtures/basic_bills.json
python manage.py enqueue_bill_processing --processor summary
```

fixture 생성 중 DB 내용이 바뀌지 않도록 worker와 동기화 명령을 먼저 종료합니다.
