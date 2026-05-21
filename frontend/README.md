# 슥법 (SSK-Law) — Frontend

최신 법안을 시민의 언어로 빠르게 훑어보는 큐레이션 웹 서비스. 빌드 단계 없이 정적 파일로 바로 서빙할 수 있도록 분리된 구조입니다.

## 실행

빌드 도구는 필요 없습니다. 임의의 정적 서버에서 `dev/index.html`을 열면 됩니다.

```bash
# 예: python
cd dev && python3 -m http.server 5173

# 또는 npx
npx serve dev
```

자연어 검색은 페이지가 `window.claude.complete` API가 주입된 환경에서 동작합니다. 다른 환경에서는 자동으로 키워드 매칭 폴백으로 전환됩니다.

## 디렉토리

```
dev/
├── index.html              엔트리. 스타일·스크립트를 순서대로 로드
├── styles/
│   ├── tokens.css          디자인 토큰(컬러/타이포/라운드/모션 이징/키프레임)·리셋
│   ├── header.css          상단 바, 브랜드 마크, 네비
│   ├── ticker.css          "지금 슥" 마퀴 티커
│   ├── layout.css          main 컨테이너, 뷰 스위칭, 검색 행, 섹션 헤드, 푸터
│   ├── carousel.css        홈 캐러셀 + 피처 카드(pick) + 입체 호버 + 유사 법안 사이드 패널
│   ├── filters.css         최신 페이지 분야 칩
│   ├── cards.css           최신 매거진 그리드 카드 + 3D tilt
│   ├── weekly.css          이번 주 인기 랭킹 행
│   ├── search-results.css  자연어 검색 결과 페이지
│   ├── modal.css           법안 상세 모달
│   ├── categories.css      분야별 허브 + 분야 상세 페이지 + 태그 quickview 팝오버
│   ├── similar.css         유사 법안 페이지 + 유사 법안 모달(원본 컨텍스트 카드 포함)
│   └── responsive.css      980px 이하 가드
└── scripts/
    ├── data.js             CATEGORIES, CATEGORY_META(분야별 hue/글리프/blurb), STAGES, PICKS, BILLS, WEEKLY
    ├── state.js            전역 헬퍼($, $$), activeCat/savedSet, ALL_BY_ID 인덱스
    ├── router.js           해시 라우터
    │                       #/, #/latest, #/weekly, #/search?q=…,
    │                       #/categories, #/categories/:id, #/picks/:id/similar
    ├── modal.js            openModal(id) — 유사 법안 항목 클릭 시 openSimilarModal 연결
    ├── card3d.js           bindCard3D / bindPick3D (마우스 위치 기반 입체 호버)
    ├── ticker.js           renderTicker
    ├── carousel.js         renderCarousel + 의도 감지(intent detection) 드래그/휠/키 스와이프
    │                       각 픽 카드 우측에 "유사한 법안 슥 보기" 사이드 패널 렌더
    ├── latest.js           renderGrid + renderFilters + cardHTML (다른 페이지에서 재사용)
    ├── weekly.js           renderWeekly
    ├── search.js           renderSearch + nlSearch (AI + 키워드 폴백)
    ├── categories.js       renderCategoriesHub / renderCategoryDetail
    │                       전역 .tag[data-cat] 클릭 → 분야 quickview 팝오버
    ├── similar.js          renderSimilarPage(parentId) + openSimilarModal(parentId, idx)
    │                       (유사 법안은 sparse data — 원본 법안 컨텍스트 카드와 함께 표시)
    └── main.js             부트스트랩 (init, ⌘K, Enter 검색)
```

## 스크립트 의존 순서

`index.html`이 다음 순서로 `<script src>`를 로드합니다. 같은 순서로 번들러 entry를 구성하면 됩니다.

1. `data.js` — 다른 모든 모듈이 의존하는 상수 (CATEGORIES, CATEGORY_META, STAGES, PICKS, BILLS, WEEKLY)
2. `state.js` — `$, $$, ALL_BY_ID`
3. `router.js` — `setRoute`는 아래 render\* 함수들을 참조
4. `modal.js` — `openModal` (내부에서 `openSimilarModal` 호출 — 클릭 시점에 평가)
5. `card3d.js` — `bindCard3D`, `bindPick3D`
6. `ticker.js`
7. `carousel.js` — 픽 사이드 패널 클릭은 `openSimilarModal`(similar.js) 의존
8. `latest.js` — `cardHTML`을 export하여 categories.js가 재사용
9. `weekly.js`
10. `categories.js` — `cardHTML`(latest.js) 의존, 전역 tag-click delegation 등록
11. `similar.js` — `openSimilarModal`, `renderSimilarPage`
12. `search.js`
13. `main.js` — `renderTicker()`, `bindCarousel()`, `setRoute(routeFromHash())` 호출

