import { defineStore } from "pinia";

import {
  CATEGORY_META,
  STAGES,
} from "../data/presentation";
import {
  getApiErrorState,
  lawApi,
  normalizeBill as normalizeApiBill,
  normalizeCategory as normalizeApiCategory,
} from "../services/api";

const navItems = [
  { name: "latest", label: "최신 법안" },
  { name: "weekly", label: "인기 법안" },
  { name: "categories", label: "분야별" },
  { name: "posts", label: "포스트" },
];

const billLayout = [
  { span: "span-6", featured: true },
  { span: "span-3" },
  { span: "span-3" },
  { span: "span-2", compact: true },
  { span: "span-2", compact: true },
  { span: "span-2", compact: true },
  { span: "span-3" },
  { span: "span-3" },
  { span: "span-2", compact: true },
  { span: "span-2", compact: true },
];

function mergeCategoryPresentation(category) {
  const meta = CATEGORY_META[category.id] || {};
  return {
    ...category,
    ...meta,
  };
}

function withBillPresentation(bill, index = 0) {
  const summary = Array.isArray(bill.summary) ? bill.summary : [bill.summaryText || bill.summary].filter(Boolean);

  return {
    ...(billLayout[index % billLayout.length] || {}),
    ...bill,
    cats: (bill.cats || []).map((cat, catIndex) => ({
      ...cat,
      accent: cat.accent ?? catIndex === 0,
    })),
    summary,
    summaryText: summary.join(" "),
  };
}

function extractArray(payload, key) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.[key])) return payload[key];
  if (Array.isArray(payload?.results)) return payload.results;
  return [];
}

function stageKeyFromLabel(label) {
  if (!label) return "proposed";
  if (label.includes("발의")) return "proposed";
  if (label.includes("위원")) return "committee";
  if (label.includes("본회의")) return "plenary";
  if (label.includes("통과") || label.includes("공포")) return "passed";
  return "committee";
}

function dateValue(date) {
  return Number(date?.replaceAll(".", "") || 0);
}

function trendValue(trend) {
  return Number.parseFloat(String(trend || "0").replace("%", "")) || 0;
}

function uniqueBills(bills) {
  const byId = new Map();
  bills.forEach((bill) => {
    if (bill?.id && !byId.has(bill.id)) byId.set(bill.id, bill);
  });
  return Array.from(byId.values());
}

function findBillByRef(state, ref) {
  return state.billDetails[ref]
    || state.bills.find((bill) => bill.id === ref)
    || state.picks.find((bill) => bill.id === ref)
    || null;
}

function getWeeklyCategoryStats(state) {
  const viewsByCategory = new Map();

  state.weekly.forEach((item) => {
    item.cats.forEach((cat) => {
      viewsByCategory.set(cat.k, (viewsByCategory.get(cat.k) || 0) + item.view);
    });
  });

  return Array.from(viewsByCategory.entries())
    .map(([id, views]) => ({
      ...state.categories.find((category) => category.id === id),
      views,
    }))
    .filter((category) => category.id)
    .sort((a, b) => b.views - a.views);
}

function createWeeklyFromBills(bills) {
  return bills.slice(0, 10).map((bill, index) => ({
    rank: index + 1,
    ref: bill.id,
    title: bill.title,
    cats: bill.cats,
    snip: bill.summary?.[0] || bill.summaryText || "",
    view: bill.viewCount || bill.comments || 0,
    trend: null,
    down: false,
    bill,
  }));
}

function emptyState(title, message) {
  return {
    status: null,
    code: "",
    title,
    message,
  };
}

