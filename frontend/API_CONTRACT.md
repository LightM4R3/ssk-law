# SSK-Law Frontend API Contract

The frontend first tries these endpoints from the same origin.
Set `window.SSK_API_BASE` before `scripts/api.js` loads if the backend runs on a different origin.

Optional endpoint overrides:

```html
<script>
  window.SSK_API_BASE = "https://api.example.com";
  window.SSK_API_ENDPOINTS = {
    picks: "/v1/home/picks",
    bills: "/v1/bills?category=all",
    weekly: "/v1/weekly",
    categories: "/v1/categories"
  };
</script>
```

## Required First

`GET /api/home/picks`

```json
{
  "picks": [
    {
      "id": "p1",
      "title": "플랫폼 노동자에게도 유급 휴가와 산재보험을.",
      "categories": [{ "id": "labor", "label": "노동" }],
      "proposedAt": "2026.04.28",
      "proposer": "김OO 의원 외 12인",
      "stage": "committee",
      "summary": ["요약 1", "요약 2", "요약 3"],
      "sentiment": 68,
      "comments": 1284,
      "impact": "예상 영향",
      "similar": [{ "title": "유사 법안", "date": "2026.03.11", "stage": "위원회" }]
    }
  ]
}
```

`GET /api/bills?category=all`

```json
{
  "bills": [
    {
      "id": "b1",
      "title": "청년 월세 지원 한도를 30만 원으로.",
      "categories": [{ "id": "housing", "label": "주거" }],
      "proposedAt": "2026.05.07",
      "proposer": "박OO 의원 외 9인",
      "stage": "proposed",
      "summary": ["요약 1", "요약 2"],
      "sentiment": 74,
      "comments": 892,
      "impact": "예상 영향"
    }
  ]
}
```

## Optional

`GET /api/categories`

```json
{
  "categories": [
    { "id": "all", "label": "전체", "count": 142 },
    { "id": "labor", "label": "노동", "count": 18 }
  ]
}
```

If this endpoint is missing, the frontend computes category counts from `/api/bills`.

`GET /api/weekly`

```json
{
  "weekly": [
    {
      "rank": 1,
      "ref": "p1",
      "title": "플랫폼 노동자 유급휴가·산재보험 보장법",
      "categories": [{ "id": "labor", "label": "노동" }],
      "snip": "4대 보험 의무화와 연 5일 유급 휴가를 단계 도입.",
      "view": 128400,
      "trend": "+42%"
    }
  ]
}
```

If this endpoint is missing, the frontend keeps the sample weekly ranking.

## Frontend Routes Backed By These Fields

- `#/categories` uses `categories` plus category ids found in bill `categories`.
- `#/categories/:id` shows bills whose category `id` matches `:id`.
- `#/picks/:id/similar` uses the selected bill's `similar` array.

No extra endpoint is required for the first version of the category or similar-bill pages.

## Stage Values

Preferred values:

- `proposed`
- `committee`
- `plenary`
- `passed`

Korean labels such as `발의`, `위원회 심사`, `본회의 상정`, `통과 · 공포` are also normalized by the frontend.
