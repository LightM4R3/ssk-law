<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import ApiStateCard from "../components/ApiStateCard.vue";
import PostCard from "../components/PostCard.vue";
import PostModal from "../components/PostModal.vue";
import {
  authApi,
  getApiErrorState,
  normalizeComment,
  normalizePost,
  postApi,
} from "../services/api";
import { useAppStore } from "../stores/app";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const store = useAppStore();
const authStore = useAuthStore();

const profile = ref(null);
const activeTab = ref("posts");
const status = ref("idle");
const errorState = ref(null);
const posts = ref([]);
const comments = ref([]);
const postsStatus = ref("idle");
const commentsStatus = ref("idle");
const postsPagination = ref({ page: 0, page_size: 10, total_count: 0, total_pages: 1 });
const commentsPagination = ref({ page: 0, page_size: 10, total_count: 0, total_pages: 1 });
const activePost = ref(null);
const activePostStatus = ref("idle");
const activeFocusCommentId = ref(null);

const userIdx = computed(() => Number(route.params.idx || 0));
const isMe = computed(() => (
  authStore.isAuthenticated
  && Number(authStore.account?.idx) === userIdx.value
));
const profileNickname = computed(() => profile.value?.nickname || "사용자");
const canLoadMorePosts = computed(() => postsPagination.value.page < postsPagination.value.total_pages);
const canLoadMoreComments = computed(() => commentsPagination.value.page < commentsPagination.value.total_pages);

function billTitleFor(post) {
  const knownBill = store.allBills.find((bill) => bill.id === post.billId);
  return post.billTitle || knownBill?.title || post.billId;
}

function formatDate(value) {
  const date = String(value || "").slice(0, 10);
  return date ? date.replaceAll("-", ".") : "";
}

function commentDisplayText(comment) {
  return comment.isDeleted ? "삭제된 댓글입니다" : comment.content;
}

function resetUserPage() {
  profile.value = null;
  activeTab.value = "posts";
  status.value = "idle";
  errorState.value = null;
  posts.value = [];
  comments.value = [];
  postsStatus.value = "idle";
  commentsStatus.value = "idle";
  postsPagination.value = { page: 0, page_size: 10, total_count: 0, total_pages: 1 };
  commentsPagination.value = { page: 0, page_size: 10, total_count: 0, total_pages: 1 };
  activePost.value = null;
  activePostStatus.value = "idle";
  activeFocusCommentId.value = null;
}

async function loadProfile() {
  status.value = "loading";
  errorState.value = null;
  try {
    profile.value = await authApi.getAccount(userIdx.value);
    status.value = "ready";
  } catch (error) {
    status.value = "error";
    errorState.value = getApiErrorState(error, "사용자 정보를 불러오지 못했어요");
  }
}

async function loadPosts(page = 1) {
  if (!userIdx.value || postsStatus.value === "loading") return;
  if (page > 1 && !canLoadMorePosts.value) return;

  postsStatus.value = "loading";
  try {
    const payload = await postApi.getPosts({
      userId: userIdx.value,
      page,
      page_size: 10,
      sort: "latest",
    });
    const incoming = (payload?.posts || []).map(normalizePost);
    posts.value = page === 1 ? incoming : [...posts.value, ...incoming];
    postsPagination.value = {
      page: Number(payload?.pagination?.page || page),
      page_size: Number(payload?.pagination?.page_size || 10),
      total_count: Number(payload?.pagination?.total_count || incoming.length),
      total_pages: Number(payload?.pagination?.total_pages || 1),
    };
    postsStatus.value = "ready";
  } catch (error) {
    postsStatus.value = "error";
    errorState.value = getApiErrorState(error, "작성한 포스트를 불러오지 못했어요");
  }
}

