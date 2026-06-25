# SSK-Law 시연 및 배포 후보 보고서

작성일: 2026-06-25  
대상 브랜치: `main`  
목적: 프로젝트 시연, 발표 자료 작성, 이후 AWS 배포 준비를 위한 구현 정리

## 1. 프로젝트 목표

SSK-Law, 서비스명 `슥법`은 국회에 매일 추가되는 법안을 시민이 빠르게 이해하고 탐색할 수 있도록 만든 법안 큐레이션 서비스다. 법률 원문은 길고 어렵고, 의안의 처리 단계도 계속 변한다. 이 프로젝트는 다음 문제를 해결하는 방향으로 설계되었다.

- 최신 발의안을 자동 수집하고 로컬 DB에 저장한다.
- 법안 원문과 의안 정보를 시민 친화적인 3줄 요약과 분야로 바꾼다.
- 화면 API는 외부 OpenAPI나 LLM에 직접 의존하지 않고 로컬 DB만 조회한다.
- 사용자는 자연어로 질문하고, 시스템은 DB의 법안들을 근거로 관련 법안을 먼저 보여준다.
- 법안별 시민 의견을 포스트와 댓글로 연결해 단순 조회 서비스가 아니라 의견 탐색 서비스로 확장한다.
- 유사 법안 추천을 통해 하나의 법안을 더 넓은 입법 흐름 안에서 볼 수 있게 한다.

초기 Notion 기획에서는 Phase 1 MVP 이후 Fine-tuning과 RAG를 순차적으로 진행하는 구성이었다. 최종 구현은 일정과 팀 리소스 상황에 맞춰 Fine-tuning 대신 로컬 RAG형 검색, 프롬프트 기반 LLM 활용, 규칙/가중치 기반 유사도 추천을 중심으로 재구성되었다.

## 2. 전체 아키텍처

서비스는 크게 네 흐름으로 나뉜다.

```text
국회 OpenAPI
  -> sync_bills 관리 명령
  -> BillSyncService / AssemblyOpenApiClient
  -> Bill / BillCategory / SyncRun 저장
  -> BillProcessingTask 생성
  -> process_bill_tasks worker
  -> SummaryProcessor
  -> Ollama
  -> BillSummary / category 갱신

Vue 프론트엔드
  -> Django REST API
  -> 로컬 DB 조회
  -> 카드, 상세 모달, 검색 결과, 포스트, 댓글 렌더링

자연어 검색
  -> query router / rewriter
  -> 규칙 또는 LLM 검색 전략 생성
  -> DB 점수 기반 검색
  -> 법안 카드 즉시 반환
  -> 별도 explain API로 짧은 RAG 설명 생성

유사 법안 추천
  -> SimilarBill cache 조회
  -> 없으면 report_weighted_v1 로컬 유사도 계산
  -> SimilarBill 저장
  -> target_bill 기반으로 실제 법안 상세 모달 연결
```

핵심 설계 원칙은 화면용 API와 외부 API/AI 처리를 분리하는 것이다. 최신 법안 목록, 상세, 분야별 페이지, 포스트 목록, 댓글 조회는 모두 로컬 DB만 조회한다. 외부 OpenAPI 호출과 Ollama 호출은 수집/후처리 worker 또는 검색 설명 API에 한정된다.

## 3. 백엔드 도입 기능

### 3.1 법안 자동 수집 파이프라인

법안 수집은 관리 명령 `sync_bills`에서 시작한다. 명령은 서비스 계층을 호출하고, 실제 OpenAPI 요청과 DB 저장은 `bills/services/assembly.py`의 수집 로직이 담당한다.

주요 동작은 다음과 같다.

1. 국회 OpenAPI를 페이지 단위로 조회한다.
2. `bill_id`를 기준으로 이미 존재하는 법안인지 확인한다.
3. 신규 법안이면 `Bill`로 저장하고 위원회 기반 임시 카테고리를 부여한다.
4. 신규 법안에 대해 `BillProcessingTask(processor="summary")`를 생성한다.
5. 기존 법안이면 제목, 위원회, 처리 결과, 단계 같은 변경 가능한 정보를 갱신한다.
6. 처리 단계가 더 낮은 단계로 후퇴하지 않도록 단계 갱신 정책을 적용한다.
7. 실행 내역은 `SyncRun`에 저장한다.

