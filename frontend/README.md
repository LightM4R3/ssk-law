# Frontend

정적 HTML/CSS/JavaScript 기반 슥법 프론트 프로토타입입니다.

## Run

```bash
python -m http.server 5173
```

브라우저에서 `http://localhost:5173`을 엽니다.

## Structure

```text
frontend/
├─ index.html
├─ scripts/
│  ├─ api.js
│  ├─ data.js
│  ├─ router.js
│  ├─ latest.js
│  ├─ weekly.js
│  ├─ search.js
│  └─ modal.js
└─ styles/
```

## Routes

| Route | Screen |
|---|---|
| `#/` | Home |
| `#/latest` | Latest bills |
| `#/weekly` | Weekly bills |
| `#/search?q=` | Natural-language search results |

## Data Flow

`scripts/api.js` first tries backend API endpoints. If API loading fails, the app falls back to sample data in `scripts/data.js`.

Primary API targets:

```text
GET /api/categories
GET /api/home/picks
GET /api/bills?category=all
GET /api/weekly
POST /api/search
GET /api/bills/{bill_id}
```