export const useAppStore = defineStore("app", {
  state: () => ({
    navItems,
    apiStatus: "idle",
    apiError: null,
    resourceErrors: {
      categories: null,
      picks: null,
      bills: null,
      weekly: null,
    },
    categories: [],
    totalTrackedCount: 0,
    bills: [],
    picks: [],
    weekly: [],
    billDetails: {},
    activeBillId: null,
    activeSimilar: null,
    searchLoading: false,
    searchAiLoading: false,
    searchAiStatus: "idle",
    searchError: null,
    searchIntro: "",
    searchSnapshot: null,
    searchResults: [],
    lastSearchQuery: "",
  }),
  getters: {
    allBills: (state) => uniqueBills([...state.picks, ...state.bills, ...Object.values(state.billDetails)]),
    activeBill: (state) => {
      if (!state.activeBillId) return null;
      return findBillByRef(state, state.activeBillId);
    },
    activeSimilarData: (state) => {
      if (!state.activeSimilar) return null;
      const parent = findBillByRef(state, state.activeSimilar.parentId);
      const similar = parent?.similar?.[state.activeSimilar.index];
      if (!parent || !similar) return null;

      return {
        parent,
        similar,
        index: state.activeSimilar.index,
      };
    },
    weeklyItems: (state) => state.weekly.map((item) => ({
      ...item,
      bill: item.bill || findBillByRef(state, item.ref),
    })),
    tickerItems: (state) => {
      const latestBill = [...state.bills].sort((a, b) => dateValue(b.proposedAt) - dateValue(a.proposedAt))[0];
      const weeklyItems = state.weekly.map((item) => ({
        ...item,
        bill: item.bill || findBillByRef(state, item.ref),
      }));
      const topWeekly = weeklyItems[0];
      const risingWeekly = weeklyItems
        .filter((item) => item.ref !== topWeekly?.ref && item.trend && trendValue(item.trend) > 0)
        .sort((a, b) => trendValue(b.trend) - trendValue(a.trend))[0];
      const categoryStats = getWeeklyCategoryStats(state);
      const topCategory = categoryStats[0];
      const digitalCategory = state.categories.find((category) => category.id === "digital");

      return [
        latestBill && {
          id: "latest-bill",
          type: "bill",
          label: "최신 발의안",
          title: latestBill.title,
          meta: `${latestBill.proposedAt} · ${STAGES[latestBill.stage]?.label || "발의"}`,
          billId: latestBill.id,
        },
        topWeekly?.bill && {
          id: "popular-bill",
          type: "bill",
          label: "인기 발의안",
          title: topWeekly.title,
          meta: `${topWeekly.view.toLocaleString()}회 읽음`,
          billId: topWeekly.bill.id,
        },
        risingWeekly?.bill && {
          id: "rising-bill",
          type: "bill",
          label: "급상승",
          title: risingWeekly.title,
          meta: risingWeekly.trend,
          billId: risingWeekly.bill.id,
        },
        topCategory && {
          id: "popular-category",
          type: "category",
          label: "인기 분야",
          title: topCategory.label,
          meta: `${topCategory.views.toLocaleString()}회 관심`,
          categoryId: topCategory.id,
        },
        digitalCategory && {
          id: "digital-watch",
          type: "category",
          label: "분야 추적",
          title: digitalCategory.label,
          meta: `법안 ${digitalCategory.count}건`,
          categoryId: digitalCategory.id,
        },
        {
          id: "weekly-ranking",
          type: "route",
          label: "TOP10",
          title: "이번 주 인기 법안 전체 보기",
          meta: "랭킹",
          route: { name: "weekly" },
        },
      ].filter(Boolean);
    },
    stageLabel: () => (stage) => STAGES[stage]?.label || stage,
    stageClass: () => (stage) => STAGES[stage]?.cls || "s1",
    stageMeta: () => (stage) => STAGES[stage] || STAGES.proposed,
    stageKeyFromLabel: () => stageKeyFromLabel,
    loadingState: () => emptyState(
      "법률을 슥 불러오는 중이에요",
      "백엔드 서버에서 최신 법안 데이터를 가져오고 있습니다.",
    ),
    emptyState: () => (title = "표시할 법안이 아직 없어요", message = "백엔드 응답은 성공했지만 이 조건에 맞는 데이터가 없습니다.") => emptyState(title, message),
  },
  actions: {
    async loadInitialData() {
      if (this.apiStatus === "loading") return;

      this.apiStatus = "loading";
      this.apiError = null;
      this.resourceErrors = {
        categories: null,
        picks: null,
        bills: null,
        weekly: null,
      };
      this.categories = [];
      this.totalTrackedCount = 0;
      this.bills = [];
      this.picks = [];
      this.weekly = [];
      this.billDetails = {};

      const [categoriesResult, picksResult, billsResult, popularResult] = await Promise.allSettled([
        lawApi.getCategories(),
        lawApi.getHomePicks(),
        lawApi.getBills({ sort: "-proposed_at", page_size: 100 }),
        lawApi.getBills({ sort: "-view_count", page_size: 10 }),
      ]);

      let loadedCount = 0;
      const errors = [];

      if (categoriesResult.status === "fulfilled") {
        const categories = extractArray(categoriesResult.value, "categories").map(normalizeApiCategory);
        const all = categories.find((category) => category.id === "all");
        this.totalTrackedCount = all?.count || this.totalTrackedCount;
        this.categories = categories
          .filter((category) => category.id !== "all")
          .map(mergeCategoryPresentation);
        loadedCount += 1;
      } else {
        errors.push(categoriesResult.reason);
        this.resourceErrors.categories = getApiErrorState(categoriesResult.reason, "분야 정보를 슥 가져오지 못하고 있어요");
      }

      if (picksResult.status === "fulfilled") {
        this.picks = extractArray(picksResult.value, "picks")
          .map((bill, index) => withBillPresentation(normalizeApiBill(bill), index));
        loadedCount += 1;
      } else {
        errors.push(picksResult.reason);
        this.resourceErrors.picks = getApiErrorState(picksResult.reason, "오늘의 큐레이션을 슥 가져오지 못하고 있어요");
      }

      if (billsResult.status === "fulfilled") {
        this.bills = extractArray(billsResult.value, "bills")
          .map((bill, index) => withBillPresentation(normalizeApiBill(bill), index));
        loadedCount += 1;
      } else {
        errors.push(billsResult.reason);
        this.resourceErrors.bills = getApiErrorState(billsResult.reason, "최신 법률을 슥 가져오지 못하고 있어요");
      }

      if (popularResult.status === "fulfilled") {
        const popularBills = extractArray(popularResult.value, "bills")
          .map((bill, index) => withBillPresentation(normalizeApiBill(bill), index));
        this.weekly = createWeeklyFromBills(popularBills);
        loadedCount += 1;
      } else {
        errors.push(popularResult.reason);
        this.resourceErrors.weekly = getApiErrorState(popularResult.reason, "인기 법률을 슥 가져오지 못하고 있어요");
      }

      this.apiStatus = loadedCount ? (errors.length ? "partial" : "ready") : "fallback";
      this.apiError = errors[0]?.message || null;
    },
    async loadBillDetail(id) {
      if (!id || this.billDetails[id]) return;

      try {
        const detail = normalizeApiBill(await lawApi.getBill(id));
        const current = findBillByRef(this, id);
        this.billDetails[id] = withBillPresentation({
          ...current,
          ...detail,
          cats: detail.cats.length ? detail.cats : current?.cats || [],
          summary: detail.summary.length ? detail.summary : current?.summary || [],
          summaryText: detail.summaryText || current?.summaryText || "",
        });
      } catch (error) {
        this.apiError = getApiErrorState(error).message;
      }
    },
    async searchBills(query) {
      const normalizedQuery = query.trim();
      this.lastSearchQuery = normalizedQuery;
      this.searchIntro = "";
      this.searchSnapshot = null;
      this.searchAiLoading = false;
      this.searchAiStatus = "idle";
      this.searchError = null;

      if (!normalizedQuery) {
        this.searchResults = [];
        this.searchLoading = false;
        return;
      }

      this.searchLoading = true;

      try {
        const payload = await lawApi.searchBills(normalizedQuery);
        if (this.lastSearchQuery !== normalizedQuery) return;
        this.searchIntro = payload?.intro || "";
        this.searchSnapshot = payload?.snapshot || null;
        this.searchResults = extractArray(payload, "bills")
          .map((bill, index) => withBillPresentation(normalizeApiBill(bill), index));
        this.searchLoading = false;

        if (payload?.aiPending) {
          this.searchAiLoading = true;
          this.searchAiStatus = "loading";
          try {
            const explanation = await lawApi.explainSearch(normalizedQuery);
            if (this.lastSearchQuery !== normalizedQuery) return;
            this.searchIntro = explanation?.intro || this.searchIntro;
            this.searchSnapshot = explanation?.snapshot || this.searchSnapshot;
            this.searchAiStatus = explanation?.aiStatus || "ready";
          } catch (error) {
            if (this.lastSearchQuery === normalizedQuery) {
              this.searchAiStatus = "unavailable";
            }
          } finally {
            if (this.lastSearchQuery === normalizedQuery) {
              this.searchAiLoading = false;
            }
          }
        }
      } catch (error) {
        if (this.lastSearchQuery !== normalizedQuery) return;
        this.searchError = getApiErrorState(error, "검색 결과를 슥 가져오지 못하고 있어요");
        this.searchResults = [];
      } finally {
        if (this.lastSearchQuery === normalizedQuery) {
          this.searchLoading = false;
        }
      }
    },
    openBill(id) {
      this.activeBillId = id;
      this.activeSimilar = null;
      document.body.style.overflow = "hidden";

      if (this.apiStatus !== "fallback") {
        this.loadBillDetail(id);
      }
    },
    closeBill() {
      this.activeBillId = null;
      document.body.style.overflow = "";
    },
    openSimilar(parentId, index) {
      this.activeBillId = null;
      this.activeSimilar = { parentId, index };
      document.body.style.overflow = "hidden";
    },
    closeSimilar() {
      this.activeSimilar = null;
      document.body.style.overflow = "";
    },
  },
});
