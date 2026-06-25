<script setup>
import { computed, ref, watch } from "vue";

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
const selectedStage = ref("all");
const stageOptions = [
  { key: "all", label: "전체" },
  { key: "proposed", label: "발의" },
  { key: "committee", label: "위원회 심사" },
  { key: "plenary", label: "본회의 상정" },
  { key: "passed", label: "통과 · 공포" },
];
const category = computed(() => store.categories.find((item) => item.id === props.id) || {
  id: props.id,
  label: "분야",
  hue: 245,
  glyph: "슥",
  blurb: "관련 법안을 불러오는 중입니다.",
});
const categoryBills = computed(() => store.bills
  .filter((bill) => bill.cats.some((cat) => cat.k === category.value.id))
  .map((bill) => ({
    ...bill,
    stageLabel: store.stageLabel(bill.stage),
    stageClass: store.stageClass(bill.stage),
  })));
const stageCounts = computed(() => {
  const counts = { all: categoryBills.value.length };
  stageOptions.slice(1).forEach((option) => {
    counts[option.key] = categoryBills.value.filter((bill) => bill.stage === option.key).length;
  });
  return counts;
});
const bills = computed(() => {
  if (selectedStage.value === "all") return categoryBills.value;
  return categoryBills.value.filter((bill) => bill.stage === selectedStage.value);
});
const selectedStageLabel = computed(() => stageOptions.find((option) => option.key === selectedStage.value)?.label || "전체");
const isLoadingCategoryBills = computed(() => Boolean(store.categoryBillLoading[props.id]));
const categoryBillError = computed(() => store.categoryBillErrors[props.id]);

watch(
  () => props.id,
  (categoryId) => {
    selectedStage.value = "all";
    store.loadCategoryBills(categoryId);
  },
  { immediate: true },
);

watch(
  () => store.apiStatus,
  (status) => {
    if (status !== "loading") store.loadCategoryBills(props.id);
  },
);
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
        <strong>{{ category.count || categoryBills.length }}</strong>
        <span>관련 법안</span>
      </div>
    </div>

    <div v-if="categoryBills.length && !isLoadingCategoryBills" class="cat-stage-filter" :style="{ '--cat-h': category.hue }">
      <div class="cat-stage-filter-head">
        <div>
          <span>단계별 보기</span>
          <strong>{{ selectedStageLabel }}</strong>
        </div>
        <p>{{ selectedStage === "all" ? "전체 법안을 보고 있어요" : `${selectedStageLabel} 단계 법안만 보고 있어요` }}</p>
      </div>
      <div class="cat-stage-options" role="tablist" aria-label="법안 단계 필터">
        <button
          v-for="option in stageOptions"
          :key="option.key"
          class="cat-stage-option"
          :class="{ active: selectedStage === option.key }"
          type="button"
          role="tab"
          :aria-selected="selectedStage === option.key"
          @click="selectedStage = option.key"
        >
          <span>{{ option.label }}</span>
          <b>{{ stageCounts[option.key] || 0 }}</b>
        </button>
      </div>
    </div>

    <div class="grid">
      <ApiStateCard
        v-if="categoryBillError"
        :state="categoryBillError"
        @retry="store.loadCategoryBills(props.id)"
      />
      <ApiStateCard
        v-else-if="isLoadingCategoryBills"
        :state="store.loadingState"
        :show-action="false"
      />
      <ApiStateCard
        v-else-if="store.resourceErrors.bills && !categoryBills.length"
        :state="store.resourceErrors.bills"
        @retry="store.loadInitialData"
      />
      <ApiStateCard
        v-else-if="store.apiStatus === 'loading' && !categoryBills.length"
        :state="store.loadingState"
        :show-action="false"
      />
      <ApiStateCard
        v-else-if="!bills.length"
        :state="store.emptyState(selectedStage === 'all' ? '이 분야의 법안이 아직 없어요' : `${selectedStageLabel} 단계의 법안이 아직 없어요`, selectedStage === 'all' ? '백엔드 응답은 성공했지만 해당 분야에 표시할 법안이 없습니다.' : '다른 단계를 선택하면 더 많은 법안을 볼 수 있습니다.')"
        @retry="store.loadInitialData"
      />
      <template v-else>
        <BillCard v-for="bill in bills" :key="bill.id" :bill="bill" @select="store.openBill($event.id)" />
      </template>
    </div>
  </section>
</template>
