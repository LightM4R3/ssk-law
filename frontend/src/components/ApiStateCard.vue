<script setup>
import { computed } from "vue";

const props = defineProps({
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

const resolvedActionLabel = computed(() => (
  props.state.actionLabel || props.actionLabel
));
const kickerLabel = computed(() => {
  if (props.state.status >= 500) return "서버 오류";
  if (props.state.status >= 400) return "요청 오류";
  if (props.state.status === 0) return "연결 오류";
  if (props.state.action === "reload") return "화면 오류";
  return "연결 대기";
});

function handleAction() {
  if (props.state.action === "reload") {
    window.location.reload();
    return;
  }
  emit("retry");
}
</script>

<template>
  <article class="api-state-card" role="status" aria-live="polite">
    <div class="api-state-mark">슥</div>
    <div class="api-state-body">
      <div class="api-state-kicker">
        <span>{{ kickerLabel }}</span>
      </div>
      <h3>{{ state.title }}</h3>
      <p>{{ state.message }}</p>
      <button v-if="showAction" class="api-state-action" type="button" @click="handleAction">
        <span>{{ resolvedActionLabel }}</span>
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