`SyncRun`은 한 번의 동기화 실행을 기록하는 모델이다. 실행 유형(`manual`, `scheduled`, `catchup`), 상태(`running`, `success`, `partial`, `failed`, `skipped`), 시작/종료 시각, 조회/신규/갱신/실패 건수, 오류 메시지를 저장한다. 또한 `running` 상태에 대한 unique constraint를 둬 같은 동기화 명령이 중복 실행되는 것을 DB 수준에서도 막는다.

### 3.2 법안 단계 갱신

법안 단계는 화면에서 다음 4단계로 표현한다.

```text
발의 -> 위원회 심사 -> 본회의 상정 -> 통과·공포
```

OpenAPI 원문에는 단계와 처리 결과가 API별로 다르게 들어온다. 이 프로젝트에서는 화면의 단계 표시와 실제 처리 결과를 분리했다.

- `Bill.stage`: 화면용 큰 단계
- `Bill.result_status`: 통과, 철회, 폐기, 부결, 대안반영폐기 등 정규화된 처리 결과
- `Bill.result_text`: OpenAPI에서 받은 사람이 읽을 수 있는 처리 결과 텍스트

이렇게 나눈 이유는 “폐기”, “철회”, “대안반영폐기” 같은 상태가 단순히 4단계 중 어디인지로만 표현되면 정보가 손실되기 때문이다. 시연 UI에서는 단계 바를 간단히 유지하면서도, 상세 화면이나 내부 검색에서는 처리 결과를 별도 필드로 활용할 수 있다.

### 3.3 AI 후처리 작업

법안은 수집 즉시 화면에 노출된다. 요약이 없다는 이유로 법안 자체를 숨기지 않는다. 대신 `BillProcessingTask`가 별도 후처리 상태를 관리한다.

`BillProcessingTask`는 다음 정보를 가진다.

- 대상 법안
- processor 종류
- processor version
- 상태: `pending`, `running`, `retry`, `succeeded`, `failed`
- 시도 횟수와 최대 시도 횟수
- 다음 실행 시각
- 마지막 오류
- 시작/종료 시각

요약 worker는 `process_bill_tasks` 명령으로 실행한다. worker는 due 상태의 작업을 제한된 개수만 직렬로 처리한다. 실패하면 1분, 5분, 30분 간격으로 재시도하고, 최대 시도 이후에는 `failed` 상태와 오류를 남긴다. 이 구조 덕분에 법안 수집과 AI 요약 실패가 서로 영향을 주지 않는다.

### 3.4 Processor 확장 구조

processor는 `key`, 의존 processor, `process(bill)` 인터페이스를 갖도록 설계했다. 현재 핵심 processor는 `summary`이고, 향후 유사도/임베딩 processor를 독립적으로 붙일 수 있다.

예상 확장 예시는 다음과 같다.

```text
summary processor
  -> BillSummary 생성
  -> category 갱신

similarity processor
  -> summary 완료 후 실행
  -> embedding 또는 SBERT score 계산
  -> SimilarBill 또는 별도 벡터 테이블 저장

law-article processor
  -> 상세 원문 저장
  -> 조문 단위 chunk 생성
  -> RAG 검색용 index 구성
```

이 방식의 장점은 요약 실패, 유사도 실패, 조문 index 실패를 서로 분리할 수 있다는 점이다. 특히 유사도 processor가 실패해도 법안 수집과 법안 노출, 요약 결과에는 영향을 주지 않는다.

## 4. LLM 사용 방식과 프롬프팅

