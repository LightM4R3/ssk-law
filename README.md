# 슥법 SSK-Law

슥법(SSK-Law)은 국회에 매일 추가되는 법률안을 일반 시민이 빠르게 이해하고, 검색하고, 의견을 남길 수 있도록 만든 법안 큐레이션 서비스입니다.

법률안 원문은 길고 어렵고, 국회 의안 단계도 계속 바뀝니다. 슥법은 열린국회정보 OpenAPI에서 법안을 수집해 로컬 DB에 저장하고, AI 요약과 카테고리 분류를 비동기 처리한 뒤, 화면 API는 항상 로컬 DB만 조회하도록 설계했습니다.

현재 버전은 발표용 MVP 기준으로 다음 흐름을 제공합니다.

```text
국회 OpenAPI 법안 수집
→ DB 저장 및 처리 이력 기록
→ AI 요약/카테고리 후처리
→ 최신/인기/분야별/검색 화면 제공
→ 법안별 포스트와 댓글 커뮤니티
→ 로그인 세션 기반 작성/수정/삭제
```

## 발표용 핵심 요약

| 구분 | 내용 |
|---|---|
| 서비스 문제 | 법률안 정보가 어렵고 흩어져 있어 시민이 현재 발의안의 의미와 진행 상황을 파악하기 어렵다. |
| 해결 방향 | 국회 법안 데이터를 자동 수집하고, AI 요약과 자연어 검색으로 시민 친화적인 탐색 경험을 제공한다. |
| 핵심 차별점 | OpenAPI/AI 처리를 화면 API와 분리해 성능을 확보하고, 법안별 시민 의견 포스트를 연결한다. |
| 주요 사용자 | 법안 이슈를 빠르게 알고 싶은 시민, 학생, 기획/정책 조사자, 발표/토론 준비자 |
| MVP 범위 | 법안 수집, AI 요약, 단계 갱신, 자연어 DB 검색, Auth, 포스트/댓글, 분야별 탐색 |

## 주요 기능

### 1. 법안 탐색

- 최신 법안 페이지
- 인기 법안 페이지
- 분야별 법안 페이지
- 분야별 상세 페이지의 단계 필터
  - 전체
  - 발의
  - 위원회 심사
  - 본회의 상정
  - 통과 · 공포
- 법안 상세 모달
  - 발의일
  - 대표 발의
  - 의안번호
  - 현재 단계
  - 최근 갱신일
  - AI 3줄 요약
  - 원문 보기
  - 시민 의견 포스트 목록

### 2. 법안 자동 수집과 단계 갱신

백엔드는 열린국회정보 OpenAPI를 통해 법안을 수집합니다.

- 일반 발의안 API에서 신규 법안 수집
- 위원회 심사 API에서 단계 갱신
- 본회의/처리 API에서 통과, 폐기, 철회 등 결과 갱신
- `bill_id` 기준 멱등 저장
- 기존 법안의 단계가 뒤로 후퇴하지 않도록 방지
- `SyncRun`에 동기화 실행 이력 저장

현재 단계 모델은 다음 4단계입니다.

```text
발의 → 위원회 심사 → 본회의 상정 → 통과 · 공포
```

처리 결과는 `result_status`, `result_text`로 별도 저장합니다.

예시:

- 원안가결
- 수정가결
- 대안가결
- 철회
- 폐기
- 대안반영폐기
- 부결
- 회송
- 심사미료

### 3. AI 요약 후처리

법안 수집과 AI 처리는 분리되어 있습니다.

```text
sync_bills
→ 신규 법안 저장
→ BillProcessingTask 생성
→ 화면에는 즉시 노출
→ process_bill_tasks worker가 요약 처리
→ BillSummary 저장
→ 카테고리 갱신
```

이 구조 덕분에 AI 요약이 느리거나 실패해도 법안 목록 API는 지연되지 않습니다.

요약 상태는 API에 `summaryStatus`로 내려갑니다.

