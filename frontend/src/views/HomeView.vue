<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

import ApiStateCard from "../components/ApiStateCard.vue";
import HomeCarousel from "../components/HomeCarousel.vue";
import { useAppStore } from "../stores/app";

const router = useRouter();
const store = useAppStore();
const query = ref("");
const picks = computed(() => store.picks.map((bill) => ({
  ...bill,
  stageLabel: store.stageLabel(bill.stage),
  stageClass: store.stageClass(bill.stage),
})));
const isLoadingPicks = computed(() => store.apiStatus === "loading" && !picks.value.length);
const curationCopy = computed(() => {
  if (store.apiStatus === "ready" || store.apiStatus === "partial") {
    return {
      eyebrow: "시민 생활과 가까운 오늘의 법안",
      sub: "오늘 눈여겨볼 만한 법안을 슥 골라봤어요.",
    };
  }

  return {
    eyebrow: "오늘의 법안",
    sub: "오늘 눈여겨볼 만한 법안을 확인하세요.",
  };
});

function submitSearch() {
  const value = query.value.trim();
  if (value) {
    router.push({ name: "search", query: { q: value } });
  }
}
</script>

<template>
  <section class="view active">
    <div class="search-row">
      <form class="search" @submit.prevent="submitSearch">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input v-model="query" placeholder="슥, 찾아보세요 · 예: 청년 월세, 플랫폼 노동, 기후" autocomplete="off" @keydown.enter="submitSearch" />
        <button class="suk-caret" type="submit" aria-label="search">&#49829;</button>
      </form>
    </div>

    <div class="section-head">
      <div>
        <h2>오늘 슥 보기 좋은 법안</h2>
        <div class="sub">{{ curationCopy.sub }}</div>
      </div>
    </div>

    <div v-if="store.resourceErrors.picks" class="grid">
      <ApiStateCard :state="store.resourceErrors.picks" @retry="store.loadInitialData" />
    </div>
    <div v-else-if="isLoadingPicks" class="grid">
      <ApiStateCard :state="store.loadingState" :show-action="false" />
    </div>
    <div v-else-if="!picks.length" class="grid">
      <ApiStateCard
        :state="store.emptyState('추천 법안이 아직 없어요', '백엔드 응답은 성공했지만 홈 추천 법안이 비어 있습니다.')"
        @retry="store.loadInitialData"
      />
    </div>
    <HomeCarousel
      v-else
      :picks="picks"
      :eyebrow="curationCopy.eyebrow"
      @select="store.openBill($event.id)"
      @select-similar="store.openSimilar($event.parentId, $event.index)"
    />
  </section>
</template>
