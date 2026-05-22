// API adapter for replacing the static demo data with backend responses.
// Set window.SSK_API_BASE before this script loads if the API lives on another origin.
const API_BASE = window.SSK_API_BASE || "";

const API_ENDPOINTS = {
  categories: "/api/categories",
  picks: "/api/home/picks",
  bills: "/api/bills?category=all&page_size=100",
  weekly: "/api/bills?sort=-view_count&page_size=10",
  ...(window.SSK_API_ENDPOINTS || {}),
};

function apiUrl(path) {
  if (/^https?:\/\//.test(path)) return path;
  return `${API_BASE}${path}`;
}

async function fetchJson(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeout || 5000);

  try {
    const res = await fetch(apiUrl(path), {
      headers: { Accept: "application/json", ...(options.headers || {}) },
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
    return await res.json();
  } finally {
    clearTimeout(timeout);
  }
}

function asArray(payload, key) {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload[key])) return payload[key];
  if (payload && Array.isArray(payload.data)) return payload.data;
  return [];
}

function normalizeCategory(raw) {
  return {
    id: raw.id || raw.key || raw.slug || "all",
    label: raw.label || raw.name || "전체",
    count: Number(raw.count || raw.total || 0),
  };
}

function normalizeCat(raw, index = 0) {
  if (typeof raw === "string") {
    return { label: raw, k: raw, accent: index === 0 };
  }
  return {
    label: raw.label || raw.name || raw.title || raw.k || raw.id || "기타",
    k: raw.k || raw.id || raw.key || raw.slug || raw.label || raw.name || "etc",
    accent: raw.accent !== undefined ? Boolean(raw.accent) : index === 0,
  };
}

function normalizeSimilar(raw) {
  return {
    title: raw.title || raw.name || "",
    date: raw.date || raw.proposedAt || raw.proposed_at || "",
    stage: raw.stageLabel || raw.stage_label || raw.stage || "",
  };
}

function normalizeStage(rawStage) {
  const stage = String(rawStage || "").trim();
  const aliases = {
    proposed: "proposed",
    proposal: "proposed",
    submitted: "proposed",
    "발의": "proposed",
    committee: "committee",
    review: "committee",
    "위원회": "committee",
    "위원회 심사": "committee",
    plenary: "plenary",
    assembly: "plenary",
    "본회의": "plenary",
    "본회의 상정": "plenary",
    passed: "passed",
    enacted: "passed",
    "통과": "passed",
    "통과 · 공포": "passed",
    "공포": "passed",
  };
  return aliases[stage] || "proposed";
}

function normalizeBill(raw, index = 0) {
  const cats = raw.cats || raw.categories || raw.categoryList || [];
  const summary = raw.summary || raw.summaries || raw.points || [];
  const similar = raw.similar || raw.similarBills || raw.related || [];

  return {
    id: String(raw.id || raw.billId || raw.bill_id || raw.ref || `api-${index}`),
    span: raw.span || (index === 0 ? "span-6" : index < 3 ? "span-3" : "span-2"),
    compact: raw.compact !== undefined ? Boolean(raw.compact) : index >= 3,
    featured: Boolean(raw.featured),
    title: raw.title || raw.name || raw.billName || "제목 없는 법안",
    cats: cats.map(normalizeCat),
    proposedAt: raw.proposedAt || raw.proposed_at || raw.proposedDate || raw.proposed_date || "",
    proposer: raw.proposer || raw.representative || raw.sponsor || "",
    stage: normalizeStage(raw.stage || raw.status),
    summary: Array.isArray(summary) ? summary : [String(summary || "")].filter(Boolean),
    sentiment: Number(raw.sentiment || raw.approvalRate || raw.approval_rate || 0),
    comments: Number(raw.comments || raw.commentCount || raw.comment_count || 0),
    impact: raw.impact || raw.expectedImpact || raw.expected_impact || "",
    similar: Array.isArray(similar) ? similar.map(normalizeSimilar) : [],
  };
}

function normalizeWeekly(raw, index = 0) {
  const cats = raw.cats || raw.categories || raw.categoryList || [];
  const summary = raw.summary || raw.summaries || [];
  const snip = raw.snip || (Array.isArray(summary) && summary[0]) || raw.description || "";
  
  // Generate visual weekly stats metrics (since they're view-based now)
  const views = Number(raw.comments || raw.viewCount || raw.view_count || raw.view || 0);
  const trends = ["+42%", "+28%", "+19%", "+12%", "+7%", "+5%", "+4%", "+2%", "+1%", "-1%"];
  const trend = trends[index] || "+1%";
  const down = trend.startsWith("-");

  return {
    rank: Number(raw.rank || index + 1),
    ref: String(raw.ref || raw.id || raw.billId || raw.bill_id || ""),
    title: raw.title || raw.name || "",
    cats: cats.map(normalizeCat),
    snip: snip,
    view: views,
    trend: trend,
    down: down,
  };
}

function replaceArray(target, source) {
  target.splice(0, target.length, ...source);
}

function rebuildCategoriesFromBills(bills) {
  const counts = new Map();
  bills.forEach(b => b.cats.forEach(c => counts.set(c.k, (counts.get(c.k) || 0) + 1)));
  return [
    { id: "all", label: "전체", count: bills.length },
    ...[...counts.entries()].map(([id, count]) => {
      const sample = bills.flatMap(b => b.cats).find(c => c.k === id);
      return { id, label: sample ? sample.label : id, count };
    }),
  ];
}

async function loadAppData() {
  try {
    const [categoriesPayload, picksPayload, billsPayload, weeklyPayload] = await Promise.all([
      fetchJson(API_ENDPOINTS.categories).catch(() => ({ categories: [] })),
      fetchJson(API_ENDPOINTS.picks),
      fetchJson(API_ENDPOINTS.bills),
      fetchJson(API_ENDPOINTS.weekly),
    ]);

    const picks = asArray(picksPayload, "picks").map(normalizeBill);
    const bills = asArray(billsPayload, "bills").map(normalizeBill);
    const weekly = asArray(weeklyPayload, "bills").map(normalizeWeekly);
    const categories = asArray(categoriesPayload, "categories").map(normalizeCategory);

    if (!picks.length || !bills.length) {
      throw new Error("API response is missing required bill lists.");
    }

    replaceArray(PICKS, picks);
    replaceArray(BILLS, bills);
    if (weekly.length) replaceArray(WEEKLY, weekly);
    replaceArray(CATEGORIES, categories.length ? categories : rebuildCategoriesFromBills(bills));

    return { source: "api" };
  } catch (error) {
    console.error("API data load failed:", error);
    throw error;
  }
}