| 상태 | 의미 |
|---|---|
| `pending` | 요약 대기 또는 재시도 대기 |
| `running` | 요약 처리 중 |
| `ready` | 요약 생성 완료 |
| `failed` | 재시도 후 최종 실패 |

### 4. 자연어 검색

검색은 먼저 로컬 DB에서 관련 법안을 찾고, 그 결과를 RAG context로 AI 설명을 생성합니다.

```text
사용자 자연어 질문
→ 개인정보 마스킹
→ 위험 질문 차단
→ 키워드/주제/단계/결과 조건 분석
→ 로컬 DB 법안 검색
→ 법안 카드 즉시 표시
→ AI 설명은 별도 요청으로 후속 표시
```

중요한 설계 원칙:

- 일반 검색 API는 OpenAPI나 Ollama를 호출하지 않습니다.
- DB에 없는 법안을 억지로 추천하지 않습니다.
- AI 설명은 검색된 법안 데이터만 근거로 작성합니다.
- 면책 문구는 AI 응답에 반복 삽입하지 않고 사이트 footer에서 공통 안내합니다.

예시 질문:

```text
내가 고등학생인데 나랑 관련된 법안이 있을까
조세 관련 법안 중에 이미 공포가 된 게 있어?
교통사고와 관련된 최신 법안이 뭐가 있을까?
```

### 5. Auth와 세션

커스텀 `Account` 모델을 사용합니다.

- 회원가입
- 로그인
- 로그아웃
- 현재 로그인 사용자 확인
- 공개 유저 정보 조회
- 비밀번호 규칙
  - 8자 이상
  - 영어 소문자 포함
  - 영어 대문자 포함
  - 숫자 포함
- 세션 유지 시간 1시간
- 페이지 이동 시 세션 갱신
- 만료된 세션으로 작성 기능 사용 시 재로그인 요청 후 새로고침

### 6. 포스트와 댓글

법안에 대해 시민 의견을 작성할 수 있습니다.

포스트:

- 법안 FK
- 작성자 FK
- 제목
- 내용
- 조회수
- 작성/수정 시각
- 작성자만 수정/삭제 가능

댓글:

- 포스트 FK
- 작성자 FK
- parent FK를 통한 대댓글
- 실제 삭제 대신 `is_deleted=True`
- 삭제된 댓글은 화면에 `삭제된 댓글입니다`로 표시
- 상위 댓글 삭제와 무관하게 대댓글 유지
- 댓글/대댓글 작성, 수정, 삭제
- 본인이 작성한 닉네임은 강조 색상 표시

### 7. 마이페이지

로그인 사용자는 마이페이지에서 자신의 활동을 확인할 수 있습니다.

- 내가 작성한 포스트
- 내가 작성한 댓글
- 사용자 닉네임 클릭 시 해당 사용자 페이지 이동
- 이동 시 열려 있던 모달 정리

### 8. 유사도 프로세서 확장

유사 법안 기능은 별도 processor로 추가할 수 있게 설계되어 있습니다.

기본 processor 구조:

```text
BillProcessor
├─ SummaryProcessor
└─ SimilarityProcessor(optional)
```

`SimilarityProcessor`는 기본 실행에는 포함하지 않습니다. 팀원이 유사도 provider를 완성하면 환경변수로 연결합니다.

```powershell
$env:BILL_PROCESSORS="bills.services.processors.SummaryProcessor,bills.services.processors.SimilarityProcessor"
$env:BILL_SIMILARITY_PROVIDER="your.module.find_similar_bills"
.\venv\Scripts\python.exe manage.py process_bill_tasks --processor similarity --limit 10 --until-empty
```

provider 예시:

```python
def find_similar_bills(bill):
    return [
        other_bill,
        {"title": "유사 법안명", "date": "2026.06.24", "stage": "위원회 심사"},
    ]
```

## 기술 스택

### Frontend

- Vue 3
- Vite
- Pinia
- Vue Router
- CSS modules 없이 전역 CSS 분리

### Backend

- Python 3.11
- Django 5
- Django REST Framework
- SQLite 개발 DB
- 열린국회정보 OpenAPI
- Ollama 로컬 LLM

