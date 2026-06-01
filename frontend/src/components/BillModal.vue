<script setup>
import { computed, onMounted, onUnmounted } from "vue";
import { useAppStore } from "../stores/app";

const props = defineProps({
  bill: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["close", "openSimilar"]);
const store = useAppStore();
const stageOrder = ["proposed", "committee", "plenary", "passed"];
const stage = computed(() => store.stageMeta(props.bill.stage));
const summary = computed(() => Array.isArray(props.bill.summary) ? props.bill.summary : [props.bill.summaryText || props.bill.summary]);

function closeOnEscape(event) {
  if (event.key === "Escape") {
    emit("close");
  }
}

onMounted(() => document.addEventListener("keydown", closeOnEscape));
onUnmounted(() => document.removeEventListener("keydown", closeOnEscape));
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal" role="dialog" aria-modal="true">
      <div class="modal-head">
        <div>
          <div class="tag-row" style="margin-bottom: 6px;">
            <span
              v-for="cat in bill.cats"
              :key="cat.k"
              class="tag"
              :class="{ accent: cat.accent }"
            >
              {{ cat.label }}
            </span>
          </div>
          <h2>{{ bill.title }}</h2>
          <div class="modal-meta">
            <span><b>발의일</b> {{ bill.proposedAt }}</span>
            <span><b>대표 발의</b> {{ bill.proposer }}</span>
            <span><b>법안번호</b> 의안 2126-{{ bill.id.toUpperCase() }}</span>
          </div>
        </div>
        <button class="close" type="button" aria-label="닫기" @click="emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>
      </div>

      <div class="modal-body">
        <div class="modal-stage">
          <div class="modal-stage-head">
            <div>현재 단계 · <span>{{ stage.label }}</span></div>
            <div>최근 업데이트 2026.05.13</div>
          </div>
          <div class="stage-track">
            <div
              v-for="step in stageOrder"
              :key="step"
              class="stage-step"
              :class="{ done: store.stageMeta(step).idx < stage.idx, active: store.stageMeta(step).idx === stage.idx }"
            ></div>
          </div>
          <div class="stage-labels">
            <span
              v-for="step in stageOrder"
              :key="step"
              :class="{ active: store.stageMeta(step).idx === stage.idx }"
            >
              {{ store.stageLabel(step) }}
            </span>
          </div>
        </div>

        <div class="modal-section">
          <h4>세 줄 요약</h4>
          <ul>
            <li v-for="line in summary" :key="line">{{ line }}</li>
          </ul>
        </div>

        <div v-if="bill.impact" class="modal-section">
          <h4>예상 영향</h4>
          <p>{{ bill.impact }}</p>
        </div>

        <div v-if="bill.similar?.length" class="modal-section">
          <h4>유사 법안 {{ bill.similar.length }}건</h4>
          <div class="similar">
            <button
              v-for="(item, index) in bill.similar"
              :key="item.title"
              class="similar-item"
              type="button"
              @click="emit('openSimilar', { parentId: bill.id, index })"
            >
              <div>
                <div class="similar-title">{{ item.title }}</div>
                <div class="similar-meta">{{ item.date }} · {{ item.stage }}</div>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--ink-4);" aria-hidden="true">
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-ghost" type="button">공유</button>
          <button class="btn btn-ghost" type="button">원문 보기</button>
        </div>
      </div>
    </div>
  </div>
</template>
