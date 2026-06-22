<script setup>
import { computed, watch } from "vue";
import { useRoute } from "vue-router";

import ApiStateCard from "../components/ApiStateCard.vue";
import BillCard from "../components/BillCard.vue";
import { useAppStore } from "../stores/app";

const route = useRoute();
const store = useAppStore();
const query = computed(() => String(route.query.q || ""));
const results = computed(() => {
  const normalizedQuery = query.value.trim();
  const bills = normalizedQuery && store.lastSearchQuery === normalizedQuery
    ? store.searchResults
    : store.bills;

  return bills.map((bill) => ({
    ...bill,
    stageLabel: store.stageLabel(bill.stage),
    stageClass: store.stageClass(bill.stage),
  }));
});
const isSearchMode = computed(() => Boolean(query.value.trim()));
const isLoadingBaseBills = computed(() => !isSearchMode.value && store.apiStatus === "loading" && !store.bills.length);

watch(query, (value) => {
  store.searchBills(value);
}, { immediate: true });
</script>

<template>
  <section class="view active">
    <div class="search-header">
      <div>
        <h2>검색 결과</h2>
        <p>{{ query || "전체" }}</p>
      </div>
      <span class="tag accent">{{ results.length }}건</span>
    </div>

    <div v-if="store.searchError" class="grid">
      <ApiStateCard
        :state="store.searchError"
        action-label="검색 다시 시도"
        @retry="store.searchBills(query)"
      />
    </div>

    <div v-else-if="store.searchLoading" class="ai-card">
      <div class="ai-avatar">슥</div>
      <div class="ai-body">
        <div class="ai-head">
          <div class="ai-title">AI 검색 중</div>
        </div>
        <div class="ai-text">
          관련 법안을 찾고 있어요
          <span class="ai-loading-dots"><span>.</span><span>.</span><span>.</span></span>
        </div>
      </div>
    </div>

    <div v-else-if="store.searchAiLoading" class="ai-card">
      <div class="ai-avatar">슥</div>
      <div class="ai-body">
        <div class="ai-head">
          <div class="ai-title">AI 설명 정리 중</div>
        </div>
        <div class="ai-text">
          관련 법안은 먼저 표시했습니다. 짧은 설명을 정리하고 있습니다
          <span class="ai-loading-dots"><span>.</span><span>.</span><span>.</span></span>
        </div>
      </div>
    </div>

    <div v-else-if="store.searchIntro" class="ai-card">
      <div class="ai-avatar">슥</div>
      <div class="ai-body">
        <div class="ai-head">
          <div class="ai-title">AI 검색 요약</div>
          <span v-if="['High', 'Medium'].includes(store.searchSnapshot?.risk_level)" class="ai-badge">{{ store.searchSnapshot.risk_level }}</span>
        </div>
        <div class="ai-text">{{ store.searchIntro }}</div>
        <div v-if="store.searchSnapshot?.keywords?.length" class="ai-keywords">
          <span v-for="keyword in store.searchSnapshot.keywords" :key="keyword" class="ai-kw">{{ keyword }}</span>
        </div>
      </div>
    </div>

    <div v-if="!store.searchError" class="grid">
      <ApiStateCard
        v-if="isLoadingBaseBills"
        :state="store.loadingState"
        :show-action="false"
      />
      <ApiStateCard
        v-else-if="!store.searchLoading && !results.length"
        :state="store.emptyState(isSearchMode ? '검색 결과가 아직 없어요' : '표시할 법안이 아직 없어요', isSearchMode ? '백엔드 응답은 성공했지만 검색어와 맞는 법안이 없습니다.' : '백엔드 응답은 성공했지만 표시할 법안이 없습니다.')"
        @retry="isSearchMode ? store.searchBills(query) : store.loadInitialData()"
      />
      <template v-else>
        <BillCard v-for="bill in results" :key="bill.id" :bill="bill" @select="store.openBill($event.id)" />
      </template>
    </div>
  </section>
</template>
