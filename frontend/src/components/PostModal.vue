<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

import PostCommentItem from "./PostCommentItem.vue";
import { getApiErrorState, normalizeComment, normalizePost, postApi } from "../services/api";
import { useAuthStore } from "../stores/auth";

const props = defineProps({
  post: {
    type: Object,
    required: true,
  },
  billTitle: {
    type: String,
    default: "",
  },
  focusCommentId: {
    type: Number,
    default: null,
  },
});

const emit = defineEmits(["close", "openBill", "openUser", "updated", "deleted"]);
const authStore = useAuthStore();
const comments = ref([]);
const commentStatus = ref("idle");
const commentError = ref(null);
const isEditing = ref(false);
const editTitle = ref("");
const editContent = ref("");
const actionError = ref("");
const isSaving = ref(false);
const isDeleting = ref(false);
const newCommentContent = ref("");
const replyParentId = ref(null);
const replyContent = ref("");
const editingCommentId = ref(null);
const editingCommentContent = ref("");
const commentActionError = ref("");
const isCommentSubmitting = ref(false);
const postModalRef = ref(null);

const isOwner = computed(() => (
  authStore.isAuthenticated
  && Number(authStore.account?.idx) === Number(props.post.userIdx)
));

const displayedCommentCount = computed(() => countActiveComments(comments.value));

function datePart(value) {
  return String(value || "").slice(0, 10);
}

function formatDate(value) {
  const date = datePart(value);
  return date ? date.replaceAll("-", ".") : "";
}

const hasEdited = computed(() => {
  if (!props.post.createdAt || !props.post.updatedAt) return false;
  const created = new Date(props.post.createdAt).getTime();
  const updated = new Date(props.post.updatedAt).getTime();
  if (!Number.isFinite(created) || !Number.isFinite(updated)) return false;
  return updated - created > 1000;
});

const displayDate = computed(() => (
  hasEdited.value ? formatDate(props.post.updatedAt) : formatDate(props.post.createdAt)
));

const editedLabel = computed(() => (
  hasEdited.value ? "수정" : ""
));

function countActiveComments(items) {
  return items.reduce((total, comment) => (
    total
    + (comment.isDeleted ? 0 : 1)
    + countActiveComments(comment.replies || [])
  ), 0);
}

function syncCommentCount() {
  emit("updated", {
    ...props.post,
    commentCount: displayedCommentCount.value,
  });
}

