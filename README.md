# 슥법 SSK-Law

슥법(SSK-Law)은 국회에 매일 올라오는 법률안을 시민이 빠르게 이해하고, 자연어로 검색하고, 법안별 의견을 나눌 수 있게 만든 AI 기반 법안 큐레이션 서비스입니다.

법률안 원문은 길고 어렵고, 국회 의안의 처리 단계도 계속 바뀝니다. 슥법은 열린국회정보 OpenAPI에서 법안을 수집해 로컬 DB에 저장하고, AI 요약과 카테고리 분류를 후처리한 뒤, 화면 API는 로컬 DB를 우선 조회하도록 설계했습니다.

## 서비스 요약

```text
매일 올라오는 국회 법안을 슥 내려보며 이해하고, 묻고, 의견을 나눌 수 있게 만드는 서비스입니다.
```

## 핵심 기능

| 영역 | 내용 |
|---|---|
| 법안 탐색 | 최신 법안, 인기 법안, 분야별 법안, 단계별 필터 |
| 법안 상세 | AI 3줄 요약, 예상 영향, 현재 단계, 원문 링크, 시민 의견 |
| 자연어 검색 | 질문을 검색 전략으로 변환한 뒤 DB 법안을 관련도 순으로 반환 |
| AI 설명 | 검색된 법안만 context로 사용해 짧은 설명을 후속 생성 |
| 유사 법안 | 제목/요약/카테고리/위원회/처리 결과 기반 weighted cosine 추천 |
| 커뮤니티 | 법안별 포스트, 댓글, 대댓글, soft delete |
| Auth | 세션 기반 회원가입/로그인/로그아웃, 마이페이지 |
| 운영 준비 | 동기화 이력, AI 처리 task, 재시도, scheduler 명령 구조 |

## 서비스 흐름

```text
국회 OpenAPI
  -> sync_bills
  -> Bill / Category / SyncRun 저장
  -> BillProcessingTask(summary) 생성
  -> process_bill_tasks worker
  -> Ollama 요약
  -> BillSummary / category 갱신

Vue SPA
  -> Django REST API
  -> 로컬 DB 조회
  -> 법안 카드 / 상세 모달 / 포스트 / 댓글 렌더링

자연어 검색
  -> query router / rule fallback
  -> DB 점수 기반 검색
  -> 법안 카드 먼저 반환
  -> search/explain에서 AI 설명 후속 생성
```

## 기술 스택

### Backend

- Python 3.11
- Django 5
- Django REST Framework
- django-cors-headers
- SQLite 개발 DB
- 열린국회정보 OpenAPI
- Ollama

### Frontend

- Vue 3
- Vite
- Pinia
- Vue Router
- CSS 기반 반응형 UI

### AI 모델

- 배치 요약 기본 모델: `OLLAMA_MODEL=gemma4:e4b`
- 실시간 검색 설명/대화 기본 모델: `OLLAMA_REALTIME_MODEL=gemma3:4b`
- Ollama URL: `OLLAMA_BASE_URL=http://localhost:11434`

실시간 검색은 속도 문제 때문에 기본값을 `gemma3:4b`로 두고, 법안 요약 batch는 `gemma4:e4b`를 사용합니다.

## 프로젝트 구조

```text
.
├─ backend/
│  ├─ accounts/       # Account, 세션 인증, 회원가입/로그인 API
│  ├─ bills/          # 법안 모델, OpenAPI 수집, 검색, 유사도, processor
│  ├─ chat/           # 자연어 대화와 개인정보 마스킹
│  ├─ config/         # Django 설정과 예외 처리
│  ├─ posts/          # 법안별 포스트/댓글 API
│  ├─ docs/           # 백엔드 API/DB/데이터 구축 문서
│  ├─ fixtures/       # 기본 법안 fixture
│  ├─ scripts/        # Windows scheduler 등록 스크립트
│  └─ manage.py
├─ frontend/
│  ├─ src/
│  │  ├─ components/  # 법안/포스트/모달 컴포넌트
│  │  ├─ views/       # Home, Latest, Categories, Posts, Search, User pages
│  │  ├─ stores/      # Pinia auth/app state
│  │  ├─ services/    # API client
│  │  └─ router/      # Vue Router
│  └─ package.json
└─ README.md
```

