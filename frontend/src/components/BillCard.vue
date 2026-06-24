<script setup>
import { computed } from "vue";

const props = defineProps({
  bill: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["select"]);

const stageClass = computed(() => {
  const order = ["proposed", "committee", "plenary", "passed"];
  const index = order.indexOf(props.bill.stage);
  return props.bill.stageClass || `s${index + 1 || 1}`;
});

const summary = computed(() => {
  if (props.bill.summaryText) return props.bill.summaryText;
  if (Array.isArray(props.bill.summary)) {
    const summaryText = props.bill.summary.filter(Boolean).join(" ");
    if (summaryText) return summaryText;
  }
  if (props.bill.summary && !Array.isArray(props.bill.summary)) return String(props.bill.summary);
  return "요약 준비 중입니다.";
});
</script>

<template>
  <article class="card" :class="[bill.span || 'span-2', { compact: bill.compact }]" tabindex="0" @click="emit('select', bill)" @keydown.enter="emit('select', bill)">
    <div class="card-shine"></div>

    <div class="card-meta">
      <div class="tag-row">
        <span
          v-for="cat in bill.cats"
          :key="cat.k"
          class="tag"
          :class="{ accent: cat.accent }"
          :data-cat="cat.k"
        >
          {{ cat.label }}
        </span>
      </div>
    </div>

    <h3>{{ bill.title }}</h3>
    <p class="summary">{{ summary }}</p>

    <div class="card-foot">
      <span class="stage">
        <span class="stage-dot" :class="stageClass"></span>
        {{ bill.stageLabel || bill.stage }}
      </span>
      <span class="foot-date">{{ bill.proposedAt }}</span>
      <span class="suk-hint">슥 보기</span>
    </div>
  </article>
</template>
