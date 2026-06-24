<script setup>
import { computed } from "vue";
import ApiStateCard from "../components/ApiStateCard.vue";
import { useAppStore } from "../stores/app";

const store = useAppStore();

function itemsInCategory(items, categoryId) {
  return items.filter((item) => item.cats?.some((cat) => cat.k === categoryId));
}

function topTitlesForCategory(categoryId, limit = 3) {
  const seen = new Set();
  const titles = [];
  const push = (title) => {
    if (title && !seen.has(title)) {
      seen.add(title);
      titles.push(title);
    }
  };

  store.weekly
    .filter((item) => item.cats?.some((cat) => cat.k === categoryId))
    .forEach((item) => push(item.title));
  itemsInCategory(store.bills, categoryId).forEach((bill) => push(bill.title));
  itemsInCategory(store.picks, categoryId).forEach((pick) => push(pick.title));

  return titles.slice(0, limit);
}

const categoryCards = computed(() => store.categories.map((category, index) => ({
  ...category,
  delay: `${index * 60}ms`,
  previewTitles: topTitlesForCategory(category.id),
})));
const isLoadingCategories = computed(() => store.apiStatus === "loading" && !store.categories.length);
</script>

<template>
  <section class="view active">
    <div class="section-head">
      <div>
        <h2>분야별로 슥 둘러보기</h2>
        <div class="sub">9개 분야 · 시민 생활과 가까운 주제부터, 카드를 클릭해 들어가 보세요.</div>
      </div>
      <div class="cat-badge total-badge">
        <span class="pulse"></span>
        총 {{ store.totalTrackedCount }}건 추적 중
      </div>
    </div>

    <div v-if="store.resourceErrors.categories" class="grid">
      <ApiStateCard :state="store.resourceErrors.categories" @retry="store.loadInitialData" />
    </div>
    <div v-else-if="isLoadingCategories" class="grid">
      <ApiStateCard :state="store.loadingState" :show-action="false" />
    </div>
    <div v-else-if="!categoryCards.length" class="grid">
      <ApiStateCard
        :state="store.emptyState('분야 정보가 아직 없어요', '백엔드 응답은 성공했지만 분야 목록이 비어 있습니다.')"
        @retry="store.loadInitialData"
      />
    </div>

    <div v-else class="cat-grid">
      <RouterLink
        v-for="cat in categoryCards"
        :key="cat.id"
        class="cat-card"
        :style="{ '--cat-h': cat.hue, '--delay': cat.delay }"
        :to="{ name: 'category-detail', params: { id: cat.id } }"
      >
        <div class="cat-card-top">
          <div class="cat-glyph">{{ cat.glyph }}</div>
          <span class="cat-badge muted">전체 법안 {{ cat.count }}건</span>
        </div>

        <h3 class="cat-name">
          {{ cat.label }}
          <span class="sub">{{ cat.sub }}</span>
        </h3>
        <p class="cat-blurb">{{ cat.blurb }}</p>

        <div class="cat-preview">
          <div v-for="title in cat.previewTitles" :key="title" class="cat-preview-item">
            <span>{{ title }}</span>
          </div>
        </div>

        <div class="cat-cta">
          슥 들어가기
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14" />
            <path d="m13 5 7 7-7 7" />
          </svg>
        </div>
      </RouterLink>
    </div>
  </section>
</template>
