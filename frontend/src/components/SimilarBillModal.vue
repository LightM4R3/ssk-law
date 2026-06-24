<script setup>
import { computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAppStore } from "../stores/app";

const props = defineProps({
  parent: {
    type: Object,
    required: true,
  },
  similar: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    required: true,
  },
});

const emit = defineEmits(["close", "openParent"]);
const router = useRouter();
const store = useAppStore();
const stageOrder = ["proposed", "committee", "plenary", "passed"];
const stageKey = computed(() => store.stageKeyFromLabel(props.similar.stage));
const stage = computed(() => store.stageMeta(stageKey.value));
const parentStage = computed(() => store.stageMeta(props.parent.stage));
const parentSummary = computed(() => Array.isArray(props.parent.summary) ? props.parent.summary[0] : props.parent.summaryText);
const lastStageIndex = stageOrder.length - 1;
const stageProgress = computed(() => `${(stage.value.idx / lastStageIndex) * 100}%`);
const stagePoints = computed(() => stageOrder.map((step, index) => {
  const meta = store.stageMeta(step);
  return {
    step,
    label: store.stageLabel(step),
    left: `${(index / lastStageIndex) * 100}%`,
    active: meta.idx === stage.value.idx,
    done: meta.idx < stage.value.idx,
    first: index === 0,
    last: index === lastStageIndex,
  };
}));

function closeOnEscape(event) {
  if (event.key === "Escape") {
    emit("close");
  }
}

function openSimilarPage() {
  const parentId = props.parent.id;
  emit("close");
  router.push({ name: "similar", params: { id: parentId } });
}

onMounted(() => document.addEventListener("keydown", closeOnEscape));
onUnmounted(() => document.removeEventListener("keydown", closeOnEscape));
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal" role="dialog" aria-modal="true">
      <div class="modal-head">
        <div>
          <div class="tag-row" style="margin-bottom: 8px;">
            <span class="tag accent">유사 법안</span>
            <span
              v-for="cat in parent.cats"
              :key="cat.k"
              class="tag"
              :class="{ accent: cat.accent }"
            >
              {{ cat.label }}
            </span>
          </div>
          <h2>{{ similar.title }}</h2>
          <div class="modal-meta">
            <span><b>발의일</b> {{ similar.date }}</span>
            <span><b>현재 단계</b> {{ similar.stage }}</span>
            <span><b>관련 법안</b> {{ parent.title }}</span>
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
            <div>발의일 {{ similar.date }}</div>
          </div>
          <div class="stage-track" :style="{ '--stage-progress': stageProgress }">
            <span class="stage-line"></span>
            <span class="stage-fill"></span>
            <span
              v-for="point in stagePoints"
              :key="point.step"
              class="stage-node"
              :class="{ done: point.done, active: point.active }"
              :style="{ left: point.left }"
              aria-hidden="true"
            ></span>
          </div>
          <div class="stage-labels">
            <span
              v-for="point in stagePoints"
              :key="point.step"
              class="stage-label"
              :class="{ active: point.active, first: point.first, last: point.last }"
              :style="{ left: point.left }"
            >
              {{ point.label }}
            </span>
          </div>
        </div>

        <div class="modal-section">
          <h4>이 법안 한 줄로</h4>
          <p>
            <strong>{{ parent.title }}</strong>과 유사한 주제·정책 방향을 다루는 발의안으로 슥법이 분류했어요.
            현재 <strong>{{ similar.stage }}</strong> 단계에 있으며,
            {{ parent.cats.map((cat) => cat.label).join(" · ") }} 분야에 속합니다.
          </p>
        </div>

        <div class="modal-section">
          <h4>원본 법안</h4>
          <button class="sim-parent" type="button" @click="emit('openParent')">
            <div class="sim-parent-top">
              <div class="tag-row">
                <span
                  v-for="cat in parent.cats"
                  :key="cat.k"
                  class="tag"
                  :class="{ accent: cat.accent }"
                >
                  {{ cat.label }}
                </span>
              </div>
              <span class="sim-parent-stage">
                <span class="stage-dot" :class="parentStage.cls"></span>
                {{ parentStage.label }}
              </span>
            </div>
            <div class="sim-parent-title">{{ parent.title }}</div>
            <div class="sim-parent-summary">{{ parentSummary }}</div>
            <div class="sim-parent-foot">
              <span>{{ parent.proposedAt }} · {{ parent.proposer }}</span>
              <span class="sim-parent-cta">슥, 원본 보기</span>
            </div>
          </button>
        </div>

        <div class="modal-section sim-pending">
          <div class="sim-pending-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 8v4l3 2" />
            </svg>
          </div>
          <div>
            <div class="sim-pending-title">슥법이 시민의 언어로 정리 중이에요</div>
            <div class="sim-pending-text">이 법안의 세 줄 요약·예상 영향·전체 조문은 곧 추가될 예정입니다. 그동안은 원본 법안 카드를 통해 맥락을 슥 둘러보세요.</div>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-primary" type="button" @click="emit('openParent')">원본 법안 보기</button>
          <button class="btn btn-ghost" type="button" @click="openSimilarPage">유사 법안 전체 보기</button>
          <button class="btn btn-ghost" type="button">원문 보기</button>
        </div>
      </div>
    </div>
  </div>
</template>
