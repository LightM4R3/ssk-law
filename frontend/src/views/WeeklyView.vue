<script setup>
import { computed } from "vue";

import ApiStateCard from "../components/ApiStateCard.vue";
import { useAppStore } from "../stores/app";

const store = useAppStore();
const items = computed(() => store.weeklyItems);
const isLoadingWeekly = computed(() => store.apiStatus === "loading" && !items.value.length);

function openWeeklyItem(item) {
  if (item.bill) {
    store.openBill(item.bill.id);
  }
}
</script>

<template>
  <section class="view active">
    <div class="section-head">
      <div>
        <h2>이번 주 인기 법안</h2>
        <div class="sub">이번 주 가장 인기가 많은 법안을 확인할 수 있어요</div>
      </div>
    </div>

    <div v-if="store.resourceErrors.weekly" class="grid">
      <ApiStateCard :state="store.resourceErrors.weekly" @retry="store.loadInitialData" />
    </div>
    <div v-else-if="isLoadingWeekly" class="grid">
      <ApiStateCard :state="store.loadingState" :show-action="false" />
    </div>
    <div v-else-if="!items.length" class="grid">
      <ApiStateCard
        :state="store.emptyState('인기 법안이 아직 없어요', '백엔드 응답은 성공했지만 인기 법안 목록이 비어 있습니다.')"
        @retry="store.loadInitialData"
      />
    </div>

    <div v-else class="weekly-list">
      <article
        v-for="item in items"
        :key="item.ref"
        class="weekly-row"
        tabindex="0"
        @click="openWeeklyItem(item)"
        @keydown.enter="openWeeklyItem(item)"
      >
        <div class="weekly-rank">{{ item.rank }}</div>
        <div class="weekly-body">
          <div class="weekly-cats">
            <span
              v-for="cat in item.cats"
              :key="cat.k"
              class="tag"
              :class="{ accent: cat.accent }"
            >
              {{ cat.label }}
            </span>
          </div>
          <div class="weekly-title">{{ item.title }}</div>
          <div class="weekly-snip">{{ item.snip }}</div>
        </div>
        <div class="weekly-stats">
          <span class="weekly-views">{{ Number(item.view || 0).toLocaleString() }}</span>
          <span v-if="item.trend" class="weekly-trend" :class="{ down: item.down }">{{ item.trend }}</span>
        </div>
        <div class="weekly-go">슥 보기</div>
      </article>
    </div>
  </section>
</template>
