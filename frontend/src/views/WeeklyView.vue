<script setup>
import { computed } from "vue";

import { useAppStore } from "../stores/app";

const store = useAppStore();
const items = computed(() => store.weeklyItems);

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
        <div class="sub">이번 주 가장 많이 읽힌 법안을 순위로 확인합니다.</div>
      </div>
    </div>

    <div class="weekly-list">
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
          <span class="weekly-views">{{ item.view.toLocaleString() }}</span>
          <span class="weekly-trend" :class="{ down: item.down }">{{ item.trend }}</span>
        </div>
        <div class="weekly-go">슥 보기</div>
      </article>
    </div>
  </section>
</template>