함수 간 forward reference(router.js에서 render\* 호출, carousel.js의 click handler에서 openSimilarModal 호출)는 모두 클릭/라우트 시점에 평가되므로 로드 순서와 무관합니다. 모든 스크립트는 ES 모듈이 아닌 평범한 전역으로 작성되어 있어, 그대로 정적 호스팅하거나 번들러(Vite/Webpack)에 점진적으로 옮길 수 있습니다.

## 데이터 모델

`scripts/data.js`의 `BILLS` 항목 한 건은 다음 모양입니다.

```js
{
  id: "b3",                          // 고유 id (ALL_BY_ID 키)
  span: "span-2" | "span-3" | "span-6",
  compact: true,                     // (옵션) 작은 카드 변형
  title: "어린이 보행자 보호구역 확대·처벌 강화법",
  cats: [{ label: "생활안전", k: "safety", accent: true }],
  proposedAt: "2026.05.03",          // YYYY.MM.DD
  proposer: "최○○ 의원 외 6인",
  stage: "proposed" | "committee" | "plenary" | "passed",
  summary: ["...", "..."],           // 2–3줄 요약 (불릿)
  impact: "전국 약 1.2만 개 …",      // 모달 '예상 영향'
  similar: [{ title, date, stage }], // 모달 '유사 법안'
}
```

`PICKS`는 홈 캐러셀용 데이터입니다.
`WEEKLY` 항목은 `ref`로 위 `id`를 참조해 모달이 같은 데이터를 띄웁니다.

`CATEGORY_META`는 분야별 시각 토큰입니다. 각 분야가 고유한 hue(oklch)와 한자/한글 글리프, 영문 sub, 한 줄 blurb, 이번 주 신규 건수, 핫 토픽 여부를 가집니다. 분야 허브 카드·분야 상세 히어로·태그 quickview 팝오버가 이 메타로 채색됩니다.

```js
CATEGORY_META.labor = {
  glyph: "勞", sub: "Labor", hue: 22,
  blurb: "일하는 사람의 권리·안전망",
  new: 4, hot: true,
};
```

실제 백엔드 연동 시 이 모델 그대로 API 응답에 매핑하면 페이지를 그대로 재사용할 수 있습니다. 입법 단계 라벨은 `data.js` 상단의 `STAGES` 맵에서 정의됩니다.

## 라우트

| 해시 | 화면 |
|---|---|
| `#/` | 홈 — "지금 슥" 티커 + "오늘 슥 보기 좋은" 캐러셀(우측에 유사 법안 사이드 패널) |
| `#/latest` | 최신 법안 매거진 그리드 + 분야 칩 필터 |
| `#/weekly` | 이번 주 인기 랭킹 |
| `#/categories` | 분야별 허브 — 9개 분야 카드 |
| `#/categories/:id` | 분야 상세 — hue 토닝 히어로 + 단계별 통계 + 분야 내 법안 그리드 |
| `#/picks/:id/similar` | 유사 법안 전용 페이지 — 원본 법안 히어로 + 유사 법안 카드 그리드 |
| `#/search?q=…` | 자연어 검색 결과 + AI 답변 + 관련 법안 그리드 |

오버레이(모달/팝오버)는 라우트가 아닌 인-페이지 상태입니다:
- `openModal(id)` — 법안 상세 모달
- `openSimilarModal(parentId, idx)` — 유사 법안 모달(원본 법안 컨텍스트 포함, sparse data 정직하게 표시)
- 전역 `.tag[data-cat]` 클릭 → 분야 quickview 팝오버 (categories.js의 capture-phase delegation)

## 디자인 토큰 메모

| 토큰 | 용도 |
|---|---|
| `--ease-suk` | `cubic-bezier(0.16, 1, 0.3, 1)` — 모든 "슥" 모션의 표준 이징 |
| `--accent` | 딥 슬레이트 블루 액센트 (oklch) |
| `--highlight` | 카드 호버 시 좌→우로 채워지는 액센트 그라데이션의 끝 |
| `--r-md / --r-lg / --r-xl` | 16 / 22 / 28px 라운드 |
| `--shadow-sm/md/lg` | 정적 그림자. 입체 호버 그림자는 `card3d.js`에서 동적으로 계산 |

`prefers-reduced-motion`을 존중합니다 (`tokens.css` 끝의 미디어 쿼리).

## 자연어 검색 동작

`scripts/search.js`의 `nlSearch(query)`가:
1. `data.js`의 모든 법안을 컴팩트 라인으로 직렬화해 프롬프트에 첨부
2. `window.claude.complete(prompt)` 호출 (Haiku, 1024 토큰)
3. 모델 응답에서 `{intro, ids[]}` JSON을 파싱
4. 실패 또는 빈 결과면 `keywordFallback`으로 자동 전환

자체 백엔드로 옮길 경우 `nlSearch`만 교체하면 됩니다 — UI/스크롤/타이핑 애니메이션은 그대로 유지.