현재 AI 제공자는 로컬 Ollama다. 설정은 환경변수로 바꿀 수 있다.

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_REALTIME_MODEL`
- `OLLAMA_TIMEOUT`
- `OLLAMA_ANALYSIS_TIMEOUT`
- `OLLAMA_KEEP_ALIVE`

### 4.1 요약 프롬프트

요약은 법안 제목, 대표 발의자, 위원회, OpenAPI 상세 내용을 입력으로 받아 다음 JSON만 반환하도록 요구한다.

```json
{
  "summary_1": "첫 번째 요약 문장",
  "summary_2": "두 번째 요약 문장",
  "summary_3": "세 번째 요약 문장",
  "impact": "예상 영향",
  "categories": ["category_slug"]
}
```

프롬프트의 핵심은 다음이다.

- 시민이 이해할 수 있는 쉬운 문장
- 3줄 요약 형식 준수
- 정해진 카테고리 slug 중 1~2개만 선택
- JSON 외 텍스트 금지
- 낮은 temperature로 일관성 유지

요약 결과는 `BillSummary`에 저장되고, category는 `BillCategory`로 갱신된다. 이 결과는 이후 목록/상세/검색/유사도 계산의 기반이 된다.

### 4.2 자연어 검색 Query Router

초기 검색은 사용자의 입력 토큰을 단순 키워드로 펼쳐 OR 검색하는 구조에 가까웠다. “기후” 같은 짧은 단어에는 반응하지만 “기후 관련 법의안”처럼 표현이 바뀌거나, “청년 벤처기업 사장인데 농수산업 회사와 계약했고 기후 피해가 있었다”처럼 여러 주제가 섞이면 검색 품질이 급격히 떨어졌다.

현재 구조는 검색 전에 입력을 검색 전략으로 바꾼다.

단순 질의는 규칙 기반으로 처리한다.

- 짧은 주제어
- 명확한 분야명
- 법안명 일부
- 단계/처리 상태 질의

복잡한 질의는 Ollama의 `analyze_user_query()`를 호출해 JSON 전략을 만든다.

```json
{
  "intent": "bill_search | legal_question | chitchat | nonsense | unsafe | too_broad | mixed",
  "summary": "검색 관점의 한 문장 요약",
  "search_query": "DB 검색용 짧은 검색문",
  "must_have": ["반드시 맞아야 하는 축"],
  "nice_to_have": ["있으면 좋은 보조 축"],
  "exclude": ["제외할 주제"],
  "keywords": ["검색용 핵심 명사"],
  "risk_level": "High | Medium | Low",
  "confidence": 0.0,
  "clarification_needed": false,
  "clarification_question": ""
}
```

`OLLAMA_ANALYSIS_TIMEOUT` 기본값은 2초다. LLM이 늦거나 실패하면 규칙 기반 fallback이 동작한다. 이 fallback은 사용자 입력에서 주제 축을 찾아 `mustHave`, `niceToHave`, `exclude`로 승격한다. 예를 들어 농수산업, 기업 지원, 기후 피해가 함께 들어오면 단순 OR 검색이 아니라 “기후 피해와 농수산업 또는 기업 지원 축을 우선하는 검색”으로 바뀐다.

### 4.3 검색 결과 점수화

검색 후보는 먼저 DB 필터로 최대 250개 정도만 가져온다. 이후 Python에서 점수화한다.

점수 기준은 다음과 같다.

- `mustHave` 조건이 맞으면 큰 가중치
- `mustHave`가 제목에 있으면 추가 점수
- `mustHave`가 카테고리에 있으면 추가 점수
- `mustHave`가 요약에 있으면 추가 점수
- `niceToHave`는 제목, 카테고리, 요약, 기타 필드 순으로 가중치
- keyword는 제목, 카테고리, 요약, 위원회/처리 결과 순으로 가중치
- 주제 synonym이 맞으면 보너스
- 요약이 준비된 법안이면 소폭 보너스
- exclude 조건에 걸리면 제외

`mustHave`가 3개 이상이면 최소 2개 축은 맞아야 결과로 인정한다. 이 덕분에 여러 주제가 섞인 질문에서 한 단어만 맞는 엉뚱한 법안이 상단에 뜨는 현상을 줄인다.

### 4.4 검색 설명 RAG

검색 API는 법안 카드를 먼저 반환한다. AI 설명은 별도 `search/explain` API에서 생성한다. 이 구조는 성능과 UX를 위해 중요하다.

- 사용자는 먼저 관련 법안 목록을 본다.
- LLM 설명이 늦어도 목록은 이미 표시된다.
- 설명은 이미 선택된 DB 법안 context만 근거로 한다.

프롬프트는 다음을 강하게 요구한다.

- 하단 카드 제목을 단순 반복하지 않는다.
- “현재 DB 기준입니다” 같은 불필요한 문장을 쓰지 않는다.
- 면책 문구는 footer에 있으므로 AI 답변에는 넣지 않는다.
- markdown, 목록, 이모지, 인사말을 쓰지 않는다.
- 2~3개의 짧은 문장으로 줄바꿈한다.
- 질문과 법안들이 어떤 정책 방향으로 이어지는지 설명한다.

후처리 함수는 markdown 기호, 링크 문법, 코드블록, 과도한 공백, 금지 문구를 제거한다. 결과가 길면 문장 단위로 잘라 UI에서 끊겨 보이지 않게 한다.

## 5. 유사도 검출

### 5.1 현재 구현 배경

파트너가 진행한 SBERT/pooled scorer와 평가 데이터셋이 있었지만, 시연 시점에는 런타임에 붙일 scorer 파일과 embedding 파이프라인이 준비되지 않았다. 그래서 현재 서비스에는 `report_weighted_v1`이라는 로컬 fallback 유사도 방식을 구현했다.

이 방식은 발표 보고서에서 언급된 `final_ensemble_title_heavy_balanced`, `weighted_field_title_sbert_balanced` 계열 아이디어를 런타임 가능한 형태로 근사한 것이다. 즉, SBERT 벡터 대신 DB에 이미 있는 제목, 요약, 카테고리, 위원회, 처리 결과를 토큰 벡터로 만들고 weighted cosine score를 계산한다.

### 5.2 field 구성

한 법안은 여러 field vector로 나뉜다.

- `title`: 법안 제목
- `current`: 위원회, 카테고리, 현재 단계, 처리 결과
- `problem`: 3줄 요약 중 첫 번째 문장
- `proposal`: 3줄 요약 중 두 번째/세 번째 문장
- `article`: 영향 설명과 처리 결과
- `full`: 위 field 전체를 합친 텍스트

현재 DB에는 상세 원문 전체가 별도 저장되어 있지 않다. SummaryProcessor가 OpenAPI 상세 내용을 가져오지만, 지금은 요약 생성에 사용하고 버리는 구조다. 따라서 `article` field는 실제 조문 전문이 아니라 `impact`와 `result_text`를 사용한다. 향후 정확도를 높이려면 원문 raw content를 저장하는 `BillRawContent` 또는 `BillTextChunk` 계층을 추가하는 것이 맞다.

### 5.3 가중치

현재 field weight는 다음과 같다.

```text
title    0.30
full     0.10
current  0.15
problem  0.15
proposal 0.15
article  0.15
```

추가 보너스는 다음과 같다.

```text
category overlap bonus 0.06
extra category bonus   0.02
committee bonus        0.04
```

최종 점수는 field별 cosine similarity의 weighted sum에 category/committee 보너스를 더한 값이다. 1.0을 넘으면 1.0으로 clamp한다. 이후 점수와 발의일을 기준으로 정렬하고 상위 5개를 저장한다.

### 5.4 cache 전략

유사도 계산은 매번 즉시 모든 법안을 비교하면 무거워진다. 따라서 `SimilarBill` 테이블에 source bill, target bill, score, rank, method를 저장한다.

- 메인 페이지의 “오늘 슥 보기 좋은 법안” 5개는 로드 시 유사 법안을 미리 계산한다.
- 일반 법안 상세 모달에서는 “유사 법안 보기” 버튼을 눌렀을 때 lazy-load한다.
- 이미 cache가 있으면 DB에서 바로 반환한다.
- `refresh=true`를 줄 때만 재계산한다.

이 구조는 시연 UX와 서버 부하 사이의 타협이다. 메인 5개에는 추천을 바로 보여주고, 전체 법안에 대해서는 사용자가 명시적으로 요청한 경우에만 계산한다.

### 5.5 향후 SBERT/pooled scorer 연결 방식

파트너 scorer가 준비되면 현재 `build_keyword_similarities()`를 교체하거나, provider interface를 추가하면 된다.

권장 구조는 다음과 같다.

```text
SimilarityProvider
  - key
  - version
  - score(source_bill, candidate_bills)

