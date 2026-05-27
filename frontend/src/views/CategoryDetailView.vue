<script setup>
import { computed } from "vue";

import BillCard from "../components/BillCard.vue";
import { useAppStore } from "../stores/app";

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
});

const store = useAppStore();
const category = computed(() => store.categories.find((item) => item.id === props.id) || store.categories[0]);
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
      <BillCard v-for="bill in bills" :key="bill.id" :bill="bill" @select="store.openBill($event.id)" />
    </div>
  </section>
</template>
