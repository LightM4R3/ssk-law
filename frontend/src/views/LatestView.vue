<script setup>
import { computed, ref } from "vue";

import ApiStateCard from "../components/ApiStateCard.vue";
import BillCard from "../components/BillCard.vue";
import { useAppStore } from "../stores/app";

const store = useAppStore();
const activeCategory = ref("all");

const categories = computed(() => [
  { id: "all", label: "전체" },
  ...store.categories,
]);

const bills = computed(() => store.bills
  .filter((bill) => activeCategory.value === "all" || bill.cats.some((cat) => cat.k === activeCategory.value))
  .map((bill) => ({
    ...bill,
    stageLabel: store.stageLabel(bill.stage),
    stageClass: store.stageClass(bill.stage),
  })));
const isLoadingBills = computed(() => store.apiStatus === "loading" && !store.bills.length);
</script>

<template>
  <section class="view active">
    <div class="section-head">
      <div>
        <h2>최신 법안</h2>
        <div class="sub">최근 발의·심사 중인 법안을 분야별로 빠르게 확인합니다.</div>
      </div>
    </div>

    <div class="filters filter-row">
      <button
        v-for="cat in categories"
        :key="cat.id"
        class="chip"
        :class="{ active: activeCategory === cat.id }"
        type="button"
        @click="activeCategory = cat.id"
      >
        {{ cat.label }}
      </button>
    </div>

    <div class="grid">
      <ApiStateCard
        v-if="store.resourceErrors.bills"
        :state="store.resourceErrors.bills"
        @retry="store.loadInitialData"
      />
      <ApiStateCard
        v-else-if="isLoadingBills"
        :state="store.loadingState"
        :show-action="false"
      />
      <ApiStateCard
        v-else-if="!bills.length"
        :state="store.emptyState('조건에 맞는 법안이 아직 없어요', '백엔드 응답은 성공했지만 이 분야에 표시할 법안이 없습니다.')"
        @retry="store.loadInitialData"
      />
      <template v-else>
        <BillCard v-for="bill in bills" :key="bill.id" :bill="bill" @select="store.openBill($event.id)" />
      </template>
    </div>
  </section>
</template>