KeywordWeightedProvider(report_weighted_v1)
SBERTPooledProvider(partner_sbert_v1)
HybridProvider(weighted_title_sbert_bm25_v1)
```

운영 DB에서는 `SimilarBill.method`와 `processor_version`을 함께 저장해 어떤 알고리즘으로 계산된 결과인지 추적해야 한다. 평가 지표는 P@5, P@10, nDCG@10, MRR을 사용할 수 있지만, 이 지표들은 사람이 라벨링한 정답 쌍이 있을 때만 의미가 있다. 현재 받은 500쌍 라벨 데이터와 LLM 확장 xlsx는 오프라인 가중치 탐색에는 사용할 수 있으나, 런타임 품질을 보장하려면 사람이 검수한 validation split을 따로 유지하는 것이 좋다.

## 6. API 동작 방식

### 6.1 법안 API

일반 법안 API는 로컬 DB만 조회한다.

- 최신 법안
- 인기 법안
- 분야별 법안
- 법안 상세
- 홈 추천
- 유사 법안
- 동기화 상태

목록 응답에는 요약 상태가 포함된다. 요약이 없으면 “요약 준비 중” 상태로 처리하고, 요약이 완료된 법안은 목록에서 더 높은 우선순위를 받을 수 있다.

### 6.2 검색 API

검색은 두 단계다.

1. `POST /api/search`: DB 검색과 법안 목록 즉시 반환
2. `POST /api/search/explain`: 이미 찾은 법안들을 context로 짧은 AI 설명 반환

검색 결과가 없거나 질문이 너무 불명확하면 “검색 결과 없음” 또는 “질문을 조금 더 구체화해 달라”는 상태를 반환한다. 서버 오류가 HTML traceback으로 노출되지 않도록 프론트에서는 `ApiStateCard`로 오류를 감싸고, 서버 오류는 “다시 시도” 버튼, 프론트 렌더링 오류는 “새로고침” 버튼으로 안내한다.

### 6.3 포스트/댓글 API

포스트는 법안에 연결되는 시민 의견 단위다.

- `Post`: title, content, user, bill, created_at, updated_at, view_count
- `Comment`: post, parent, user, content, created_at, updated_at, view_count, is_deleted

정책은 다음과 같다.

- Read는 비로그인 가능
- Create/Update/Delete는 로그인 세션 필요
- Update/Delete는 작성자 본인만 가능
- 포스트 상세 조회 시 view_count 증가
- 같은 session의 반복 조회는 일정 시간 동안 view_count 중복 증가 방지
- 댓글 삭제는 실제 삭제가 아니라 `is_deleted=True` soft delete
- 상위 댓글이 삭제되어도 대댓글은 유지

목록 API는 10개 단위 pagination을 지원하고, 포스트 정렬은 최신순과 인기순을 제공한다. 인기순은 현재 view_count 기준이다.

### 6.4 Auth/session

현재 인증은 Django session 기반이다.

- 로그인 성공 시 session key rotation
- `SESSION_COOKIE_AGE=3600`
- `SESSION_SAVE_EVERY_REQUEST=True`
- 페이지 이동 또는 API 요청이 있으면 session 만료 시간이 갱신된다.
- 세션이 만료된 상태에서 댓글 작성, 포스트 작성 같은 보호 기능을 호출하면 재로그인을 안내하고 refresh하도록 프론트에서 처리한다.

비밀번호 정책은 회원가입 시 8글자 이상, 영어 소문자, 대문자, 숫자를 모두 포함하도록 검증한다.

## 7. 프론트엔드 구현 방향

프론트엔드는 Vue 3, Vite, Pinia 기반 SPA다.

주요 화면은 다음과 같다.

- 홈: 오늘 슥 보기 좋은 법안, 메인 검색, 유사 법안 진입
- 최신 법안: 최신순 법안 목록과 pagination/더 보기
- 인기 법안: 조회수 기반 랭킹
- 분야별: 분야 카드, 분야 상세, 단계별 필터
- 검색 결과: DB 검색 결과와 AI 검색 요약
- 포스트: 포스트 목록, 상세 overlay, 댓글/대댓글
- 마이페이지: 내 포스트, 내 댓글
- 로그인/회원가입

모달 구조는 법안 상세, 포스트 상세, 포스트 작성, 유사 법안 상세가 서로 겹치는 경우를 고려해 store에서 열림 상태를 관리한다. 예를 들어 포스트 상세에서 법안명을 누르면 법안 모달이 뜨고, 닫으면 기존 포스트 모달로 돌아올 수 있게 처리했다.

모바일 UI에서는 상단 nav가 두 줄로 늘어나는 문제를 해결하기 위해 하단 고정 nav bar를 적용했다. 각 메뉴에는 아이콘과 선택 highlight를 넣어 모바일 앱처럼 탐색할 수 있게 했다.

성능 문제를 줄이기 위해 다음 조치를 반영했다.

- 커스텀 scrollbar 제거
- 유사 법안은 전체 자동 계산이 아니라 lazy-load
- 포스트/댓글 list는 pagination과 필요한 시점 로딩
- 에러 화면은 raw traceback 대신 공통 카드로 표시
- 상단 이동 버튼을 고정 overlay로 제공

## 8. Notion WBS 대비 실제 진행

Notion의 초기 문서는 프로젝트를 다음 Phase로 잡고 있었다.

- Phase 1: 최신 발의안 목록/상세, 3줄 요약, 자연어 검색 v0, 안전장치, 기본 화면 연결
- Phase 2: Fine-tuning을 통한 질문 분석, 요약, 태깅 품질 개선
- Phase 3: RAG를 통한 유사 발의안 검색, 조문 기반 검색 고도화
- 초기 MVP에서는 Auth, 회원가입, 로그인 기반 마이페이지가 제외 또는 Stretch로 이동

실제 진행은 다음처럼 바뀌었다.

| 구분 | Notion WBS | 실제 구현 |
|---|---|---|
| Auth | MVP 제외 또는 Stretch | 세션 기반 로그인, 회원가입, 로그아웃, 마이페이지까지 구현 |
| 관심 법안 | 저장 기능 중심 | 별도 관심 저장보다 포스트/댓글 커뮤니티 흐름으로 확장 |
| 자연어 검색 | Phase 1 v0, 이후 Fine-tuning | 규칙 + LLM query router + DB scoring + RAG 설명으로 구현 |
| Fine-tuning | W4~W6 핵심 과제 | 일정상 직접 모델 튜닝은 보류, 프롬프트/RAG/fallback 개선으로 대체 |
| RAG | W7 구현 예정 | DB 법안 context 기반 검색 설명, 유사 법안 추천 일부 구현 |
| 유사 법안 | embedding/pgvector/SBERT 계획 | 현재는 report_weighted_v1 로컬 weighted cosine fallback |
| 조문 기반 검색 | Phase 3 확장 | 아직 미구현, 향후 raw content/chunk 저장 필요 |
| 배포 | 최종 정리 단계 | 로컬 시연 기준 완료, AWS 배포 계획 문서화 |
| 커뮤니티 | 초기 핵심 범위 아님 | Post/Comment CRUD, overlay, 마이페이지 연동까지 구현 |

Fine-tuning이 보류된 이유는 모델 학습 자체보다도 “학습 데이터, 평가 기준, 런타임 scorer 연결, 배포 사양”이 함께 준비되어야 했기 때문이다. 팀원이 IR 평가와 NLP 실험 자동화를 진행했고 500쌍 라벨 및 LLM 확장 데이터셋은 확보했지만, 서비스 런타임에 바로 연결 가능한 SBERT/pooled scorer가 시연 시점에 없었다. 그래서 현 버전은 Fine-tuning 모델을 직접 탑재하지 않고, 다음 전략으로 현실적인 MVP 품질을 끌어올렸다.

- 질문을 바로 검색하지 않고 검색 전략 JSON으로 변환
- LLM 실패 시 규칙 기반 fallback
- DB 법안 context만 사용하는 RAG식 설명
- 유사도 추천은 cache 가능한 로컬 weighted cosine으로 대체
- 추후 scorer 교체를 위해 `method`, `score`, `rank`, `target_bill` 구조 유지

즉, 계획의 방향은 유지하되 구현 우선순위는 “발표 가능한 동작 서비스”에 맞춰 바뀌었다.

## 9. 로컬 실행 및 테스트

### 9.1 백엔드

```bash
cd backend
venv\Scripts\activate
python manage.py migrate
python manage.py runserver
```

### 9.2 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

### 9.3 Ollama

```bash
ollama serve
ollama pull gemma3:4b
```

환경변수 예시:

```bash
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=gemma4:e4b
set OLLAMA_REALTIME_MODEL=gemma3:4b
set OLLAMA_ANALYSIS_TIMEOUT=2
```

### 9.4 데이터 갱신

최신 법안 동기화:

```bash
python manage.py sync_bills --pages 10 --trigger manual
```

초기 대량 데이터 확보:

```bash
python manage.py sync_bills --target-count 300 --pages 50 --trigger manual
```

요약 worker:

```bash
python manage.py process_bill_tasks --limit 5 --stop-when-empty
```

요약 작업 누락분 생성:

```bash
python manage.py enqueue_bill_processing --processor summary
```

### 9.5 검증 명령

```bash
cd backend
python manage.py check
python manage.py test bills.test_pipeline.SearchResponseTests

