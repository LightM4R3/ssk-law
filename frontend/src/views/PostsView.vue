<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import ApiStateCard from "../components/ApiStateCard.vue";
import PostCard from "../components/PostCard.vue";
import PostModal from "../components/PostModal.vue";
import { getApiErrorState, normalizePost, postApi } from "../services/api";
import { useAppStore } from "../stores/app";
import { useAuthStore } from "../stores/auth";

const store = useAppStore();
const authStore = useAuthStore();
const router = useRouter();
const posts = ref([]);
const pagination = ref({
  page: 0,
  page_size: 10,
  total_count: 0,
  total_pages: 1,
});
const status = ref("idle");
const errorState = ref(null);
const sentinel = ref(null);
const activePost = ref(null);
const activePostStatus = ref("idle");
const activeSort = ref("latest");
let observer = null;

const isInitialLoading = computed(() => status.value === "loading" && posts.value.length === 0);
const isLoadingMore = computed(() => status.value === "loading" && posts.value.length > 0);
const hasMore = computed(() => pagination.value.page < pagination.value.total_pages);

function billTitleFor(post) {
  const knownBill = store.allBills.find((bill) => bill.id === post.billId);
  return post.billTitle || knownBill?.title || post.billId;
}

function replacePost(updatedPost) {
  posts.value = posts.value.map((post) => (
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

async function loadPosts(page = 1, sort = activeSort.value) {
  if (status.value === "loading") return;
  if (page > 1 && !hasMore.value) return;

  status.value = "loading";
  errorState.value = null;

  try {
    const payload = await postApi.getPosts({ page, page_size: 10, sort });
    const incoming = (payload?.posts || []).map(normalizePost);

    posts.value = page === 1 ? incoming : [...posts.value, ...incoming];
    pagination.value = {
      page: Number(payload?.pagination?.page || page),
      page_size: Number(payload?.pagination?.page_size || 10),
      total_count: Number(payload?.pagination?.total_count || incoming.length),
      total_pages: Number(payload?.pagination?.total_pages || 1),
    };
    status.value = "ready";

    await nextTick();
    observeSentinel();
  } catch (error) {
    status.value = "error";
    errorState.value = getApiErrorState(error, "포스트를 불러오지 못하고 있어요");
  }
}

function changeSort(sort) {
  if (activeSort.value === sort && posts.value.length) return;
  activeSort.value = sort;
  posts.value = [];
  pagination.value = {
    page: 0,
    page_size: 10,
    total_count: 0,
    total_pages: 1,
  };
  loadPosts(1, sort);
}

function loadNextPage() {
  if (!hasMore.value || status.value === "loading") return;
  loadPosts(pagination.value.page + 1);
}

async function openPost(post) {
  activePost.value = post;
  activePostStatus.value = "loading";
  document.body.style.overflow = "hidden";

  try {
    const detail = normalizePost(await postApi.getPost(post.idx));
    replacePost(detail);
    activePostStatus.value = "ready";
  } catch (error) {
    activePostStatus.value = "error";
  }
}

function closePost() {
  activePost.value = null;
  activePostStatus.value = "idle";
  document.body.style.overflow = "";
}

function openBillFromPost(post) {
  if (!post?.billId) return;
  store.openBill(post.billId);
}

function openUserPage(userIdx) {
  if (!userIdx) return;
  closePost();
  if (store.activeBill) store.closeBill();
  if (store.activeSimilarData) store.closeSimilar();
  router.push({ name: "user-page", params: { idx: userIdx } });
}

function handlePostUpdated(updatedPost) {
  replacePost(updatedPost);
}

function handlePostDeleted(postIdx) {
  posts.value = posts.value.filter((post) => post.idx !== postIdx);
  pagination.value = {
    ...pagination.value,
    total_count: Math.max(0, pagination.value.total_count - 1),
  };
  closePost();
}

function observeSentinel() {
  if (!sentinel.value || !("IntersectionObserver" in window)) return;

  if (!observer) {
    observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        loadNextPage();
      }
    }, { rootMargin: "260px 0px" });
  }

  observer.disconnect();
  observer.observe(sentinel.value);
}

onMounted(() => {
  loadPosts(1);
});

watch(
  () => store.activeBill,
  (activeBill) => {
    if (activePost.value && !activeBill) {
      document.body.style.overflow = "hidden";
    }
  },
);

onBeforeUnmount(() => {
  if (observer) observer.disconnect();
  document.body.style.overflow = "";
});
</script>

<template>
  <section class="view active post-view">
    <div class="section-head">
      <div>
        <h2>포스트</h2>
        <div class="sub">슥 내려보며 법안에 대한 이야기를 확인해보세요</div>
      </div>
      <div class="post-sort-tabs" aria-label="포스트 정렬">
        <button
          type="button"
          :class="{ active: activeSort === 'latest' }"
          @click="changeSort('latest')"
        >
          최신순
        </button>
        <button
          type="button"
          :class="{ active: activeSort === 'popular' }"
          @click="changeSort('popular')"
        >
          인기순
        </button>
      </div>
    </div>

    <div class="post-feed">
      <ApiStateCard
        v-if="errorState && !posts.length"
        :state="errorState"
        @retry="loadPosts(1)"
      />
      <ApiStateCard
        v-else-if="isInitialLoading"
        :state="store.loadingState"
        :show-action="false"
      />
      <ApiStateCard
        v-else-if="!posts.length"
        :state="store.emptyState('아직 작성된 포스트가 없어요', '첫 포스트가 작성되면 이곳에 10개 단위로 표시됩니다.')"
        :show-action="false"
      />

      <template v-else>
        <PostCard
          v-for="post in posts"
          :key="post.idx"
          :post="post"
          :bill-title="billTitleFor(post)"
          :is-owned="Number(authStore.account?.idx) === Number(post.userIdx)"
          @select="openPost"
          @open-bill="openBillFromPost"
          @open-user="openUserPage"
        />
      </template>

      <div ref="sentinel" class="post-load-sentinel" aria-hidden="true"></div>

      <div v-if="isLoadingMore" class="post-loading-more" role="status">
        <span></span>
        <b>다음 포스트를 불러오는 중</b>
      </div>
      <button
        v-else-if="hasMore"
        class="post-load-more"
        type="button"
        @click="loadNextPage"
      >
        더 불러오기
      </button>
      <div v-else-if="posts.length" class="post-end">
        모든 포스트를 확인했어요.
      </div>
    </div>

    <PostModal
      v-if="activePost"
      :post="activePost"
      :bill-title="billTitleFor(activePost)"
      :class="{ 'is-loading-detail': activePostStatus === 'loading' }"
      @close="closePost"
      @open-bill="openBillFromPost"
      @open-user="openUserPage"
      @updated="handlePostUpdated"
      @deleted="handlePostDeleted"
    />
  </section>
</template>