async function scrollToFocusedComment() {
  const targetId = Number(props.focusCommentId || 0);
  if (!targetId || commentStatus.value !== "ready") return;

  await nextTick();
  window.setTimeout(() => {
    const target = postModalRef.value?.querySelector(`[data-comment-id="${targetId}"]`);
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, 120);
}

function resetEditForm() {
  editTitle.value = props.post.title || "";
  editContent.value = props.post.content || "";
  actionError.value = "";
}

async function loadComments() {
  commentStatus.value = "loading";
  commentError.value = null;

  try {
    const payload = await postApi.getComments(props.post.idx);
    comments.value = (payload?.comments || []).map(normalizeComment);
    commentStatus.value = "ready";
    syncCommentCount();
    scrollToFocusedComment();
  } catch (error) {
    commentStatus.value = "error";
    commentError.value = getApiErrorState(error, "댓글을 불러오지 못하고 있어요");
  }
}

function resetCommentForms() {
  newCommentContent.value = "";
  replyParentId.value = null;
  replyContent.value = "";
  editingCommentId.value = null;
  editingCommentContent.value = "";
  commentActionError.value = "";
}

function startReply(comment) {
  if (!authStore.isAuthenticated) {
    commentActionError.value = "로그인 후 답글을 작성할 수 있습니다.";
    return;
  }
  replyParentId.value = comment.idx;
  replyContent.value = "";
  editingCommentId.value = null;
  commentActionError.value = "";
}

function cancelReply() {
  replyParentId.value = null;
  replyContent.value = "";
}

async function submitComment(parent = null) {
  if (isCommentSubmitting.value) return;
  if (!authStore.isAuthenticated) {
    commentActionError.value = "로그인 후 댓글을 작성할 수 있습니다.";
    return;
  }

  const content = (parent ? replyContent.value : newCommentContent.value).trim();
  if (!content) {
    commentActionError.value = "댓글 내용을 입력해주세요.";
    return;
  }

  isCommentSubmitting.value = true;
  commentActionError.value = "";
  try {
    const payload = { content };
    if (parent) payload.parentIdx = parent.idx;
    await postApi.createComment(props.post.idx, payload);
    if (parent) {
      cancelReply();
    } else {
      newCommentContent.value = "";
    }
    await loadComments();
  } catch (error) {
    commentActionError.value = getApiErrorState(error, "댓글을 저장하지 못했어요").message;
  } finally {
    isCommentSubmitting.value = false;
  }
}

function startCommentEdit(comment) {
  editingCommentId.value = comment.idx;
  editingCommentContent.value = comment.content;
  replyParentId.value = null;
  commentActionError.value = "";
}

function cancelCommentEdit() {
  editingCommentId.value = null;
  editingCommentContent.value = "";
}

async function saveCommentEdit(comment) {
  if (isCommentSubmitting.value) return;
  const content = editingCommentContent.value.trim();
  if (!content) {
    commentActionError.value = "댓글 내용을 입력해주세요.";
    return;
  }

  isCommentSubmitting.value = true;
  commentActionError.value = "";
  try {
    await postApi.updateComment(comment.idx, { content });
    cancelCommentEdit();
    await loadComments();
  } catch (error) {
    commentActionError.value = getApiErrorState(error, "댓글을 수정하지 못했어요").message;
  } finally {
    isCommentSubmitting.value = false;
  }
}

async function deleteComment(comment) {
  if (isCommentSubmitting.value) return;
  if (!window.confirm("이 댓글을 삭제할까요?")) return;

  isCommentSubmitting.value = true;
  commentActionError.value = "";
  try {
    await postApi.deleteComment(comment.idx);
    await loadComments();
  } catch (error) {
    commentActionError.value = getApiErrorState(error, "댓글을 삭제하지 못했어요").message;
  } finally {
    isCommentSubmitting.value = false;
  }
}

function startEdit() {
  resetEditForm();
  isEditing.value = true;
}

function cancelEdit() {
  isEditing.value = false;
  resetEditForm();
}

async function saveEdit() {
  if (isSaving.value) return;
  const title = editTitle.value.trim();
  const content = editContent.value.trim();

  if (!title || !content) {
    actionError.value = "제목과 내용을 모두 입력해주세요.";
    return;
  }

  isSaving.value = true;
  actionError.value = "";
  try {
    const updated = normalizePost(await postApi.updatePost(props.post.idx, { title, content }));
    isEditing.value = false;
    emit("updated", updated);
  } catch (error) {
    actionError.value = getApiErrorState(error, "포스트를 수정하지 못했어요").message;
  } finally {
    isSaving.value = false;
  }
}

async function deletePost() {
  if (isDeleting.value) return;
  if (!window.confirm("이 포스트를 삭제할까요?")) return;

  isDeleting.value = true;
  actionError.value = "";
  try {
    await postApi.deletePost(props.post.idx);
    emit("deleted", props.post.idx);
  } catch (error) {
    actionError.value = getApiErrorState(error, "포스트를 삭제하지 못했어요").message;
  } finally {
    isDeleting.value = false;
  }
}

function closeOnEscape(event) {
  if (event.key === "Escape") {
    emit("close");
  }
}

watch(() => props.post.idx, () => {
  resetEditForm();
  resetCommentForms();
  isEditing.value = false;
  loadComments();
}, { immediate: true });

watch(() => props.focusCommentId, () => {
  scrollToFocusedComment();
});

onMounted(() => document.addEventListener("keydown", closeOnEscape));
onUnmounted(() => document.removeEventListener("keydown", closeOnEscape));
</script>

<template>
  <div class="post-modal-overlay" @click.self="emit('close')">
    <article ref="postModalRef" class="post-modal" role="dialog" aria-modal="true">
      <header class="post-modal-head" :class="{ editing: isEditing }">
        <div>
          <button class="post-modal-bill" type="button" @click="emit('openBill', post)">
            {{ billTitle || post.billId || "연결된 법안" }}
          </button>
          <h2 v-if="!isEditing">{{ post.title }}</h2>
          <input
            v-else
            v-model="editTitle"
            class="post-edit-title"
            type="text"
            maxlength="200"
          />
          <div class="post-modal-meta">
            <button
              class="post-author-link"
              type="button"
              :class="{ mine: isOwner }"
              @click="emit('openUser', post.userIdx)"
            >
              {{ post.nickname }}
            </button>
            <span>{{ displayDate }}</span>
            <span v-if="editedLabel">{{ editedLabel }}</span>
            <span>댓글 {{ displayedCommentCount }}</span>
            <span>조회 {{ post.viewCount }}</span>
          </div>
        </div>
        <button class="close" type="button" aria-label="닫기" @click="emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>
      </header>

      <div class="post-modal-body">
        <section class="post-modal-content">
          <p v-if="!isEditing">{{ post.content }}</p>
          <textarea
            v-else
            v-model="editContent"
            class="post-edit-content"
            rows="10"
          ></textarea>

          <div v-if="isOwner" class="post-owner-actions">
            <template v-if="isEditing">
              <button class="btn btn-primary" type="button" :disabled="isSaving" @click="saveEdit">
                {{ isSaving ? "저장 중" : "저장" }}
              </button>
              <button class="btn btn-ghost" type="button" :disabled="isSaving" @click="cancelEdit">
                취소
              </button>
            </template>
            <template v-else>
              <button class="btn btn-ghost" type="button" @click="startEdit">수정</button>
              <button class="btn btn-danger" type="button" :disabled="isDeleting" @click="deletePost">
                {{ isDeleting ? "삭제 중" : "삭제" }}
              </button>
            </template>
          </div>
          <p v-if="actionError" class="post-action-error">{{ actionError }}</p>
        </section>

        <section class="post-comments">
          <div class="post-comments-head">
            <h3>댓글</h3>
            <span>{{ displayedCommentCount }}개</span>
          </div>

          <form class="post-comment-form" @submit.prevent="submitComment()">
            <textarea
              v-model="newCommentContent"
              rows="3"
              :placeholder="authStore.isAuthenticated ? '댓글을 작성해주세요.' : '로그인 후 댓글을 작성할 수 있습니다.'"
              :disabled="!authStore.isAuthenticated || isCommentSubmitting"
            ></textarea>
            <button
              class="btn btn-primary"
              type="submit"
              :disabled="!authStore.isAuthenticated || isCommentSubmitting"
            >
              댓글 작성
            </button>
          </form>
          <p v-if="commentActionError" class="post-action-error">{{ commentActionError }}</p>

          <div v-if="commentStatus === 'loading'" class="post-comments-state">댓글을 불러오는 중입니다.</div>
          <div v-else-if="commentError" class="post-comments-state">{{ commentError.message }}</div>
          <div v-else-if="!comments.length" class="post-comments-state">아직 댓글이 없습니다.</div>
          <div v-else class="post-comment-list">
            <PostCommentItem
              v-for="comment in comments"
              :key="comment.idx"
              :comment="comment"
              :focus-comment-id="focusCommentId"
              :reply-parent-id="replyParentId"
              :reply-content="replyContent"
              :editing-comment-id="editingCommentId"
              :editing-comment-content="editingCommentContent"
              :is-submitting="isCommentSubmitting"
              @start-reply="startReply"
              @cancel-reply="cancelReply"
              @update-reply-content="replyContent = $event"
              @submit-reply="submitComment"
              @start-edit="startCommentEdit"
              @cancel-edit="cancelCommentEdit"
              @update-edit-content="editingCommentContent = $event"
              @save-edit="saveCommentEdit"
              @delete="deleteComment"
              @open-user="emit('openUser', $event)"
            />
          </div>
        </section>
      </div>
    </article>
  </div>
</template>
