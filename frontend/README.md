# 슥법(SSK-Law) Frontend

Vue 3 + Vite 기반 프론트엔드입니다. `App onboarding_0527.zip`의 최신 정적 UI를 Vue 컴포넌트 구조로 옮겨가고 있습니다.

정적 원본 HTML/CSS/JS는 repo 루트의 `local-static-original/`에 로컬 전용으로 보관합니다. 해당 폴더는 git에 올리지 않습니다.

## 실행

```bash
cd frontend
npm install
npm run dev
```

기본 개발 서버는 `http://127.0.0.1:5173`입니다.

## 빌드

```bash
cd frontend
npm run build
```

## API 연결

프론트 코드에서는 `/api` 경로를 Django 백엔드로 프록시할 수 있게 설정했습니다.

- 기본 프록시 대상: `http://127.0.0.1:8000`
- 변경 시: `VITE_SSK_API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev`
- 배포 환경에서 API 호스트를 직접 지정할 때: `VITE_SSK_API_BASE=https://example.com`

API 호출 함수는 `src/services/api.js`에 모아두었습니다.

## 구조

```text
frontend/
├─ index.html                 # Vite 진입점
├─ package.json               # Vue/Vite 실행 스크립트
├─ vite.config.js             # 개발 서버와 /api 프록시
├─ styles/                    # 기존 CSS 토큰/화면 스타일, Vue에서도 재사용
└─ src/
   ├─ App.vue                 # 공통 레이아웃
   ├─ main.js                 # Vue 앱 부트스트랩
   ├─ data/                   # 최신 정적 data.js를 ES module로 변환한 seed 데이터
   ├─ router/                 # Vue Router
   ├─ stores/                 # Pinia 상태
   ├─ services/               # API adapter
   ├─ components/             # 공통 Vue 컴포넌트
   └─ views/                  # 라우트 화면
```

## 마이그레이션 원칙

1. 기존 `styles/`는 우선 그대로 재사용합니다.
2. 정적 JS의 DOM 조작 로직은 Vue 컴포넌트와 Pinia 상태로 이전합니다.
3. `src/services/api.js`의 응답 형태를 Django API와 먼저 맞춘 뒤, `src/data/seed.js` 더미 데이터를 API 데이터로 교체합니다.
