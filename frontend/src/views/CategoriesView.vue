<script setup>
import { computed } from "vue";
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

function stageCountsForCategory(category) {
  const counts = { proposed: 0, committee: 0, plenary: 0, passed: 0 };
  const bills = itemsInCategory(store.bills, category.id);

  bills.forEach((bill) => {
    if (counts[bill.stage] !== undefined) counts[bill.stage] += 1;
  });

  const remaining = Math.max(0, (category.count || 0) - bills.length);
  if (remaining) {
    const proposed = Math.round(remaining * 0.45);
    const committee = Math.round(remaining * 0.32);
    const plenary = Math.round(remaining * 0.16);
    counts.proposed += proposed;
    counts.committee += committee;
    counts.plenary += plenary;
    counts.passed += Math.max(0, remaining - proposed - committee - plenary);
  }

  return counts;
}

const categoryCards = computed(() => store.categories.map((category, index) => ({
  ...category,
  delay: `${index * 60}ms`,
  stageCounts: stageCountsForCategory(category),
  previewTitles: topTitlesForCategory(category.id),
})));
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

    <div class="cat-grid">
      <RouterLink
        v-for="cat in categoryCards"
        :key="cat.id"
        class="cat-card"
        :style="{ '--cat-h': cat.hue, '--delay': cat.delay }"
        :to="{ name: 'category-detail', params: { id: cat.id } }"
      >
        <div class="cat-card-top">
          <div class="cat-glyph">{{ cat.glyph }}</div>
          <span v-if="cat.hot" class="cat-badge"><span class="pulse"></span>이번 주 화제</span>
          <span v-else class="cat-badge muted">신규 {{ cat.new }}건</span>
        </div>

        <h3 class="cat-name">
          {{ cat.label }}
          <span class="sub">{{ cat.sub }}</span>
        </h3>
        <p class="cat-blurb">{{ cat.blurb }}</p>

        <div class="cat-stats">
          <div class="cat-stat">
            <span class="cat-stat-num">{{ cat.count }}<span class="delta">+{{ cat.new }}</span></span>
            <span class="cat-stat-label">전체 / 이번주 신규</span>
          </div>
          <div class="cat-stat">
            <span class="cat-stat-num">{{ cat.stageCounts.committee }}</span>
            <span class="cat-stat-label">위원회 심사 중</span>
          </div>
        </div>

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
