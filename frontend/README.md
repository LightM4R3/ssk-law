# SSK-Law Frontend

슥법 프론트엔드는 Vue 3 + Vite 기반 SPA입니다. Django REST API에서 법안, 검색, 포스트, 댓글, 인증 데이터를 받아 사용자가 법안을 빠르게 탐색하고 의견을 남길 수 있는 UI를 제공합니다.

## 주요 화면

| Route | 화면 | 설명 |
|---|---|---|
| `/` | Home | 검색창, 오늘 슥 보기 좋은 법안, 유사 법안 진입 |
| `/latest` | 최신 법안 | 최신 발의안 목록, 더 보기, scroll load |
| `/weekly` | 인기 법안 | 조회수 기반 인기 법안 랭킹 |
| `/categories` | 분야별 | 분야 카드와 분야별 전체 법안 수 |
| `/categories/:id` | 분야 상세 | 분야별 법안 목록, 단계 필터 |
| `/posts` | 포스트 | 법안별 시민 포스트 목록, 최신순/인기순 |
| `/search` | 검색 결과 | 자연어 검색 결과와 AI 검색 요약 |
| `/users/:idx` | 마이페이지 | 유저 포스트/댓글 활동 |
| `/login` | 로그인 | 세션 로그인 |
| `/signup` | 회원가입 | 비밀번호 정책 포함 |
| `/picks/:id/similar` | 유사 법안 | 홈 추천 법안 기준 유사 법안 목록 |

## 주요 UI 기능

- 법안 카드
- 법안 상세 모달
- 유사 법안 모달
- 포스트 상세 overlay
- 포스트 작성 모달
- 댓글/대댓글 tree
- 로그인 상태 표시와 로그아웃
- 마이페이지 포스트/댓글 탭
- 모바일 하단 navigation
- 상단 이동 버튼
- API 오류 공통 카드
- 서버 오류 재시도 버튼

## 설치와 실행

```powershell
cd frontend
npm install
npm run dev
```

기본 개발 서버:

```text
http://127.0.0.1:5173
```

## 빌드

```powershell
cd frontend
npm.cmd run build
```

빌드 결과는 `frontend/dist/`에 생성됩니다.

## API 연결

개발 중에는 Vite proxy가 `/api` 요청을 Django backend로 넘깁니다.

- 기본 proxy target: `http://127.0.0.1:8000`
- 변경 환경변수: `VITE_SSK_API_PROXY_TARGET`

예시:

```powershell
$env:VITE_SSK_API_PROXY_TARGET="http://127.0.0.1:8001"
npm run dev
```

배포 환경에서 API base URL을 직접 지정할 때:

```powershell
$env:VITE_SSK_API_BASE="https://api.example.com"
npm run build
```

API 호출은 `src/services/api.js`에 모여 있습니다.

## 프로젝트 구조

```text
frontend/
├─ index.html
├─ package.json
├─ vite.config.js
├─ src/
│  ├─ App.vue
│  ├─ main.js
│  ├─ assets/styles/index.css
│  ├─ components/
│  │  ├─ ApiStateCard.vue
│  │  ├─ AuthPasswordField.vue
│  │  ├─ BillCard.vue
│  │  ├─ BillModal.vue
│  │  ├─ HomeCarousel.vue
│  │  ├─ PostCard.vue
│  │  ├─ PostCommentItem.vue
│  │  ├─ PostCreateModal.vue
│  │  ├─ PostModal.vue
│  │  └─ SimilarBillModal.vue
│  ├─ data/
│  │  └─ display.js
│  ├─ router/
│  │  └─ index.js
│  ├─ services/
│  │  └─ api.js
│  ├─ stores/
│  │  ├─ app.js
│  │  └─ auth.js
│  └─ views/
│     ├─ HomeView.vue
│     ├─ LatestView.vue
│     ├─ WeeklyView.vue
│     ├─ CategoriesView.vue
│     ├─ CategoryDetailView.vue
│     ├─ PostsView.vue
│     ├─ SearchView.vue
│     ├─ SimilarView.vue
│     ├─ UserPageView.vue
│     ├─ LoginView.vue
│     └─ SignupView.vue
```

## 상태 관리

### `stores/auth.js`

- 현재 로그인 계정
- 로그인/로그아웃
- 회원가입
- CSRF token 준비
- 세션 만료 처리
- 로그인 필요 기능에서 재로그인 안내

### `stores/app.js`

- 법안 상세 모달
- 포스트 상세 모달
- 유사 법안 모달
- 포스트 작성 모달
- 모달 간 이동 상태
- 법안/포스트 생성 후 목록 갱신

## 주요 화면 동작

### Home

- 오늘 슥 보기 좋은 법안 노출
- 홈 추천 법안의 유사 법안 cache 활용
- 검색창 입력 후 `/search?q=`로 이동

### Search

- `POST /api/search`로 법안 카드 먼저 표시
- `POST /api/search/explain`으로 AI 설명 후속 표시
- 결과 없음/서버 오류/연결 대기 상태를 `ApiStateCard`로 표시

### Bill Modal

- 법안 기본 정보
- 단계 bar
- AI 3줄 요약
- 원문 보기
- 유사 법안 보기 lazy-load
- 시민들의 의견 목록
- 로그인 상태면 포스트 작성 버튼 표시

### Posts

- 10개 단위 pagination
- 최신순/인기순 정렬
- scroll 하단 접근 시 추가 load
- 포스트 클릭 시 overlay 상세
- 작성자 본인일 경우 수정/삭제 버튼

### Comments

- 댓글과 대댓글 tree 표시
- 로그인 상태에서 댓글/대댓글 작성
- 본인 댓글만 수정/삭제
- 삭제된 댓글은 서버 응답 기준으로 `삭제된 댓글입니다.` 표시
- 삭제된 댓글의 대댓글은 유지

### User Page

- 유저 닉네임 표시
- 작성한 포스트 목록
- 작성한 댓글 목록
- 닉네임 클릭 시 해당 유저 페이지로 이동

## Auth UX

- 로그인 성공 시 상단에 `{nickname}님` 표시
- 로그인 상태에서 마이페이지 버튼 표시
- 로그아웃 버튼은 상단에 유지
- 모바일에서는 주요 navigation을 하단 bar로 표시
- 세션 만료 상태에서 작성 기능 호출 시 재로그인 안내

## 반응형 UI

- 데스크톱: 상단 navigation
- 모바일: 하단 고정 navigation
- 긴 제목/본문은 모바일에서 말줄임 처리
- 법안/포스트 카드 폭은 화면 크기에 따라 유동적으로 배치

## 오류 처리

서버 traceback이나 HTML 오류는 사용자에게 그대로 보여주지 않습니다.

- 서버/API 오류: `다시 시도` 버튼 표시
- 프론트 렌더링/상태 오류: 새로고침 안내
- 검색 결과 없음: “검색 결과가 아직 없어요” 상태 카드

## 개발 참고

### dev server

```powershell
npm run dev
```

### production build

```powershell
npm.cmd run build
```

### preview

```powershell
npm run preview
```

## 배포 시 고려사항

- `VITE_SSK_API_BASE`를 운영 API 주소로 지정
- Django CORS origin에 프론트 배포 도메인 추가
- 정적 배포는 S3 + CloudFront 또는 Amplify 고려
- API 오류 메시지가 내부 stack trace를 노출하지 않는지 확인
- 모바일 하단 navigation과 modal z-index 재검증
