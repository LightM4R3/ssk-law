# 슥법 (SSK-Law) — API 명세서

> **버전**: v1.0-MVP  
> **최종 수정**: 2026-05-19  
> **Base URL**: `http://localhost:8000`  
> **프레임워크**: Django 5.x + Django REST Framework 3.x

---

## 목차

1. [공통 사항](#1-공통-사항)
2. [법안 API](#2-법안-api)
3. [AI 챗봇 API](#3-ai-챗봇-api)
4. [관리 API (내부용)](#4-관리-api-내부용)
5. [에러 응답](#5-에러-응답)
6. [프론트엔드 연동 가이드](#6-프론트엔드-연동-가이드)

---

## 1. 공통 사항

### 1.1 Base URL

```
개발: http://localhost:8000
프론트엔드: window.SSK_API_BASE = "http://localhost:8000"
```

### 1.2 Content-Type

- 요청: `application/json`
- 응답: `application/json`

### 1.3 CORS

프론트엔드(`http://localhost:5173`)에서의 요청을 허용합니다.

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

### 1.4 인증

MVP 단계에서는 인증 없이 모든 API를 공개합니다. 챗봇의 세션 식별은 `session_key` 파라미터로 처리합니다.

### 1.5 공통 응답 형식

모든 응답은 아래 형식을 따릅니다.

**성공 (리스트)**:
```json
{
  "<resource_name>": [ ... ]
}
```

**성공 (단건)**:
```json
{
  "id": "...",
  "title": "...",
  ...
}
```

**에러**:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "해당 법안을 찾을 수 없습니다."
  }
}
```

### 1.6 페이지네이션

법안 목록 API는 커서 기반 페이지네이션을 지원합니다.

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `page` | int | 1 | 페이지 번호 |
| `page_size` | int | 20 | 페이지당 법안 수 (최대 100) |

응답에 `pagination` 필드가 포함됩니다:

```json
{
  "bills": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 142,
    "total_pages": 8
  }
}
```

---

## 2. 법안 API

### 2.1 `GET /api/categories` — 분야 목록

프론트엔드 필터 탭에 사용되는 분야별 법안 개수를 반환합니다.

**요청**: 파라미터 없음

**응답 `200 OK`**:
```json
{
  "categories": [
    { "id": "all", "label": "전체", "count": 142 },
    { "id": "labor", "label": "노동", "count": 18 },
    { "id": "welfare", "label": "복지", "count": 24 },
    { "id": "housing", "label": "주거", "count": 12 },
    { "id": "economy", "label": "경제", "count": 21 },
    { "id": "education", "label": "교육", "count": 11 },
    { "id": "env", "label": "환경 · 기후", "count": 9 },
    { "id": "digital", "label": "디지털", "count": 14 },
    { "id": "health", "label": "보건", "count": 13 },
    { "id": "safety", "label": "생활안전", "count": 8 }
  ]
}
```

**구현 노트**:
- `count`는 해당 분야에 속하는 법안의 실시간 집계 (`annotate(Count)`)
- `all`의 count는 전체 법안 수

---

### 2.2 `GET /api/home/picks` — 홈 추천 법안 (캐러셀)

홈 화면 캐러셀에 노출되는 에디터 추천 5개 법안을 반환합니다.

**요청**: 파라미터 없음

**응답 `200 OK`**:
```json
{
  "picks": [
    {
      "id": "PRC_Z2Z1...",
      "title": "플랫폼 노동자에게도 유급 휴가와 산재보험을.",
      "categories": [
        { "id": "labor", "label": "노동" },
        { "id": "welfare", "label": "복지" }
      ],
      "proposedAt": "2026.04.28",
      "proposer": "김○○ 의원 외 12인",
      "stage": "committee",
      "summary": [
        "배달·대리·가사 등 플랫폼을 통해 일하는 노동자에게도 4대 보험과 유급 휴가를 단계적으로 보장합니다.",
        "주 15시간 이상 일한 경우 연 5일의 유급 휴가를 도입합니다.",
        "플랫폼 기업은 노동자 보호 알고리즘 운영 지침을 매년 공시합니다."
      ],
      "sentiment": 68,
      "comments": 1284,
      "impact": "약 80만 명의 플랫폼 노동자에게 직접 영향. 휴식권·의료 안전망 확대.",
      "similar": [
        {
          "title": "특수형태근로종사자 권익 보호법 일부개정안",
          "date": "2026.03.11",
          "stage": "위원회"
        }
      ]
    }
  ]
}
```

**구현 노트**:
- MVP에서는 조회수 상위 5개 법안 또는 최근 동기화된 법안 중 AI 요약이 완료된 법안을 자동 선택
- 향후 에디터 수동 큐레이션 기능 추가 가능

---

### 2.3 `GET /api/bills` — 최신 법안 목록

최신 법안 페이지에 사용되는 법안 리스트를 반환합니다.

**요청 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `category` | string | `all` | 분야 slug 필터 (예: `labor`, `housing`) |
| `sort` | string | `-proposed_at` | 정렬 기준 (`-proposed_at`: 최신순, `-view_count`: 조회수순) |
| `page` | int | 1 | 페이지 번호 |
| `page_size` | int | 20 | 페이지당 건수 |

**응답 `200 OK`**:
```json
{
  "bills": [
    {
      "id": "PRC_Z2Z1...",
      "title": "청년 월세 지원 한도를 30만 원으로.",
      "categories": [
        { "id": "housing", "label": "주거" }
      ],
      "proposedAt": "2026.05.07",
      "proposer": "박○○ 의원 외 9인",
      "stage": "proposed",
      "summary": ["요약 1", "요약 2"],
      "sentiment": 74,
      "comments": 892,
      "impact": "지원 대상 약 13만 명 확대 예상."
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 142,
    "total_pages": 8
  }
}
```

**구현 노트**:
- 기본 정렬: `proposed_at DESC` (최신순)
- `category=all`일 때 전체 법안 반환
- `summary`, `sentiment`, `impact`는 `BillSummary` JOIN

---

### 2.4 `GET /api/bills/{bill_id}` — 법안 상세

모달에서 사용하는 법안 상세 정보를 반환합니다.

**Path 파라미터**:

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `bill_id` | string | 법안 식별자 (국회 BILL_ID 또는 내부 ID) |

**응답 `200 OK`**:
```json
{
  "id": "PRC_Z2Z1...",
  "billNo": "2113663",
  "title": "플랫폼 노동자에게도 유급 휴가와 산재보험을.",
  "categories": [
    { "id": "labor", "label": "노동" },
    { "id": "welfare", "label": "복지" }
  ],
  "proposedAt": "2026.04.28",
  "proposer": "김○○ 의원 외 12인",
  "committee": "환경노동위원회",
  "stage": "committee",
  "detailLink": "https://likms.assembly.go.kr/bill/...",
  "summary": [
    "배달·대리·가사 등 플랫폼을 통해 일하는 노동자에게도 4대 보험과 유급 휴가를 단계적으로 보장합니다.",
    "주 15시간 이상 일한 경우 연 5일의 유급 휴가를 도입합니다.",
    "플랫폼 기업은 노동자 보호 알고리즘 운영 지침을 매년 공시합니다."
  ],
  "sentiment": 68,
  "comments": 1284,
  "impact": "약 80만 명의 플랫폼 노동자에게 직접 영향. 휴식권·의료 안전망 확대.",
  "similar": [
    {
      "title": "특수형태근로종사자 권익 보호법 일부개정안",
      "date": "2026.03.11",
      "stage": "위원회"
    },
    {
      "title": "프리랜서 표준계약 의무화법",
      "date": "2026.02.04",
      "stage": "본회의"
    }
  ],
  "viewCount": 128400,
  "syncedAt": "2026-05-19T12:00:00Z"
}
```

**에러 `404 Not Found`**:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "해당 법안을 찾을 수 없습니다."
  }
}
```

---

### 2.5 `POST /api/search` — 자연어 검색 (AI)

사용자의 자연어 질문을 AI가 분석하여 관련 법안을 검색하고 친근한 답변을 생성합니다.

**요청 Body**:
```json
{
  "query": "청년 월세와 관련된 법안은 뭐가 있어?"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `query` | string | ✅ | 자연어 검색 질문 (1~500자) |

**응답 `200 OK`**:
```json
{
  "intro": "청년 월세 관련 법안 3건을 슥 찾아봤어! 월세 지원 한도를 올리는 법안이 가장 주목받고 있어.",
  "ids": ["PRC_Z2Z1...", "PRC_A1B2...", "PRC_C3D4..."],
  "bills": [
    {
      "id": "PRC_Z2Z1...",
      "title": "청년 월세 지원 한도를 30만 원으로.",
      "categories": [{ "id": "housing", "label": "주거" }],
      "proposedAt": "2026.05.07",
      "proposer": "박○○ 의원 외 9인",
      "stage": "proposed",
      "summary": ["요약 1", "요약 2"],
      "sentiment": 74,
      "comments": 892,
      "impact": "지원 대상 약 13만 명 확대 예상."
    }
  ]
}
```

**구현 노트**:
- AI(Ollama)에게 법안 목록 컨텍스트와 사용자 질문을 전달
- AI가 관련 법안 ID를 선별하고 친근한 답변 생성
- AI 호출 실패 시 키워드 기반 폴백 검색 수행
- 응답의 `bills`에는 선별된 법안의 상세 정보를 포함하여 프론트엔드 추가 요청을 최소화

**에러 `400 Bad Request`**:
```json
{
  "error": {
    "code": "INVALID_QUERY",
    "message": "검색어를 입력해 주세요."
  }
}
```

---

## 3. AI 챗봇 API

### 3.1 `POST /api/chat` — 챗봇 메시지 전송

법률 관련 질문에 AI가 답변하는 챗봇 API입니다. 대화 히스토리를 세션 단위로 관리합니다.

**요청 Body**:
```json
{
  "session_key": "550e8400-e29b-41d4-a716-446655440000",
  "message": "플랫폼 노동자 보호법이 통과되면 배달 기사에게 어떤 변화가 있어?"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `session_key` | string | ❌ | 세션 식별 UUID (미전송 시 새 세션 생성) |
| `message` | string | ✅ | 사용자 질문 (1~1000자) |

**응답 `200 OK`**:
```json
{
  "session_key": "550e8400-e29b-41d4-a716-446655440000",
  "reply": "플랫폼 노동자 보호법이 통과되면 배달 기사에게 큰 변화가 생길 수 있어! 크게 세 가지를 정리해볼게.\n\n1. **4대 보험 적용**: 고용보험, 산재보험 등 4대 보험에 가입할 수 있어서 사고 시 보상을 받을 수 있어.\n2. **유급 휴가**: 주 15시간 이상 일하면 연 5일의 유급 휴가가 생겨.\n3. **알고리즘 투명성**: 배달 배정이나 평가 방식에 대해 플랫폼 기업이 투명하게 공개해야 해.\n\n현재 위원회 심사 단계에 있고, 약 80만 명의 플랫폼 노동자에게 영향이 예상돼.",
  "related_bills": [
    {
      "id": "PRC_Z2Z1...",
      "title": "플랫폼 노동자에게도 유급 휴가와 산재보험을."
    }
  ]
}
```

| 응답 필드 | 타입 | 설명 |
|-----------|------|------|
| `session_key` | string | 세션 키 (새 세션 생성 시 이 값을 클라이언트에서 저장) |
| `reply` | string | AI 답변 (마크다운 포맷 가능) |
| `related_bills` | array | 답변에 언급된 관련 법안 목록 |

**구현 노트**:
- `session_key` 미전송 시 새 UUID를 생성하여 `ChatSession` 레코드 생성
- 동일 세션의 최근 10개 메시지를 AI 컨텍스트에 포함 (대화 히스토리)
- 관련 법안 DB 데이터를 AI 프롬프트에 주입하여 정확한 정보 기반 답변 생성
- AI 호출 실패 시 안내 메시지 반환

**에러 `400 Bad Request`**:
```json
{
  "error": {
    "code": "INVALID_MESSAGE",
    "message": "질문을 입력해 주세요."
  }
}
```

### 3.2 `GET /api/chat/history` — 대화 내역 조회

세션의 대화 내역을 조회합니다.

**요청 파라미터**:

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `session_key` | string | ✅ | 세션 식별 UUID |

**응답 `200 OK`**:
```json
{
  "session_key": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "role": "user",
      "content": "플랫폼 노동자 보호법이 뭐야?",
      "created_at": "2026-05-19T12:00:00Z"
    },
    {
      "role": "assistant",
      "content": "플랫폼 노동자 보호법은...",
      "related_bills": [
        { "id": "PRC_Z2Z1...", "title": "플랫폼 노동자에게도 유급 휴가와 산재보험을." }
      ],
      "created_at": "2026-05-19T12:00:05Z"
    }
  ]
}
```

---

## 4. 관리 API (내부용)

### 4.1 `POST /api/admin/sync-bills` — 법안 수동 동기화

> 이 API는 개발/운영 시 수동 트리거용입니다. 운영에서는 Django Management Command 또는 Celery 스케줄러로 자동 실행합니다.

**요청 Body** (선택):
```json
{
  "age": 22,
  "page_size": 100
}
```

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `age` | int | 22 | 국회 대수 |
| `page_size` | int | 100 | 한 번에 가져올 건수 |

**응답 `200 OK`**:
```json
{
  "synced": 47,
  "created": 12,
  "updated": 35,
  "summarized": 12,
  "errors": []
}
```

---

## 5. 에러 응답

### 5.1 에러 코드 일람

| HTTP 상태 | code | 설명 |
|-----------|------|------|
| `400` | `INVALID_QUERY` | 검색어 누락 또는 유효하지 않은 질문 |
| `400` | `INVALID_MESSAGE` | 챗봇 메시지 누락 |
| `400` | `INVALID_PARAM` | 잘못된 파라미터 |
| `404` | `NOT_FOUND` | 리소스를 찾을 수 없음 |
| `500` | `INTERNAL_ERROR` | 서버 내부 오류 |
| `503` | `AI_UNAVAILABLE` | AI 모델(Ollama) 연결 실패 |

### 5.2 에러 응답 형식

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "사용자에게 보여줄 수 있는 한국어 메시지"
  }
}
```

---

## 6. 프론트엔드 연동 가이드

### 6.1 응답 필드 매핑

프론트엔드 `api.js`의 정규화 함수가 다양한 필드명을 수용하도록 설계되어 있습니다. 아래는 백엔드 응답 필드와 프론트엔드 내부 필드의 대응표입니다.

| 백엔드 응답 필드 | 프론트엔드 내부 필드 | 설명 |
|-----------------|---------------------|------|
| `id` | `id` | 법안 식별자 |
| `title` | `title` | 법안명 |
| `categories` | `cats` | 분야 목록 (`normalizeCat` 처리) |
| `categories[].id` | `cats[].k` | 분야 slug |
| `categories[].label` | `cats[].label` | 분야 표시명 |
| `proposedAt` | `proposedAt` | 발의일 (형식: `YYYY.MM.DD`) |
| `proposer` | `proposer` | 대표발의자 |
| `stage` | `stage` | 진행 단계 (`normalizeStage` 처리) |
| `summary` | `summary` | 요약 배열 |
| `sentiment` | `sentiment` | 긍정 지표 |
| `comments` | `comments` | 댓글 수 |
| `impact` | `impact` | 예상 영향 |
| `similar` | `similar` | 유사 법안 배열 |

### 6.2 Stage 값

백엔드에서 반환하는 `stage` 값:

| 값 | 프론트엔드 표시 |
|----|---------------|
| `proposed` | 발의 |
| `committee` | 위원회 심사 |
| `plenary` | 본회의 상정 |
| `passed` | 통과 · 공포 |

### 6.3 날짜 형식

- 프론트엔드 표시용: `YYYY.MM.DD` (예: `2026.05.07`)
- API 직렬화: `proposedAt` 필드에 `YYYY.MM.DD` 형식 사용 (프론트엔드 호환)

### 6.4 프론트엔드 설정 예시

```html
<script>
  window.SSK_API_BASE = "http://localhost:8000";
</script>
```

---

## API 엔드포인트 요약

| Method | Endpoint | 설명 | 프론트엔드 매핑 |
|--------|----------|------|----------------|
| `GET` | `/api/categories` | 분야 목록 | `API_ENDPOINTS.categories` |
| `GET` | `/api/home/picks` | 홈 추천 법안 | `API_ENDPOINTS.picks` |
| `GET` | `/api/bills` | 최신 법안 목록 | `API_ENDPOINTS.bills` |
| `GET` | `/api/bills/{bill_id}` | 법안 상세 | `fetchJson` 직접 호출 |
| `POST` | `/api/search` | 자연어 검색 | `search.js → nlSearch` |
| `POST` | `/api/chat` | 챗봇 메시지 | 신규 챗봇 UI |
| `GET` | `/api/chat/history` | 대화 내역 | 신규 챗봇 UI |
| `POST` | `/api/admin/sync-bills` | 법안 동기화 (내부) | 관리자 전용 |

---

## Django 앱 구조 (권장)

```text
backend/
├── config/              # Django 프로젝트 설정
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── bills/               # 법안 관련 앱
│   ├── models.py        # Category, Bill, BillCategory, BillSummary, SimilarBill, WeeklyRanking
│   ├── serializers.py   # DRF Serializers
│   ├── views.py         # API Views
│   ├── urls.py          # 법안 URL 라우팅
│   └── management/
│       └── commands/
│           └── sync_bills.py   # 국회 API 동기화 커맨드
├── chat/                # AI 챗봇 앱
│   ├── models.py        # ChatSession, ChatMessage
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── services/            # 외부 서비스 연동
│   ├── assembly_api.py  # 열린국회정보 API 클라이언트
│   └── ollama.py        # Ollama AI 클라이언트
├── manage.py
└── requirements.txt
```

---

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DJANGO_SECRET_KEY` | (개발용 자동 생성) | Django SECRET_KEY |
| `DJANGO_DEBUG` | `True` | 디버그 모드 |
| `ASSEMBLY_API_KEY` | - | 열린국회정보 API 인증키 |
| `ASSEMBLY_API_BASE_URL` | `https://open.assembly.go.kr/portal/openapi` | 국회 API 베이스 URL |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | 사용 모델명 |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | 데이터베이스 연결 문자열 |
