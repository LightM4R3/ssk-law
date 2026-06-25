<script setup>
import { computed } from "vue";

const props = defineProps({
  post: {
    type: Object,
    required: true,
  },
  billTitle: {
    type: String,
    default: "",
  },
  isOwned: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["select", "openBill", "openUser"]);

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
</script>

<template>
  <article
    class="post-card"
    tabindex="0"
    @click="emit('select', post)"
    @keydown.enter="emit('select', post)"
  >
    <button
      class="post-card-bill"
      type="button"
      @click.stop="emit('openBill', post)"
    >
      {{ billTitle || post.billId || "연결된 법안" }}
    </button>
    <h3>{{ post.title }}</h3>
    <p>{{ post.content }}</p>
    <div class="post-card-foot">
      <div class="post-card-author">
        <button
          class="post-author-link"
          type="button"
          :class="{ mine: isOwned }"
          @click.stop="emit('openUser', post.userIdx)"
        >
          {{ post.nickname }}
        </button>
        <span>{{ displayDate }}</span>
        <span v-if="editedLabel">{{ editedLabel }}</span>
      </div>
      <div class="post-card-stats">
        <span>댓글 {{ post.commentCount }}</span>
        <span>조회 {{ post.viewCount }}</span>
      </div>
    </div>
  </article>
</template>