## 로컬 실행

### 1. 백엔드

```powershell
cd backend
.\venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

가상환경을 활성화하지 않고 직접 실행할 수도 있습니다.

```powershell
cd backend
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

### 2. 프론트엔드

```powershell
cd frontend
npm install
npm run dev
```

기본 접속 주소:

```text
http://127.0.0.1:5173
```

### 3. Ollama

```powershell
ollama serve
ollama pull gemma4:e4b
ollama pull gemma3:4b
```

## 주요 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `DJANGO_DEBUG` | `True` | Django debug mode |
| `DJANGO_SECRET_KEY` | 개발 기본값 | 운영에서는 반드시 외부 secret 사용 |
| `SESSION_COOKIE_AGE` | `3600` | 로그인 세션 유지 시간 |
| `ASSEMBLY_API_KEY` | 개발 키 | 열린국회정보 API key |
| `ASSEMBLY_API_BASE_URL` | `https://open.assembly.go.kr/portal/openapi` | OpenAPI base URL |
| `ASSEMBLY_SYNC_PAGES` | `10` | 기본 수집 페이지 수 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 URL |
| `OLLAMA_MODEL` | `gemma4:e4b` | 배치 요약 모델 |
| `OLLAMA_REALTIME_MODEL` | `gemma3:4b` | 검색 설명/대화 모델 |
| `OLLAMA_TIMEOUT` | `180` | 요약/대화 timeout |
| `OLLAMA_ANALYSIS_TIMEOUT` | `2` | 검색 전략 분석 timeout |
| `OLLAMA_KEEP_ALIVE` | `30m` | Ollama model keep-alive |

## 데이터 구축

### 실제 법안 대량 적재

```powershell
cd backend
.\venv\Scripts\python.exe manage.py sync_bills --target-count 300 --pages 50 --trigger manual
```

### 증분 동기화

```powershell
.\venv\Scripts\python.exe manage.py sync_bills --pages 10 --known-page-limit 2 --trigger scheduled
```

### AI 요약 worker

```powershell
.\venv\Scripts\python.exe manage.py process_bill_tasks --limit 5 --until-empty --sleep-seconds 3
```

### 누락된 요약 작업 생성

```powershell
.\venv\Scripts\python.exe manage.py enqueue_bill_processing --processor summary
```

### 개발용 커뮤니티 더미 데이터

기존 계정, 포스트, 댓글을 정리하고 개발 확인용 사용자 10명, 포스트 20개, 댓글/대댓글 50개를 생성합니다.

```powershell
.\venv\Scripts\python.exe manage.py seed_demo_community
```

기본 비밀번호:

```text
DemoPass123
```

## 동기화와 후처리 설계

`sync_bills`는 OpenAPI 데이터를 수집하고, `BillProcessingTask`를 생성합니다. `process_bill_tasks`는 task를 처리하며, 실패 시 재시도 상태와 오류를 남깁니다.

`SyncRun`은 한 번의 동기화 실행을 기록합니다.

- 실행 유형: `manual`, `scheduled`, `catchup`
- 상태: `running`, `success`, `no_changes`, `partial`, `failed`, `skipped`
- 조회/신규/갱신/실패 건수
- 오류 메시지
- 중복 실행 방지 constraint

운영 스케줄 예시:

- 09:00~10:00 사이 10분 간격 동기화
- 오전 신규 법안이 0건인 날 13:00 보정 동기화
- AI worker 별도 주기 실행