### AI

- 배치 요약 모델: `OLLAMA_MODEL`
- 실시간 검색 설명 모델: `OLLAMA_REALTIME_MODEL`
- 기본 URL: `http://localhost:11434`

모델명은 환경변수로 변경합니다.

## 프로젝트 구조

```text
.
├─ backend/
│  ├─ accounts/            # Account, 로그인/회원가입/세션 API
│  ├─ bills/               # 법안 모델, 수집 파이프라인, 검색 API
│  ├─ chat/                # 자연어 질문 분석, 개인정보 마스킹
│  ├─ config/              # Django 설정
│  ├─ posts/               # 포스트/댓글 API
│  ├─ docs/                # 백엔드 문서
│  ├─ scripts/             # 작업 스케줄러 등록 스크립트
│  └─ manage.py
├─ frontend/
│  ├─ src/
│  │  ├─ components/       # 법안/포스트/모달 컴포넌트
│  │  ├─ stores/           # Pinia 상태 관리
│  │  ├─ views/            # 라우트 화면
│  │  └─ services/         # API client
│  ├─ styles/              # 화면별 CSS
│  └─ package.json
├─ docs/screenshots/       # README용 스크린샷
└─ README.md
```

## 로컬 실행

### 1. 백엔드 설치

```powershell
cd backend
.\venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
```

가상환경을 직접 실행하는 방식도 가능합니다.

```powershell
cd backend
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

### 2. 프론트엔드 설치

```powershell
cd frontend
npm install
npm run dev
```

브라우저에서 접속합니다.

```text
http://127.0.0.1:5173
```

### 3. Ollama 실행

요약과 AI 검색 설명을 사용하려면 Ollama가 필요합니다.

```powershell
ollama list
ollama serve
```

필요 시 모델을 내려받습니다.

```powershell
ollama pull gemma3:4b
```

## 주요 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `DJANGO_SECRET_KEY` | 개발 기본값 | Django secret key |
| `DJANGO_DEBUG` | `True` | 개발/운영 debug 설정 |
| `SESSION_COOKIE_AGE` | `3600` | 로그인 세션 유지 시간 |
| `ASSEMBLY_API_KEY` | 개발 설정값 | 열린국회정보 API key |
| `ASSEMBLY_API_BASE_URL` | `https://open.assembly.go.kr/portal/openapi` | 국회 OpenAPI base URL |
| `ASSEMBLY_SYNC_PAGES` | `10` | 기본 동기화 조회 페이지 수 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 URL |
| `OLLAMA_MODEL` | 설정값 | 배치 요약 모델 |
| `OLLAMA_REALTIME_MODEL` | 설정값 | 검색 설명 모델 |
| `OLLAMA_TIMEOUT` | `180` | Ollama timeout 초 |
| `BILL_PROCESSORS` | `SummaryProcessor` | 후처리 processor 목록 |
| `BILL_SIMILARITY_PROVIDER` | 빈 값 | 유사도 provider 경로 |

## 데이터 구축 절차

자세한 운영 절차는 [backend/docs/DB_DATA_BOOTSTRAP_GUIDE.md](backend/docs/DB_DATA_BOOTSTRAP_GUIDE.md)를 참고합니다.

### 초기 실제 법안 적재

```powershell
cd backend
.\venv\Scripts\python.exe manage.py sync_bills --target-count 300 --pages 50 --trigger manual
```

### 증분 동기화

```powershell
.\venv\Scripts\python.exe manage.py sync_bills --pages 10 --known-page-limit 2 --trigger scheduled
```

### 13시 보정 동기화

오전 신규 법안이 0건인 날만 실행합니다.

```powershell
.\venv\Scripts\python.exe manage.py sync_bills --pages 10 --trigger catchup --catch-up-only
```

### AI 작업 처리

```powershell
.\venv\Scripts\python.exe manage.py process_bill_tasks --limit 5 --until-empty --sleep-seconds 3
```

### 처리 현황 확인

