<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import PostModal from "./PostModal.vue";
import { getApiErrorState, normalizePost, postApi } from "../services/api";
import { useAppStore } from "../stores/app";
import { useAuthStore } from "../stores/auth";

const props = defineProps({
  bill: {
    type: Object,
    required: true,
  },
  createdPost: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["close", "openSimilar", "writePost"]);
const store = useAppStore();
const authStore = useAuthStore();
const router = useRouter();
const billPosts = ref([]);
const billPostsStatus = ref("idle");
const billPostsError = ref(null);
const activePost = ref(null);
const stageOrder = ["proposed", "committee", "plenary", "passed"];
const stage = computed(() => store.stageMeta(props.bill.stage));
const summary = computed(() => {
  if (Array.isArray(props.bill.summary)) {
    const lines = props.bill.summary.filter(Boolean);
    return lines.length ? lines : ["요약 준비 중입니다."];
  }
  const summaryText = props.bill.summaryText || props.bill.summary || props.bill.impact;
  return summaryText ? [String(summaryText)] : ["요약 준비 중입니다."];
});
const billNumber = computed(() => props.bill.billNo ? `의안 ${props.bill.billNo}` : props.bill.id);
const syncedDate = computed(() => {
  if (!props.bill.syncedAt) return "";
  return String(props.bill.syncedAt).slice(0, 10).replaceAll("-", ".");
});

function openDetailLink() {
  if (props.bill.detailLink) {
    window.open(props.bill.detailLink, "_blank", "noopener,noreferrer");
  }
}

async function loadBillPosts() {
  if (!props.bill?.id) return;

  billPostsStatus.value = "loading";
  billPostsError.value = null;
  try {
    const payload = await postApi.getPosts({
      billId: props.bill.id,
      page: 1,
      page_size: 5,
      sort: "latest",
    });
    billPosts.value = (payload?.posts || []).map(normalizePost);
    billPostsStatus.value = "ready";
  } catch (error) {
    billPostsStatus.value = "error";
    billPostsError.value = getApiErrorState(error, "포스트를 불러오지 못했어요");
  }
}

function prependCreatedPost(post) {
  if (!post || !props.bill?.id) return;

  const normalizedPost = normalizePost({
    ...post,
    billTitle: post.billTitle || props.bill.title,
  });

  if (String(normalizedPost.billId) !== String(props.bill.id)) return;

  billPosts.value = [
    normalizedPost,
    ...billPosts.value.filter((item) => item.idx !== normalizedPost.idx),
  ].slice(0, 5);
  billPostsStatus.value = "ready";
  billPostsError.value = null;
}

async function openPost(post) {
  activePost.value = post;
  try {
    activePost.value = {
      ...post,
      ...normalizePost(await postApi.getPost(post.idx)),
      billTitle: post.billTitle || props.bill.title,
    };
  } catch (error) {
    activePost.value = post;
  }
}

function closePost() {
  activePost.value = null;
}

function handlePostUpdated(updatedPost) {
  billPosts.value = billPosts.value.map((post) => (
    post.idx === updatedPost.idx
      ? { ...post, ...updatedPost, billTitle: updatedPost.billTitle || post.billTitle }
      : post
  ));
  if (activePost.value?.idx === updatedPost.idx) {
    activePost.value = {
      ...activePost.value,
      ...updatedPost,
      billTitle: updatedPost.billTitle || activePost.value.billTitle,
    };
  }
}

function handlePostDeleted(postIdx) {
  billPosts.value = billPosts.value.filter((post) => post.idx !== postIdx);
  closePost();
}

function openUserPage(userIdx) {
  if (!userIdx) return;
  closePost();
  emit("close");
  router.push({ name: "user-page", params: { idx: userIdx } });
}

function formatPostDate(value) {
  const date = String(value || "").slice(0, 10);
  return date ? date.replaceAll("-", ".") : "";
}

function closeOnEscape(event) {
  if (event.key === "Escape") {
    emit("close");
  }
}

watch(() => props.bill?.id, () => {
  activePost.value = null;
  loadBillPosts();
}, { immediate: true });

watch(() => props.createdPost, (post) => {
  prependCreatedPost(post);
});

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
            <span><b>법안번호</b> {{ billNumber }}</span>
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
            <div v-if="syncedDate">최근 업데이트 {{ syncedDate }}</div>
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

        <div class="modal-section bill-post-preview-section">
          <h4>시민들의 의견 슥 보기</h4>
          <div v-if="billPostsStatus === 'loading'" class="bill-post-preview-state">
            포스트를 불러오는 중입니다.
          </div>
          <div v-else-if="billPostsError" class="bill-post-preview-state">
            {{ billPostsError.message }}
          </div>
          <div v-else-if="!billPosts.length" class="bill-post-preview-state">
            아직 이 법안에 대한 포스트가 없습니다.
          </div>
          <div v-else class="bill-post-preview-list">
            <button
              v-for="post in billPosts"
              :key="post.idx"
              class="bill-post-preview"
              type="button"
              @click="openPost(post)"
            >
              <div>
                <strong>{{ post.title }}</strong>
                <span>{{ post.nickname }} · {{ formatPostDate(post.updatedAt || post.createdAt) }}</span>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
          </div>
        </div>

        <div class="modal-actions">
          <button
            v-if="authStore.isAuthenticated"
            class="btn btn-blue"
            type="button"
            @click="emit('writePost', bill)"
          >
            포스트 작성하기
          </button>
          <button v-if="bill.detailLink" class="btn btn-ghost" type="button" @click="openDetailLink">원문 보기</button>
        </div>
      </div>
    </div>
    <PostModal
      v-if="activePost"
      :post="activePost"
      :bill-title="bill.title"
      @close="closePost"
      @open-bill="closePost"
      @open-user="openUserPage"
      @updated="handlePostUpdated"
      @deleted="handlePostDeleted"
    />
  </div>
</template>
