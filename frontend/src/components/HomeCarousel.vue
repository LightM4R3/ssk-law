<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useAppStore } from "../stores/app";

const props = defineProps({
  picks: {
    type: Array,
    required: true,
  },
  eyebrow: {
    type: String,
    default: "추천 법안",
  },
});

const emit = defineEmits(["select", "selectSimilar"]);
const router = useRouter();
const store = useAppStore();
const viewport = ref(null);
const index = ref(0);
const width = ref(0);
const dragging = ref(false);
const startX = ref(0);
const dragX = ref(0);
const wasDrag = ref(false);
const stageOrder = ["proposed", "committee", "plenary", "passed"];

const transform = computed(() => `translateX(${(-index.value * width.value) + dragX.value}px)`);

function measure() {
  width.value = viewport.value?.getBoundingClientRect().width || 0;
}

function goTo(nextIndex) {
  index.value = Math.max(0, Math.min(props.picks.length - 1, nextIndex));
  dragX.value = 0;
}

function pointerDown(event) {
  if (event.target.closest(".pick-cta")) return;
  dragging.value = true;
  wasDrag.value = false;
  startX.value = event.clientX;
}

function pointerMove(event) {
  if (!dragging.value) return;
  const dx = event.clientX - startX.value;
  if (Math.abs(dx) > 8) wasDrag.value = true;
  dragX.value = dx * 0.7;
}

function pointerUp() {
  if (!dragging.value) return;
  dragging.value = false;
  const threshold = width.value * 0.35;
  if (dragX.value < -threshold) goTo(index.value + 1);
  else if (dragX.value > threshold) goTo(index.value - 1);
  else goTo(index.value);
  window.setTimeout(() => {
    wasDrag.value = false;
  }, 80);
}

function openPick(pick) {
  if (!wasDrag.value) emit("select", pick);
}

function openSimilarPage(pick) {
  router.push({ name: "similar", params: { id: pick.id } });
}

function onKeydown(event) {
  if (event.target?.tagName === "INPUT") return;
  if (event.key === "ArrowRight") goTo(index.value + 1);
  if (event.key === "ArrowLeft") goTo(index.value - 1);
}

watch(() => props.picks.length, () => nextTick(measure));

onMounted(() => {
  nextTick(measure);
  window.addEventListener("resize", measure);
  window.addEventListener("keydown", onKeydown);
});

onUnmounted(() => {
  window.removeEventListener("resize", measure);
  window.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <div class="carousel">
    <div
      ref="viewport"
      class="carousel-viewport"
      @pointerdown="pointerDown"
      @pointermove="pointerMove"
      @pointerup="pointerUp"
      @pointercancel="pointerUp"
      @pointerleave="pointerUp"
    >
      <div class="carousel-track" :class="{ dragging }" :style="{ transform }">
        <div v-for="(pick, pickIndex) in picks" :key="pick.id" class="carousel-slide" :data-i="pickIndex" @click="openPick(pick)">
          <article class="pick" :class="{ 'in-view': pickIndex === index }">
            <div class="pick-shine"></div>
            <div class="pick-num">{{ String(pickIndex + 1).padStart(2, "0") }} <span>/ {{ String(picks.length).padStart(2, "0") }}</span></div>
            <div class="pick-body">
              <div class="pick-main">
                <span class="pick-eyebrow">{{ eyebrow }}</span>
                <div class="pick-cats">
                  <span v-for="cat in pick.cats" :key="cat.k" class="tag" :class="{ accent: cat.accent }">{{ cat.label }}</span>
                </div>
                <h2>{{ pick.title }}</h2>
                <ul class="summary">
                  <li v-for="line in pick.summary" :key="line">{{ line }}</li>
                </ul>
                <div class="pick-meta">
                  <span><b>발의일</b> {{ pick.proposedAt }}</span>
                  <span><b>대표 발의</b> {{ pick.proposer }}</span>
                </div>
                <button class="pick-cta" type="button" @click.stop="emit('select', pick)">
                  슥, 자세히 보기
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M5 12h14" />
                    <path d="m13 5 7 7-7 7" />
                  </svg>
                </button>
              </div>

              <aside v-if="pick.similar?.length" class="pick-side">
                <div class="pick-side-head">
                  <span class="pick-side-eyebrow">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="m9 6 6 6-6 6" />
                    </svg>
                    유사한 법안 슥 보기
                  </span>
                  <span class="pick-side-count">{{ pick.similar.length }}건</span>
                </div>
                <div class="pick-side-list">
                  <button
                    v-for="(similar, similarIndex) in pick.similar.slice(0, 2)"
                    :key="similar.title"
                    class="pick-sim"
                    type="button"
                    @click.stop="emit('selectSimilar', { parentId: pick.id, index: similarIndex })"
                  >
                    <div class="pick-sim-top">
                      <span class="pick-sim-num">{{ String(similarIndex + 1).padStart(2, "0") }}</span>
                      <span class="pick-sim-stage">{{ similar.stage }}</span>
                    </div>
                    <div class="pick-sim-title">{{ similar.title }}</div>
                    <div class="pick-sim-meta">
                      <span>{{ similar.date }}</span>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="M5 12h14" />
                        <path d="m13 5 7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                </div>
                <button class="pick-sim-more" type="button" @click.stop="openSimilarPage(pick)">
                  유사 법안 더 보기
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="m9 6 6 6-6 6" />
                  </svg>
                </button>
              </aside>
            </div>

            <div class="pick-foot">
              <div class="stage-block">
                <h4>입법 단계</h4>
                <div class="stage-track">
                  <div
                    v-for="step in stageOrder"
                    :key="step"
                    class="stage-step"
                    :class="{ done: store.stageMeta(step).idx < store.stageMeta(pick.stage).idx, active: store.stageMeta(step).idx === store.stageMeta(pick.stage).idx }"
                  ></div>
                </div>
                <div class="stage-labels">
                  <span
                    v-for="step in stageOrder"
                    :key="step"
                    :class="{ active: store.stageMeta(step).idx === store.stageMeta(pick.stage).idx }"
                  >
                    {{ store.stageLabel(step) }}
                  </span>
                </div>
              </div>
            </div>
          </article>
        </div>
      </div>
    </div>

    <div class="carousel-controls">
      <div class="carousel-dots">
        <button
          v-for="(_, dotIndex) in picks"
          :key="dotIndex"
          class="dot"
          :class="{ active: dotIndex === index }"
          type="button"
          :aria-label="`${dotIndex + 1}번`"
          @click="goTo(dotIndex)"
        ></button>
      </div>
      <div class="swipe-hint">
        <span>슥 넘기기</span>
        <span class="key">←</span>
        <span class="key">→</span>
      </div>
      <div class="carousel-arrows">
        <button class="arrow" type="button" aria-label="이전" :disabled="index === 0" @click="goTo(index - 1)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>
        <button class="arrow" type="button" aria-label="다음" :disabled="index === picks.length - 1" @click="goTo(index + 1)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="m9 18 6-6-6-6" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>
