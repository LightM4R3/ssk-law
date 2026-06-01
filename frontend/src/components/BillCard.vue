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

const summary = computed(() => props.bill.summaryText || props.bill.summary);
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