```powershell
.\venv\Scripts\python.exe manage.py shell -c "from django.db.models import Count; from bills.models import Bill,BillSummary,BillProcessingTask,SyncRun; print('법안:',Bill.objects.count()); print('요약:',BillSummary.objects.count()); print('작업:',list(BillProcessingTask.objects.values('processor','status').annotate(count=Count('id')))); print('동기화:',SyncRun.objects.order_by('-started_at').values('status','trigger','fetched_count','created_count','updated_count','failed_count','error_message').first())"
```

## 자동화 운영 설계

로컬 개발 환경에서는 Windows 작업 스케줄러를 사용할 수 있습니다.

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\scripts\register_bill_tasks.ps1
```

등록 목표:

- 09:00~10:00 사이 10분 간격 법안 동기화
- 오전 신규 법안이 0건인 날 13:00 보정 조회
- AI worker 주기 실행
- 동일 작업 중복 실행 방지

AWS 배포 시에는 같은 명령을 다음 방식으로 옮길 수 있습니다.

- EventBridge Scheduler + ECS/Fargate task
- EC2 cron + systemd worker
- Django management command 기반 batch job
- Ollama 또는 별도 LLM 서버를 내부 네트워크에서 호출

## API 요약

### Accounts

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/auth/csrf` | CSRF 토큰 |
| `POST` | `/api/auth/login` | 로그인 |
| `POST` | `/api/auth/logout` | 로그아웃 |
| `GET` | `/api/auth/me` | 현재 계정 |
| `POST` | `/api/accounts` | 회원가입 |
| `GET` | `/api/users/:idx` | 공개 유저 정보 |

### Bills

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/categories` | 분야 목록과 전체 집계 |
| `GET` | `/api/home/picks` | 홈 추천 법안 |
| `GET` | `/api/bills` | 법안 목록, category/sort/page 지원 |
| `GET` | `/api/bills/:bill_id` | 법안 상세 |
| `GET` | `/api/sync/status` | 마지막 동기화 상태 |
| `POST` | `/api/search` | 로컬 DB 기반 자연어 검색 |
| `POST` | `/api/search/explain` | 검색 결과 기반 AI 설명 |

### Posts

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/posts` | 포스트 목록 |
| `POST` | `/api/posts` | 포스트 작성 |
| `GET` | `/api/posts/:idx` | 포스트 상세, 조회수 증가 |
| `PATCH` | `/api/posts/:idx` | 포스트 수정 |
| `DELETE` | `/api/posts/:idx` | 포스트 삭제 |
| `GET` | `/api/posts/:idx/comments` | 댓글 목록 |
| `POST` | `/api/posts/:idx/comments` | 댓글/대댓글 작성 |
| `PATCH` | `/api/comments/:idx` | 댓글 수정 |
| `DELETE` | `/api/comments/:idx` | 댓글 soft delete |
| `GET` | `/api/users/:idx/comments` | 유저 작성 댓글 |

### Chat

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/chat` | 자연어 법률/법안 질문 |
| `GET` | `/api/chat/history` | 세션 대화 이력 |

## 화면 구성

| Route | 화면 | 설명 |
|---|---|---|
| `#/` | Home | 검색창, 오늘 보기 좋은 법안 carousel |
| `#/latest` | 최신 법안 | 최신 발의안 목록, 더 보기와 scroll load |
| `#/weekly` | 인기 법안 | 조회수 기준 인기 법안 |
| `#/categories` | 분야별 | 분야 카드와 분야별 전체 법안 수 |
| `#/categories/:id` | 분야 상세 | 해당 분야 전체 법안과 단계 필터 |
| `#/posts` | 포스트 | 포스트 목록, 최신순/인기순 |
| `#/search?q=` | 검색 결과 | 자연어 검색 결과와 AI 설명 |
| `#/users/:idx` | 마이페이지 | 유저 포스트/댓글 활동 |
| Modal | 법안 상세 | 단계, 요약, 원문, 시민 의견 |
| Modal | 포스트 상세 | 본문, 댓글, 대댓글 |
| Modal | 포스트 작성 | 선택한 법안에 의견 작성 |

