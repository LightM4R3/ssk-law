import { defineStore } from "pinia";

import {
  BILLS,
  CATEGORIES,
  CATEGORY_META,
  PICKS,
  STAGES,
  WEEKLY,
} from "../data/seed";

const navItems = [
  { name: "home", label: "홈" },
  { name: "latest", label: "최신 법안" },
  { name: "weekly", label: "인기 법안" },
  { name: "categories", label: "분야별" },
];

function normalizeCategory(category) {
  const meta = CATEGORY_META[category.id] || {};
  return {
    ...category,
    ...meta,
  };
}

function normalizeBill(bill) {
  return {
    ...bill,
    summaryText: Array.isArray(bill.summary) ? bill.summary.join(" ") : bill.summary,
  };
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

function findBillByRef(state, ref) {
  return state.bills.find((bill) => bill.id === ref)
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

export const useAppStore = defineStore("app", {
  state: () => ({
    navItems,
    categories: CATEGORIES.filter((category) => category.id !== "all").map(normalizeCategory),
    totalTrackedCount: CATEGORIES.find((category) => category.id === "all")?.count || 0,
    bills: BILLS.map(normalizeBill),
    picks: PICKS.map(normalizeBill),
    weekly: WEEKLY,
    activeBillId: null,
    activeSimilar: null,
  }),
  getters: {
    allBills: (state) => [...state.picks, ...state.bills],
    activeBill: (state) => {
      if (!state.activeBillId) return null;
      return [...state.picks, ...state.bills].find((bill) => bill.id === state.activeBillId) || null;
    },
    activeSimilarData: (state) => {
      if (!state.activeSimilar) return null;
      const allBills = [...state.picks, ...state.bills];
      const parent = allBills.find((bill) => bill.id === state.activeSimilar.parentId);
      const similar = parent?.similar?.[state.activeSimilar.index];
      if (!parent || !similar) return null;

      return {
        parent,
        similar,
        index: state.activeSimilar.index,
      };
    },
    weeklyItems: (state) => state.weekly.map((item) => {
      const bill = state.bills.find((candidate) => candidate.id === item.ref)
        || state.picks.find((candidate) => candidate.id === item.ref);

      return {
        ...item,
        bill,
      };
    }),
    tickerItems: (state) => {
      const latestBill = [...state.bills].sort((a, b) => dateValue(b.proposedAt) - dateValue(a.proposedAt))[0];
      const weeklyItems = state.weekly.map((item) => ({
        ...item,
        bill: findBillByRef(state, item.ref),
      }));
      const topWeekly = weeklyItems[0];
      const risingWeekly = weeklyItems
        .filter((item) => item.ref !== topWeekly?.ref && trendValue(item.trend) > 0)
        .sort((a, b) => trendValue(b.trend) - trendValue(a.trend))[0];
      const categoryStats = getWeeklyCategoryStats(state);
      const topCategory = categoryStats[0];
      const newestCategory = [...state.categories]
        .filter((category) => category.id !== topCategory?.id)
        .sort((a, b) => (b.new || 0) - (a.new || 0))[0];
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
        newestCategory && {
          id: "newest-category",
          type: "category",
          label: "신규 많은 분야",
          title: newestCategory.label,
          meta: `이번 주 신규 ${newestCategory.new}건`,
          categoryId: newestCategory.id,
        },
        digitalCategory && {
          id: "digital-watch",
          type: "category",
          label: "분야 추적",
          title: "디지털 권리",
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
  },
  actions: {
    openBill(id) {
      this.activeBillId = id;
      this.activeSimilar = null;
      document.body.style.overflow = "hidden";
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