async function loadComments(page = 1) {
  if (!userIdx.value || commentsStatus.value === "loading") return;
  if (page > 1 && !canLoadMoreComments.value) return;

  commentsStatus.value = "loading";
  try {
    const payload = await postApi.getUserComments(userIdx.value, {
      page,
      page_size: 10,
    });
    const incoming = (payload?.comments || []).map(normalizeComment);
    comments.value = page === 1 ? incoming : [...comments.value, ...incoming];
    commentsPagination.value = {
      page: Number(payload?.pagination?.page || page),
      page_size: Number(payload?.pagination?.page_size || 10),
      total_count: Number(payload?.pagination?.total_count || incoming.length),
      total_pages: Number(payload?.pagination?.total_pages || 1),
    };
    commentsStatus.value = "ready";
  } catch (error) {
    commentsStatus.value = "error";
    errorState.value = getApiErrorState(error, "작성한 댓글을 불러오지 못했어요");
  }
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

async function openPost(post) {
  const isCommentRef = Boolean(post.postIdx);
  const postIdx = isCommentRef ? post.postIdx : post.idx;
  if (!postIdx) return;

  const previewPost = isCommentRef
    ? normalizePost({
      idx: post.postIdx,
      title: post.postTitle,
      bill: post.postBillId,
      billTitle: post.billTitle,
      userIdx: userIdx.value,
      nickname: profileNickname.value,
      content: "",
      createdAt: post.createdAt,
      updatedAt: post.updatedAt,
    })
    : post;

  activePost.value = previewPost;
  activeFocusCommentId.value = isCommentRef ? post.idx : null;
  activePostStatus.value = "loading";
  document.body.style.overflow = "hidden";

  try {
    const detail = normalizePost(await postApi.getPost(postIdx));
    replacePost(detail);
    activePost.value = {
      ...detail,
      billTitle: detail.billTitle || post.billTitle || billTitleFor(detail),
    };
    activePostStatus.value = "ready";
  } catch (error) {
    activePostStatus.value = "error";
  }
}

function closePost() {
  activePost.value = null;
  activePostStatus.value = "idle";
  activeFocusCommentId.value = null;
  document.body.style.overflow = "";
}

function openBillFromPost(post) {
  if (!post?.billId && !post?.postBillId) return;
  closePost();
  store.openBill(post.billId || post.postBillId);
}

function openUserPage(idx) {
  if (!idx) return;
  closePost();
  router.push({ name: "user-page", params: { idx } });
}

function handlePostDeleted(postIdx) {
  posts.value = posts.value.filter((post) => post.idx !== postIdx);
  closePost();
}

async function initialize() {
  if (!userIdx.value) return;
  resetUserPage();
  await loadProfile();
  await Promise.all([loadPosts(1), loadComments(1)]);
}

onMounted(initialize);

watch(() => route.params.idx, () => {
  document.body.style.overflow = "";
  initialize();
});
</script>

<template>
  <section class="view active post-view user-page">
    <div class="user-page-head">
      <div>
        <p>{{ isMe ? "내정보" : "사용자 정보" }}</p>
        <h2>{{ profileNickname }}</h2>
      </div>
      <span v-if="isMe" class="user-page-badge">나의 활동</span>
    </div>

    <ApiStateCard
      v-if="status === 'error'"
      :state="errorState"
      @retry="initialize"
    />

    <template v-else>
      <div class="post-sort-tabs user-page-tabs" aria-label="마이페이지 탭">
        <button
          type="button"
          :class="{ active: activeTab === 'posts' }"
          @click="activeTab = 'posts'"
        >
          포스트
        </button>
        <button
          type="button"
          :class="{ active: activeTab === 'comments' }"
          @click="activeTab = 'comments'"
        >
          댓글
        </button>
      </div>

      <div v-if="activeTab === 'posts'" class="post-feed user-page-feed">
        <ApiStateCard
          v-if="postsStatus === 'loading' && !posts.length"
          :state="store.loadingState"
          :show-action="false"
        />
        <ApiStateCard
          v-else-if="!posts.length"
          :state="store.emptyState('작성한 포스트가 없습니다.', '아직 이 사용자가 작성한 포스트가 없습니다.')"
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
          <button
            v-if="canLoadMorePosts"
            class="post-load-more"
            type="button"
            :disabled="postsStatus === 'loading'"
            @click="loadPosts(postsPagination.page + 1)"
          >
            {{ postsStatus === "loading" ? "불러오는 중" : "더 불러오기" }}
          </button>
        </template>
      </div>

      <div v-else class="user-comment-list">
        <ApiStateCard
          v-if="commentsStatus === 'loading' && !comments.length"
          :state="store.loadingState"
          :show-action="false"
        />
        <ApiStateCard
          v-else-if="!comments.length"
          :state="store.emptyState('작성한 댓글이 없습니다.', '아직 이 사용자가 작성한 댓글이 없습니다.')"
          :show-action="false"
        />
        <template v-else>
          <article
            v-for="comment in comments"
            :key="comment.idx"
            class="user-comment-card"
            tabindex="0"
            @click="openPost(comment)"
            @keydown.enter="openPost(comment)"
          >
            <div>
              <strong>{{ comment.postTitle || `포스트 #${comment.postIdx}` }}</strong>
              <span>{{ comment.billTitle || comment.postBillId }}</span>
            </div>
            <p :class="{ deleted: comment.isDeleted }">{{ commentDisplayText(comment) }}</p>
            <small>{{ formatDate(comment.updatedAt || comment.createdAt) }}</small>
          </article>
          <button
            v-if="canLoadMoreComments"
            class="post-load-more"
            type="button"
            :disabled="commentsStatus === 'loading'"
            @click="loadComments(commentsPagination.page + 1)"
          >
            {{ commentsStatus === "loading" ? "불러오는 중" : "더 불러오기" }}
          </button>
        </template>
      </div>
    </template>

    <PostModal
      v-if="activePost"
      :post="activePost"
      :bill-title="billTitleFor(activePost)"
      :focus-comment-id="activeFocusCommentId"
      :class="{ 'is-loading-detail': activePostStatus === 'loading' }"
      @close="closePost"
      @open-bill="openBillFromPost"
      @open-user="openUserPage"
      @updated="replacePost"
      @deleted="handlePostDeleted"
    />
  </section>
</template>
