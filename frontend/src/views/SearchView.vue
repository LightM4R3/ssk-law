<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";

import BillCard from "../components/BillCard.vue";
import { useAppStore } from "../stores/app";

const route = useRoute();
const store = useAppStore();
const query = computed(() => String(route.query.q || ""));
const results = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  const bills = keyword
    ? store.bills.filter((bill) => `${bill.title} ${bill.summaryText}`.toLowerCase().includes(keyword))
    : store.bills;

  return bills.map((bill) => ({
    ...bill,
    stageLabel: store.stageLabel(bill.stage),
    stageClass: store.stageClass(bill.stage),
  }));
});
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

    <div class="grid">
      <BillCard v-for="bill in results" :key="bill.id" :bill="bill" @select="store.openBill($event.id)" />
    </div>
  </section>
</template>