## 테스트와 검증

### 백엔드 전체 테스트

```powershell
cd backend
.\venv\Scripts\python.exe manage.py test --settings=config.settings
```

### 검색/파이프라인 핵심 테스트

```powershell
cd backend
.\venv\Scripts\python.exe manage.py test bills.test_pipeline.SearchResponseTests bills.test_pipeline.BillProcessingTests --settings=config.settings
```

### 프론트 빌드

```powershell
cd frontend
npm.cmd run build
```

최근 확인:

- Backend 전체 테스트: 65개 통과
- Search/Processor 테스트: 통과
- Frontend production build: 통과

## 발표 포인트

### 1. 화면 API와 외부 처리 분리

일반 사용자가 보는 API는 로컬 DB만 조회합니다. OpenAPI와 Ollama 호출은 동기화/worker 명령에서만 실행됩니다.

이 구조는 검색과 목록 화면의 응답 지연을 줄이고, AI 처리 실패가 서비스 전체 장애로 번지는 것을 막습니다.

### 2. 신규 법안 즉시 노출

신규 법안은 요약이 없어도 먼저 DB에 저장되고 화면에 표시됩니다. 요약은 `BillProcessingTask`로 따로 처리합니다.

### 3. 진행 단계 갱신

단순 최신 발의안만 보여주는 것이 아니라 위원회 심사, 본회의 상정, 통과/공포 및 폐기/철회 등의 결과까지 갱신할 수 있도록 설계했습니다.

### 4. 자연어 DB 검색

질문을 바로 LLM에 던지는 구조가 아니라, DB 법안을 먼저 검색한 뒤 해당 결과를 AI 설명의 근거로 사용합니다.

### 5. 시민 의견 연결

법안 상세 화면에서 시민 포스트를 바로 확인하고, 로그인 사용자는 해당 법안에 의견을 작성할 수 있습니다.

### 6. 확장 가능한 후처리

요약 processor와 유사도 processor가 같은 task worker 구조를 사용합니다. 팀원이 만든 embedding/유사도 기능을 별도 provider로 연결할 수 있습니다.

## 현재 한계와 향후 개선

- SQLite 개발 DB 기준이므로 운영 배포 시 PostgreSQL 전환 필요
- Ollama 로컬 모델 성능에 따라 요약 속도 편차 존재
- 유사 법안 검색은 provider 연결 전까지 제한적
- 인기 법안은 현재 조회수 기반이며, 실제 주간 집계를 위해서는 조회 이벤트 테이블 고도화 필요
- 카테고리 분류는 AI 요약 완료 후 더 정확해지므로 pending 법안은 임시 분류가 섞일 수 있음
- 운영 환경에서는 CORS, ALLOWED_HOSTS, SECRET_KEY, HTTPS cookie 설정을 반드시 강화해야 함

## Git 협업 규칙

브랜치 이름:

```text
feat/<scope>-<short-name>
fix/<scope>-<short-name>
docs/<scope>-<short-name>
refactor/<scope>-<short-name>
test/<scope>-<short-name>
```

커밋 메시지:

```text
feat: add bill stage filters
fix: prevent stale session writes
docs: update project presentation readme
test: add bill processing pipeline tests
```

PR에는 다음 내용을 포함합니다.

```text
## Summary
- 변경 요약

## Test
- 확인한 실행/테스트 방법

## Screenshots
- UI 변경 전/후
```

## 라이선스와 주의

슥법의 설명은 국회 발의안 데이터와 AI 요약에 기반한 참고 정보입니다. 구체적인 법률 자문을 대신하지 않습니다.

국회 OpenAPI 데이터는 공개 데이터를 활용하며, 운영 시 API 이용 조건과 호출 제한을 확인해야 합니다.

## 시연/배포 후보 상세 보고서

프로젝트 시연, 발표 자료 작성, AWS 배포 준비를 위한 상세 구현 설명은 [`docs/DEMO_RELEASE_REPORT.md`](docs/DEMO_RELEASE_REPORT.md)를 참고하세요.
