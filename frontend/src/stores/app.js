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

const tickerItems = [
  "플랫폼 노동자 보호 법안 상임위 심사",
  "청년 월세 지원 확대안 신규 발의",
  "디지털 권리 분야 법안 14건",
  "이번 주 인기 분야: 복지",
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

export const useAppStore = defineStore("app", {
  state: () => ({
    navItems,
    tickerItems,
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
