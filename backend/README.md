# SSK-Law Backend

슥법 백엔드는 Django REST Framework 기반 API 서버입니다. 열린국회정보 OpenAPI에서 법안을 수집하고, AI 요약 작업을 비동기 task로 분리하며, 프론트엔드에는 로컬 DB 기반 API를 제공합니다.

## 핵심 역할

- 국회 OpenAPI 법안 수집
- 법안 단계와 처리 결과 갱신
- 동기화 실행 이력 기록
- AI 요약/카테고리 후처리 task 관리
- 자연어 검색과 검색 설명 API
- 유사 법안 cache/lazy-load API
- 세션 기반 Auth
- 법안별 포스트/댓글 API
- 개발용 샘플 커뮤니티 데이터 생성

## 요구사항

- Python 3.11 이상
- SQLite 개발 DB
- Ollama
  - 요약 모델: `gemma4:e4b`
  - 실시간 검색/대화 모델: `gemma3:4b`
- 열린국회정보 OpenAPI key

## 설치

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
```

가상환경이 이미 있다면:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py migrate
```

## 실행

```powershell
cd backend
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `DJANGO_DEBUG` | `True` | 개발 debug mode |
| `DJANGO_SECRET_KEY` | 개발 기본값 | 운영 secret key |
| `SESSION_COOKIE_AGE` | `3600` | 세션 유지 시간 |
| `ASSEMBLY_API_KEY` | 개발 키 | 열린국회정보 API key |
| `ASSEMBLY_API_BASE_URL` | `https://open.assembly.go.kr/portal/openapi` | OpenAPI base |
| `ASSEMBLY_SYNC_PAGES` | `10` | 기본 조회 페이지 수 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 |
| `OLLAMA_MODEL` | `gemma4:e4b` | 배치 요약 모델 |
| `OLLAMA_REALTIME_MODEL` | `gemma3:4b` | 검색 설명/대화 모델 |
| `OLLAMA_TIMEOUT` | `180` | LLM timeout |
| `OLLAMA_ANALYSIS_TIMEOUT` | `2` | 검색 전략 분석 timeout |
| `OLLAMA_KEEP_ALIVE` | `30m` | Ollama model keep-alive |
| `BILL_PROCESSORS` | `bills.services.processors.SummaryProcessor` | 후처리 processor 목록 |
| `BILL_SIMILARITY_PROVIDER` | 빈 값 | 외부 유사도 provider 경로 |

## 앱 구성

```text
backend/
├─ accounts/     # Account 모델, 세션 인증, 회원가입/로그인/유저 API
├─ bills/        # Bill 모델, 법안 수집, 검색, 유사도, processor
├─ chat/         # 대화형 질문 API, 개인정보 마스킹
├─ config/       # Django 설정, URL, 예외 처리
├─ posts/        # Post/Comment 모델과 CRUD API
├─ services/     # Ollama client
├─ docs/         # API/DB/데이터 구축 문서
├─ fixtures/     # 기본 법안 fixture
├─ scripts/      # Windows 작업 스케줄러 등록 스크립트
└─ manage.py
```

## 데이터 모델 요약

### Bills

- `Bill`: 법안 기본 정보, 단계, 처리 결과, 조회수
- `Category`: 분야
- `BillCategory`: 법안-분야 연결
- `BillSummary`: AI 3줄 요약과 영향
- `SimilarBill`: 유사 법안 cache
- `SyncRun`: 동기화 실행 이력
- `BillProcessingTask`: 요약/유사도 등 후처리 작업

### Accounts

- `Account`: 커스텀 계정 모델
- Django session 기반 인증
- 로그인 성공 시 session key rotation
- 세션 유지 시간 1시간

### Posts

- `Post`: 법안에 연결되는 시민 의견
- `Comment`: 댓글/대댓글
- 댓글 삭제 시 row는 유지하지만 `content`를 서버에서 삭제 문구로 치환하고 `is_deleted=True`로 저장

## 법안 수집

### 대량 초기 적재

```powershell
.\venv\Scripts\python.exe manage.py sync_bills --target-count 300 --pages 50 --trigger manual
```

### 증분 동기화

```powershell
.\venv\Scripts\python.exe manage.py sync_bills --pages 10 --known-page-limit 2 --trigger scheduled
```

### 13시 보정 동기화

오전 신규 법안 합계가 0건인 날만 실행합니다.

```powershell
.\venv\Scripts\python.exe manage.py sync_bills --pages 10 --trigger catchup --catch-up-only
```

## AI 후처리

법안은 수집 즉시 화면에 노출됩니다. 요약은 별도 task로 처리합니다.

```powershell
# 대기 중인 task 처리
.\venv\Scripts\python.exe manage.py process_bill_tasks --limit 5 --until-empty --sleep-seconds 3

# 기존 법안에 요약 task 생성
.\venv\Scripts\python.exe manage.py enqueue_bill_processing --processor summary
```

