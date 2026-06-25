<script setup>
import { computed, watch } from "vue";
import { useRouter } from "vue-router";

import { useAppStore } from "../stores/app";

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
});

const router = useRouter();
const store = useAppStore();
const stageOrder = ["proposed", "committee", "plenary", "passed"];
const parent = computed(() => store.allBills.find((bill) => bill.id === props.id));
const dominantCategory = computed(() => {
  if (!parent.value?.cats?.length) return null;
  return parent.value.cats.find((cat) => cat.accent) || parent.value.cats[0];
});
const categoryMeta = computed(() => store.categories.find((cat) => cat.id === dominantCategory.value?.k));
const parentStage = computed(() => parent.value ? store.stageMeta(parent.value.stage) : null);
const parentSummary = computed(() => {
  if (!parent.value) return "";
  return Array.isArray(parent.value.summary) ? parent.value.summary[0] : parent.value.summaryText;
});
const isLoadingSimilar = computed(() => Boolean(parent.value && store.similarLoading[parent.value.id]));
const similarError = computed(() => (parent.value ? store.similarErrors[parent.value.id] : null));

function openParent() {
  if (parent.value) {
    store.openBill(parent.value.id);
  }
}

function openSimilar(index) {
  if (parent.value) {
    store.openSimilar(parent.value.id, index);
  }
}

function goHome() {
  router.push({ name: "home" });
}

watch(() => parent.value?.id, (id) => {
  if (!id) return;
  store.loadSimilarBills(id, { limit: 10 });
}, { immediate: true });
</script>

<template>
  <section v-if="parent" class="view active">
    <button class="similar-crumb" type="button" @click="goHome">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M19 12H5" />
        <path d="m12 19-7-7 7-7" />
      </svg>
      <span>홈으로</span>
    </button>

    <section class="cat-hero similar-hero" :style="{ '--cat-h': categoryMeta?.hue || 245 }">
      <div class="cat-hero-glyph">{{ categoryMeta?.glyph || "슥" }}</div>
      <div class="cat-hero-text">
        <div class="similar-hero-eyebrow">이 법안과 유사한 법안</div>
        <h1>{{ parent.title }}</h1>
        <div class="similar-hero-cats">
          <span
            v-for="cat in parent.cats"
            :key="cat.k"
            class="tag"
            :class="{ accent: cat.accent }"
          >
            {{ cat.label }}
          </span>
        </div>
        <div class="similar-hero-meta">
          <span><b>발의일</b> {{ parent.proposedAt }}</span>
          <span><b>대표 발의</b> {{ parent.proposer }}</span>
          <span class="similar-hero-stage">
            <span class="stage-dot" :class="parentStage.cls"></span>
            {{ parentStage.label }}
          </span>
        </div>
        <p class="desc">슥법이 함께 살펴볼 만한 법안 {{ parent.similar?.length || 0 }}건을 모았어요. 카드를 클릭하면 해당 법안의 상세를 슥 들여다볼 수 있어요.</p>
      </div>
      <div class="cat-hero-stats">
        <span class="cat-hero-stat-num">{{ parent.similar?.length || 0 }}</span>
        <span class="cat-hero-stat-label">유사 법안</span>
        <button class="similar-hero-cta" type="button" @click="openParent">
          원본 법안 보기
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14" />
            <path d="m13 5 7 7-7 7" />
          </svg>
        </button>
      </div>
    </section>

    <div class="section-head" style="margin: 4px 0 16px;">
      <div>
        <h2 style="font-size: 22px;">유사한 법안 {{ parent.similar?.length || 0 }}건</h2>
        <div class="sub">슥법은 분야·정책 방향·키워드를 종합해 유사 법안을 묶어요.</div>
      </div>
    </div>

    <div v-if="isLoadingSimilar" class="similar-empty">
      유사 법안을 불러오는 중입니다.
    </div>

    <div v-else-if="similarError" class="similar-empty">
      {{ similarError.message }}
    </div>

    <div v-else-if="parent.similar?.length" class="similar-grid">
      <article
        v-for="(similar, index) in parent.similar"
        :key="similar.title"
        class="similar-card"
        tabindex="0"
        :style="{ '--delay': `${index * 60}ms` }"
        @click="openSimilar(index)"
        @keydown.enter="openSimilar(index)"
      >
        <div class="similar-card-top">
          <span class="similar-card-num">{{ String(index + 1).padStart(2, "0") }}</span>
          <span class="similar-card-stage">
            <span class="stage-dot" :class="store.stageMeta(store.stageKeyFromLabel(similar.stage)).cls"></span>
            {{ similar.stage }}
          </span>
        </div>
        <h3 class="similar-card-title">{{ similar.title }}</h3>
        <div class="similar-card-cats">
          <span
            v-for="cat in parent.cats"
            :key="cat.k"
            class="tag"
            :class="{ accent: cat.accent }"
          >
            {{ cat.label }}
          </span>
        </div>
        <div class="similar-card-foot">
          <span>{{ similar.date }}</span>
          <span class="similar-card-cta">슥 들어가기</span>
        </div>
      </article>
    </div>

    <div v-else class="similar-empty">
      아직 분류된 유사 법안이 없어요. 슥법이 새 법안을 추적해 곧 추가할 예정입니다.
    </div>
  </section>

  <section v-else class="view active">
    <div class="similar-empty">
      법안을 찾을 수 없습니다.
    </div>
  </section>
</template>
