<script setup>
defineProps({
  state: {
    type: Object,
    required: true,
  },
  actionLabel: {
    type: String,
    default: "다시 시도",
  },
  showAction: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(["retry"]);
</script>

<template>
  <article class="api-state-card" role="status" aria-live="polite">
    <div class="api-state-mark">슥</div>
    <div class="api-state-body">
      <div class="api-state-kicker">
        <span v-if="state.status">HTTP {{ state.status }}</span>
        <span v-else>연결 대기</span>
        <span v-if="state.code">· {{ state.code }}</span>
      </div>
      <h3>{{ state.title }}</h3>
      <p>{{ state.message }}</p>
      <button v-if="showAction" class="api-state-action" type="button" @click="emit('retry')">
        <span>{{ actionLabel }}</span>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M21 12a9 9 0 0 1-15.2 6.5" />
          <path d="M3 12A9 9 0 0 1 18.2 5.5" />
          <path d="M18 2v4h-4" />
          <path d="M6 22v-4h4" />
        </svg>
      </button>
    </div>
  </article>
</template>
