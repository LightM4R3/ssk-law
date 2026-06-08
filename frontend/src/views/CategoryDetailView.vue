<script setup>
import { computed } from "vue";

import ApiStateCard from "../components/ApiStateCard.vue";
import BillCard from "../components/BillCard.vue";
import { useAppStore } from "../stores/app";

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
});

const store = useAppStore();
const category = computed(() => store.categories.find((item) => item.id === props.id) || {
  id: props.id,
  label: "분야",
  hue: 245,
  glyph: "슥",
  blurb: "관련 법안을 불러오는 중입니다.",
});
const bills = computed(() => store.bills
  .filter((bill) => bill.cats.some((cat) => cat.k === category.value.id))
  .map((bill) => ({
    ...bill,
    stageLabel: store.stageLabel(bill.stage),
    stageClass: store.stageClass(bill.stage),
  })));
</script>

<template>
  <section class="view active">
    <div class="cat-hero" :style="{ '--cat-h': category.hue }">
      <div class="cat-hero-glyph">{{ category.glyph }}</div>
      <div>
        <h2>{{ category.label }}</h2>
        <p>{{ category.blurb }}</p>
      </div>
      <div class="cat-hero-stats">
        <strong>{{ bills.length }}</strong>
        <span>관련 법안</span>
      </div>
    </div>

    <div class="grid">
      <ApiStateCard
        v-if="store.resourceErrors.bills"
        :state="store.resourceErrors.bills"
        @retry="store.loadInitialData"
      />
      <ApiStateCard
        v-else-if="store.apiStatus === 'loading' && !store.bills.length"
        :state="store.loadingState"
        :show-action="false"
      />
      <ApiStateCard
        v-else-if="!bills.length"
        :state="store.emptyState('이 분야의 법안이 아직 없어요', '백엔드 응답은 성공했지만 해당 분야에 표시할 법안이 없습니다.')"
        @retry="store.loadInitialData"
      />
      <template v-else>
        <BillCard v-for="bill in bills" :key="bill.id" :bill="bill" @select="store.openBill($event.id)" />
      </template>
    </div>
  </section>
</template>
