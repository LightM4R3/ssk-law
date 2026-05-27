<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

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
      <label class="search">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input v-model="query" placeholder="슥, 찾아보세요 · 예: 청년 월세, 플랫폼 노동, 기후" autocomplete="off" @keydown.enter="submitSearch" />
        <span class="suk-caret">슥</span>
        <span class="kbd">⌘ K</span>
      </label>
      <button class="sort-btn" type="button" @click="submitSearch">
        <span>오늘의 큐레이션</span>
      </button>
    </div>

    <div class="section-head">
      <div>
        <h2>오늘 슥 보기 좋은 법안</h2>
        <div class="sub">5월 14일 · 슥법 에디터가 고른 다섯 법안을 확인하세요.</div>
      </div>
    </div>

    <HomeCarousel
      :picks="picks"
      @select="store.openBill($event.id)"
      @select-similar="store.openSimilar($event.parentId, $event.index)"
    />
  </section>
</template>
