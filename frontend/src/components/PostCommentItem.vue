<script setup>
import { computed } from "vue";

import { useAuthStore } from "../stores/auth";

const props = defineProps({
  comment: {
    type: Object,
    required: true,
  },
  replyParentId: {
    type: Number,
    default: null,
  },
  replyContent: {
    type: String,
    default: "",
  },
  editingCommentId: {
    type: Number,
    default: null,
  },
  editingCommentContent: {
    type: String,
    default: "",
  },
  isSubmitting: {
    type: Boolean,
    default: false,
  },
  focusCommentId: {
    type: Number,
    default: null,
  },
});

const emit = defineEmits([
  "startReply",
  "cancelReply",
  "updateReplyContent",
  "submitReply",
  "startEdit",
  "cancelEdit",
  "updateEditContent",
  "saveEdit",
  "delete",
  "openUser",
]);

const authStore = useAuthStore();

const isOwner = computed(() => (
  authStore.isAuthenticated
  && !props.comment.isDeleted
  && Number(authStore.account?.idx) === Number(props.comment.userIdx)
));

const isReplying = computed(() => props.replyParentId === props.comment.idx);
const isEditing = computed(() => props.editingCommentId === props.comment.idx);
const isFocused = computed(() => Number(props.focusCommentId) === Number(props.comment.idx));
const hasEdited = computed(() => {
  if (!props.comment.createdAt || !props.comment.updatedAt) return false;
  const created = new Date(props.comment.createdAt).getTime();
  const updated = new Date(props.comment.updatedAt).getTime();
  if (!Number.isFinite(created) || !Number.isFinite(updated)) return false;
  return updated - created > 1000;
});
const displayDate = computed(() => (
  hasEdited.value ? formatDate(props.comment.updatedAt) : formatDate(props.comment.createdAt)
));

function formatDate(value) {
  const date = String(value || "").slice(0, 10);
  return date ? date.replaceAll("-", ".") : "";
}
</script>

<template>
  <div
    class="post-comment"
    :class="{ reply: comment.parent, focused: isFocused }"
    :data-comment-id="comment.idx"
  >
    <div class="post-comment-main">
      <button
        class="post-author-link"
        type="button"
        :class="{ mine: isOwner }"
        @click="emit('openUser', comment.userIdx)"
      >
        {{ comment.nickname }}
      </button>
      <span>{{ displayDate }}</span>
      <span v-if="hasEdited">수정</span>
      <div v-if="isOwner" class="post-comment-actions">
        <button type="button" @click="emit('startEdit', comment)">수정</button>
        <button type="button" @click="emit('delete', comment)">삭제</button>
      </div>
    </div>

    <template v-if="isEditing">
      <textarea
        class="post-comment-edit"
        rows="3"
        :value="editingCommentContent"
        @input="emit('updateEditContent', $event.target.value)"
      ></textarea>
      <div class="post-comment-form-actions">
        <button
          class="btn btn-primary"
          type="button"
          :disabled="isSubmitting"
          @click="emit('saveEdit', comment)"
        >
          저장
        </button>
        <button
          class="btn btn-ghost"
          type="button"
          :disabled="isSubmitting"
          @click="emit('cancelEdit')"
        >
          취소
        </button>
      </div>
    </template>
    <p v-else :class="{ deleted: comment.isDeleted }">
      {{ comment.isDeleted ? "삭제된 댓글입니다." : comment.content }}
    </p>

    <button
      v-if="authStore.isAuthenticated && !comment.isDeleted"
      class="post-reply-trigger"
      type="button"
      @click="emit('startReply', comment)"
    >
      답글
    </button>

    <form
      v-if="isReplying"
      class="post-comment-form reply-form"
      @submit.prevent="emit('submitReply', comment)"
    >
      <textarea
        rows="2"
        placeholder="답글을 작성해주세요."
        :value="replyContent"
        @input="emit('updateReplyContent', $event.target.value)"
      ></textarea>
      <div class="post-comment-form-actions">
        <button class="btn btn-primary" type="submit" :disabled="isSubmitting">
          답글 작성
        </button>
        <button
          class="btn btn-ghost"
          type="button"
          :disabled="isSubmitting"
          @click="emit('cancelReply')"
        >
          취소
        </button>
      </div>
    </form>

    <div v-if="comment.replies.length" class="post-replies">
      <PostCommentItem
        v-for="reply in comment.replies"
        :key="reply.idx"
        :comment="reply"
        :focus-comment-id="focusCommentId"
        :reply-parent-id="replyParentId"
        :reply-content="replyContent"
        :editing-comment-id="editingCommentId"
        :editing-comment-content="editingCommentContent"
        :is-submitting="isSubmitting"
        @start-reply="emit('startReply', $event)"
        @cancel-reply="emit('cancelReply')"
        @update-reply-content="emit('updateReplyContent', $event)"
        @submit-reply="emit('submitReply', $event)"
        @start-edit="emit('startEdit', $event)"
        @cancel-edit="emit('cancelEdit')"
        @update-edit-content="emit('updateEditContent', $event)"
        @save-edit="emit('saveEdit', $event)"
        @delete="emit('delete', $event)"
        @open-user="emit('openUser', $event)"
      />
    </div>
  </div>
</template>