cd ../frontend
npm run build
```

## 10. AWS 배포 예정안

현재는 로컬 시연 기준이지만, AWS 배포 시 다음 구성이 적합하다.

### 10.1 기본 인프라

- Django API: EC2 + gunicorn + nginx 또는 ECS Fargate
- DB: Amazon RDS PostgreSQL
- 정적 파일: S3 + CloudFront
- 프론트엔드: S3/CloudFront 또는 Amplify
- Secret 관리: AWS SSM Parameter Store 또는 Secrets Manager
- 로그: CloudWatch Logs
- 도메인/HTTPS: Route53 + ACM

### 10.2 환경 설정

운영에서는 다음을 반드시 바꾼다.

- `DEBUG=False`
- `ALLOWED_HOSTS` 제한
- `CORS_ALLOWED_ORIGINS` 제한
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECRET_KEY` 외부 secret 관리
- 국회 OpenAPI key 외부 secret 관리
- SQLite 대신 PostgreSQL 사용

### 10.3 Scheduler/worker

현재 로컬에서는 OS scheduler나 수동 명령으로 실행한다. AWS에서는 다음 중 하나를 선택한다.

1. EventBridge Scheduler -> ECS one-off task
2. EC2 cron/systemd timer -> Django management command
3. Celery Beat + Celery Worker + Redis/SQS