처리 실패 시 `BillProcessingTask`에 오류와 다음 실행 시각을 기록합니다. 기본 재시도 간격은 1분, 5분, 30분입니다.

## 개발용 샘플 데이터

기존 계정/포스트/댓글을 정리하고 개발 확인용 샘플 커뮤니티 데이터를 생성합니다.

```powershell
.\venv\Scripts\python.exe manage.py seed_demo_community
```

생성 내용:

- 계정 10개
- 포스트 20개
- 댓글/대댓글 50개
- 실제 요약된 법안에 연결
- 사용자별 말투와 관심사가 다른 더미 문장

기본 비밀번호:

```text
DemoPass123
```

## 자동화 스케줄

Windows 작업 스케줄러 등록:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\scripts\register_bill_tasks.ps1
```

목표 운영 흐름:

- 09:00~10:00 10분 간격 동기화
- 오전 신규 법안이 0건이면 13:00 보정 동기화
- AI worker 별도 주기 실행
- DB의 `SyncRun`과 OS scheduler로 중복 실행 방지

Linux cron 예시:

```cron
0,10,20,30,40,50 9 * * * /srv/ssk-law/backend/venv/bin/python /srv/ssk-law/backend/manage.py sync_bills --trigger scheduled
0 13 * * * /srv/ssk-law/backend/venv/bin/python /srv/ssk-law/backend/manage.py sync_bills --trigger catchup --catch-up-only
* * * * * /srv/ssk-law/backend/venv/bin/python /srv/ssk-law/backend/manage.py process_bill_tasks --limit 1
```

## 자연어 검색 구조

`POST /api/search`는 검색 결과를 빠르게 보여주기 위해 OpenAPI와 Ollama를 직접 기다리지 않습니다.

1. 사용자 질문 마스킹
2. 규칙 기반 query 분석
3. 복합 질문은 LLM query router 호출
4. LLM 실패/timeout 시 rules fallback
5. must/nice/exclude/keywords 기반 DB 점수화
6. 관련 법안 반환

`POST /api/search/explain`은 이미 반환된 법안들을 context로 사용해 짧은 설명을 생성합니다.

## 유사 법안 구조

현재 기본 유사도 방식은 `report_weighted_v1`입니다.

- SBERT 런타임 scorer가 붙기 전까지 사용하는 fallback
- 제목, 요약, 카테고리, 위원회, 처리 결과를 field vector로 구성
- weighted cosine + category/committee bonus
- `SimilarBill`에 method, rank, score, target_bill 저장

관련 API:

```text
GET /api/bills/:bill_id/similar
```

## API 요약

### Auth

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
| `GET` | `/api/categories` | 분야 목록 |
| `GET` | `/api/home/picks` | 홈 추천 |
| `GET` | `/api/bills` | 법안 목록 |
| `GET` | `/api/bills/:bill_id` | 법안 상세 |
| `GET` | `/api/bills/:bill_id/similar` | 유사 법안 |
| `GET` | `/api/sync/status` | 동기화 상태 |
| `POST` | `/api/search` | 자연어 검색 |
| `POST` | `/api/search/explain` | 검색 설명 |

### Posts

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/posts` | 목록, `page`, `sort`, `billId`, `userId` 지원 |
| `POST` | `/api/posts` | 작성 |
| `GET` | `/api/posts/:idx` | 상세, 조회수 증가 |
| `PATCH` | `/api/posts/:idx` | 수정 |
| `DELETE` | `/api/posts/:idx` | 삭제 |
| `GET` | `/api/posts/:idx/comments` | 댓글 tree |
| `POST` | `/api/posts/:idx/comments` | 댓글/대댓글 작성 |
| `GET` | `/api/comments/:idx` | 댓글 상세 |
| `PATCH` | `/api/comments/:idx` | 댓글 수정 |
| `DELETE` | `/api/comments/:idx` | 댓글 soft delete |
| `GET` | `/api/users/:idx/comments` | 유저 댓글 |

## 테스트

```powershell
cd backend
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test
```

특정 테스트:

```powershell
.\venv\Scripts\python.exe manage.py test posts
.\venv\Scripts\python.exe manage.py test bills.test_pipeline.SearchResponseTests
```

## 운영 배포 시 변경할 것

- SQLite -> PostgreSQL
- `DJANGO_DEBUG=False`
- `ALLOWED_HOSTS` 제한
- CORS origin 제한
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- secret key와 API key를 SSM/Secrets Manager로 분리
- scheduler를 EventBridge, ECS task, Celery/SQS 등으로 이전
- Ollama는 GPU 인스턴스 또는 외부 LLM API 전환 검토

## 참고 문서

- `backend/docs/API_SPEC.md`
- `backend/docs/DATABASE_SPEC.md`
- `backend/docs/DB_DATA_BOOTSTRAP_GUIDE.md`
