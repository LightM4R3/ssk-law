import { defineStore } from "pinia";

import {
  CATEGORY_META,
  STAGES,
} from "../data/display";
import {
  getApiErrorState,
  lawApi,
  normalizeBill as normalizeApiBill,
  normalizeCategory as normalizeApiCategory,
  normalizeSimilar,
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

function findBillByTitle(state, title) {
  if (!title) return null;
  return uniqueBills([...state.picks, ...state.bills, ...Object.values(state.billDetails)])
    .find((bill) => bill.title === title)
    || null;
}

function seedBillFromSimilar(parent, similar) {
  if (!parent || !similar?.targetId) return null;
  return withBillPresentation({
    ...parent,
    id: similar.targetId,
    idx: similar.targetId,
    title: similar.title || parent.title,
    proposedAt: similar.date || "",
    stage: similar.stage ? stageKeyFromLabel(similar.stage) : parent.stage,
    summary: ["상세 정보를 불러오는 중입니다."],
    summaryText: "상세 정보를 불러오는 중입니다.",
    similar: [],
    similarLoaded: false,
    detailLoaded: false,
  });
}

function mergeBillById(items, id, changes) {
  return items.map((bill) => (
    bill.id === id
      ? withBillPresentation({ ...bill, ...changes })
      : bill
  ));
}

function deferAfterPaint(callback, delay = 180) {
  if (typeof window === "undefined") {
    callback();
    return null;
  }

  let timerId = null;
  const schedule = () => {
    timerId = window.setTimeout(callback, delay);
  };

  if (typeof window.requestAnimationFrame === "function") {
    window.requestAnimationFrame(schedule);
  } else {
    schedule();
  }

  return () => {
    if (timerId !== null) window.clearTimeout(timerId);
  };
}

let cancelPendingBillDetailLoad = null;

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
    categoryBillLoading: {},
    categoryBillErrors: {},
    categories: [],
    totalTrackedCount: 0,
    bills: [],
    picks: [],
    weekly: [],
    billDetails: {},
    similarLoading: {},
    similarErrors: {},
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
      this.similarLoading = {};
      this.similarErrors = {};
      this.categoryBillLoading = {};
      this.categoryBillErrors = {};

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
    async loadBillDetail(id, options = {}) {
      if (!id || (this.billDetails[id]?.detailLoaded && !options.force)) return;

      try {
        const detail = normalizeApiBill(await lawApi.getBill(id));
        const current = findBillByRef(this, id);
        this.billDetails[id] = withBillPresentation({
          ...current,
          ...detail,
          cats: detail.cats.length ? detail.cats : current?.cats || [],
          summary: detail.summary.length ? detail.summary : current?.summary || [],
          summaryText: detail.summaryText || current?.summaryText || "",
          similar: current?.similar?.length ? current.similar : detail.similar,
          similarLoaded: current?.similarLoaded || detail.similarLoaded,
          detailLoaded: true,
        });
      } catch (error) {
        this.apiError = getApiErrorState(error).message;
      }
    },
    async loadSimilarBills(id, options = {}) {
      if (!id || this.similarLoading[id]) return;
      const current = findBillByRef(this, id);
      const requestedLimit = Number(options.limit || 5);
      if (
        current?.similarLoaded
        && !options.refresh
        && (current.similar?.length || 0) >= requestedLimit
      ) return;

      this.similarLoading[id] = true;
      this.similarErrors[id] = null;
      try {
        const payload = await lawApi.getSimilarBills(id, {
          limit: requestedLimit,
          ...(options.refresh ? { refresh: 1 } : {}),
        });
        const similar = normalizeSimilar(payload?.similar || []);
        const changes = { similar, similarLoaded: true };
        this.picks = mergeBillById(this.picks, id, changes);
        this.bills = mergeBillById(this.bills, id, changes);
        if (this.billDetails[id]) {
          this.billDetails[id] = withBillPresentation({
            ...this.billDetails[id],
            ...changes,
          });
        } else if (current) {
          this.billDetails[id] = withBillPresentation({
            ...current,
            ...changes,
          });
        }
      } catch (error) {
        this.similarErrors[id] = getApiErrorState(error, "유사 법안을 불러오지 못했어요");
      } finally {
        this.similarLoading[id] = false;
      }
    },
    async loadCategoryBills(categoryId) {
      if (!categoryId || this.categoryBillLoading[categoryId]) return;

      const category = this.categories.find((item) => item.id === categoryId);
      const alreadyLoaded = this.bills.filter((bill) => bill.cats?.some((cat) => cat.k === categoryId)).length;
      if (category?.count && alreadyLoaded >= category.count) {
        this.categoryBillErrors[categoryId] = null;
        return;
      }

      this.categoryBillLoading[categoryId] = true;
      this.categoryBillErrors[categoryId] = null;
      try {
        let page = 1;
        let totalPages = 1;
        const loaded = [];
        do {
          const payload = await lawApi.getBills({
            category: categoryId,
            sort: "-proposed_at",
            page,
            page_size: 100,
          });
          const incoming = extractArray(payload, "bills")
            .map((bill, index) => withBillPresentation(normalizeApiBill(bill), this.bills.length + loaded.length + index));
          loaded.push(...incoming);
          totalPages = Number(payload?.pagination?.total_pages || page);
          page += 1;
        } while (page <= totalPages);

        this.bills = uniqueBills([...this.bills, ...loaded]);
      } catch (error) {
        this.categoryBillErrors[categoryId] = getApiErrorState(error, "분야별 법안을 슥 가져오지 못하고 있어요");
      } finally {
        this.categoryBillLoading[categoryId] = false;
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
      if (cancelPendingBillDetailLoad) {
        cancelPendingBillDetailLoad();
        cancelPendingBillDetailLoad = null;
      }

      this.activeBillId = id;
      this.activeSimilar = null;
      document.body.style.overflow = "hidden";

      if (this.apiStatus !== "fallback") {
        const current = findBillByRef(this, id);
        const loadDetail = () => {
          cancelPendingBillDetailLoad = null;
          if (this.activeBillId === id) this.loadBillDetail(id);
        };

        if (current) {
          cancelPendingBillDetailLoad = deferAfterPaint(loadDetail, 220);
        } else {
          loadDetail();
        }
      }
    },
    async openBillFromSimilar(id, seed = null) {
      if (!id) return;
      this.activeSimilar = null;

      if (seed && !findBillByRef(this, id)) {
        this.billDetails[id] = seed;
      }

      this.openBill(id);

      if (this.apiStatus !== "fallback") {
        await this.loadBillDetail(id, { force: true });
      }
    },
    closeBill() {
      if (cancelPendingBillDetailLoad) {
        cancelPendingBillDetailLoad();
        cancelPendingBillDetailLoad = null;
      }
      this.activeBillId = null;
      document.body.style.overflow = "";
    },
    openSimilar(parentId, index) {
      const parent = findBillByRef(this, parentId);
      const similar = parent?.similar?.[index];
      if (similar?.targetId) {
        this.openBillFromSimilar(similar.targetId, seedBillFromSimilar(parent, similar));
        return;
      }

      const target = findBillByTitle(this, similar?.title);
      if (target?.id) {
        this.openBillFromSimilar(target.id);
        return;
      }

      this.activeBillId = null;
      this.activeSimilar = { parentId, index };
      document.body.style.overflow = "hidden";
    },
    openSimilarItem({ parent, similar, index = 0 } = {}) {
      if (similar?.targetId) {
        this.openBillFromSimilar(similar.targetId, seedBillFromSimilar(parent, similar));
        return;
      }

      if (parent?.id) {
        this.openSimilar(parent.id, index);
      }
    },
    closeSimilar() {
      this.activeSimilar = null;
      document.body.style.overflow = "";
    },
  },
});