권장 운영 구조는 다음이다.

```text
EventBridge
  -> sync_bills task
  -> 신규 BillProcessingTask 생성

Worker service
  -> process_bill_tasks 반복 실행
  -> summary / similarity processor 처리
```

Ollama는 별도 EC2 인스턴스에 올릴 수 있지만, CPU only 환경에서는 응답 지연이 크다. 운영에서는 GPU 인스턴스, 더 작은 모델, 또는 외부 LLM API 전환을 검토해야 한다. 비용과 성능을 고려하면 검색 목록은 DB에서 즉시 반환하고, LLM은 요약 worker와 설명 생성에만 제한하는 현재 구조를 유지하는 것이 좋다.

### 10.4 향후 성능 개선

- SimilarBill cache 사전 생성 batch
- PostgreSQL full-text search 또는 trigram index
- pgvector 기반 embedding 검색
- Redis cache
- Celery/SQS 기반 worker 안정화
- 원문 chunk 저장 후 조문/제안이유 RAG
- CloudWatch metric 기반 실패 알림

## 11. 현재 한계와 다음 작업

현재 시연 버전의 한계는 명확하다.

- Fine-tuned model은 아직 런타임에 붙어 있지 않다.
- 유사도는 SBERT가 아니라 로컬 weighted cosine fallback이다.
- 법안 상세 raw content가 DB에 저장되지 않아 조문/원문 기반 RAG가 제한된다.
- 요약 worker는 로컬 명령 기반이라 운영용 queue/worker 구성이 필요하다.
- 인기 법안은 실제 주간 집계가 아니라 현재 view_count 기반 성격이 강하다.
- 법안 단계는 4단계 UI와 별도 result status를 함께 쓰지만, 더 세밀한 국회 절차 표현은 추후 확장 여지가 있다.