Windows scheduler 등록 스크립트:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\scripts\register_bill_tasks.ps1
```

## 검색과 유사도

### 자연어 검색

검색은 LLM 답변을 기다린 뒤 결과를 보여주는 구조가 아닙니다.

1. 사용자 질문을 분석한다.
2. 단순 질의는 규칙 기반 분석을 사용한다.
3. 복합 질의는 LLM query router가 검색 전략 JSON을 만든다.
4. 실패하거나 느리면 규칙 기반 fallback을 사용한다.
5. DB에서 제목, 카테고리, 요약, 위원회, 처리 결과를 점수화한다.
6. 법안 카드를 먼저 반환한다.
7. `search/explain`이 검색된 법안을 context로 짧은 설명을 만든다.

### 유사 법안

현재 유사 법안은 런타임 SBERT 모델이 아니라 `report_weighted_v1` 로컬 fallback입니다.

- `title`: 0.30
- `full`: 0.10
- `current`: 0.15
- `problem`: 0.15
- `proposal`: 0.15
- `article`: 0.15
- category overlap bonus
- committee bonus

결과는 `SimilarBill`에 cache합니다. 메인 추천 법안 5개는 홈 로드 시 cache를 보장하고, 일반 법안은 사용자가 `유사 법안 보기`를 누를 때 lazy-load합니다.

## 삭제 댓글 정책

댓글은 대댓글 구조 유지를 위해 row를 hard delete하지 않습니다. 대신 삭제 시 서버에서 다음 처리를 합니다.

- `is_deleted=True`
- `content="삭제된 댓글입니다."`로 치환
- 삭제된 댓글은 수정/삭제 추가 요청 차단
- serializer에서도 삭제 댓글 content를 다시 마스킹

따라서 API를 직접 호출해도 삭제 전 원문 댓글은 노출되지 않습니다.

## 주요 API

### Accounts

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/auth/csrf` | CSRF 토큰 |
| `POST` | `/api/auth/login` | 로그인 |
| `POST` | `/api/auth/logout` | 로그아웃 |
| `GET` | `/api/auth/me` | 현재 로그인 계정 |
| `POST` | `/api/accounts` | 회원가입 |
| `GET` | `/api/users/:idx` | 공개 유저 정보 |

### Bills

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/categories` | 분야 목록과 집계 |
| `GET` | `/api/home/picks` | 홈 추천 법안 |
| `GET` | `/api/bills` | 법안 목록 |
| `GET` | `/api/bills/:bill_id` | 법안 상세 |
| `GET` | `/api/bills/:bill_id/similar` | 유사 법안 lazy-load |
| `GET` | `/api/sync/status` | 동기화 상태 |
| `POST` | `/api/search` | 자연어 DB 검색 |
| `POST` | `/api/search/explain` | 검색 결과 기반 AI 설명 |

### Posts

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/posts` | 포스트 목록 |
| `POST` | `/api/posts` | 포스트 작성 |
| `GET` | `/api/posts/:idx` | 포스트 상세 |
| `PATCH` | `/api/posts/:idx` | 포스트 수정 |
| `DELETE` | `/api/posts/:idx` | 포스트 삭제 |
| `GET` | `/api/posts/:idx/comments` | 댓글/대댓글 목록 |
| `POST` | `/api/posts/:idx/comments` | 댓글/대댓글 작성 |
| `PATCH` | `/api/comments/:idx` | 댓글 수정 |
| `DELETE` | `/api/comments/:idx` | 댓글 soft delete |
| `GET` | `/api/users/:idx/comments` | 유저 댓글 목록 |

## 테스트

### 백엔드

```powershell
cd backend
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test
```

### 프론트엔드

```powershell
cd frontend
npm.cmd run build
```

## 상세 문서

- [DB 데이터 구축 가이드](backend/docs/DB_DATA_BOOTSTRAP_GUIDE.md)
- [API 명세](backend/docs/API_SPEC.md)
- [DB 명세](backend/docs/DATABASE_SPEC.md)

## 현재 한계와 향후 계획

- 로컬 SQLite 기준이므로 운영 배포 시 PostgreSQL 전환 필요
- Ollama 로컬 모델 성능에 따라 요약/설명 속도 편차 존재
- 유사 법안은 현재 weighted cosine fallback이며, 향후 SBERT/pooled scorer 연결 예정
- 원문 raw content 저장과 chunking 기반 조문 RAG는 추후 작업
- 인기 법안은 현재 조회수 기반이며, 실제 주간 인기 집계에는 조회 이벤트 테이블 필요
- AWS 배포 시 `DEBUG=False`, `ALLOWED_HOSTS`, CORS, secure cookie, secret 관리 강화 필요

## 라이선스와 주의

슥법의 설명은 국회 발의안 데이터와 AI 요약에 기반한 참고 정보입니다. 구체적인 법률 자문을 대신하지 않습니다.

국회 OpenAPI 데이터는 공개 데이터를 활용하며, 운영 시 API 이용 조건과 호출 제한을 확인해야 합니다.