우선순위 높은 다음 작업은 다음이다.

1. 원문 상세 content 저장 모델 추가
2. partner SBERT/pooled scorer provider 연결
3. SimilarBill 사전 계산 batch 추가
4. PostgreSQL 전환 및 검색 index 구성
5. AWS worker/scheduler 구성
6. 주간 인기 집계용 view event 테이블 추가
7. 라벨 데이터셋 기반 유사도 회귀 평가 자동화

## 12. 시연 흐름

권장 시연 순서는 다음이다.

1. 홈 화면에서 오늘 추천 법안 확인
2. 법안 상세 모달 열기
3. 단계 바, 3줄 요약, 원문 보기 확인
4. 유사 법안 보기 클릭
5. 유사 법안 상세 모달 확인
6. 자연어 검색 입력
7. 법안 카드가 먼저 뜨고 AI 설명이 후속으로 뜨는 흐름 확인
8. 분야별 페이지에서 단계 필터 확인
9. 포스트 페이지에서 포스트 상세/댓글/대댓글 확인
10. 로그인 후 포스트 작성, 댓글 작성, 마이페이지 확인
11. `/api/sync/status` 또는 관리 명령 결과로 데이터 갱신 구조 설명

이 시연은 “법안 수집 -> AI 요약 -> DB 검색 -> 유사도 추천 -> 시민 의견”의 전체 흐름을 하나로 보여준다.
