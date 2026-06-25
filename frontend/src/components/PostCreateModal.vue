<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";

import { getApiErrorState, normalizePost, postApi } from "../services/api";

const props = defineProps({
  initialBill: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["close", "created"]);

const title = ref("");
const content = ref("");
const isSubmitting = ref(false);
const errorMessage = ref("");
const showSuccess = ref(false);
const isSuccessLeaving = ref(false);
const successTimers = [];

const selectedBill = computed(() => props.initialBill);

async function submitPost() {
  if (isSubmitting.value) return;
  if (!selectedBill.value?.id) {
    errorMessage.value = "법안을 선택해주세요.";
    return;
  }

  const trimmedTitle = title.value.trim();
  const trimmedContent = content.value.trim();
  if (!trimmedTitle || !trimmedContent) {
    errorMessage.value = "제목과 내용을 모두 입력해주세요.";
    return;
  }

  isSubmitting.value = true;
  errorMessage.value = "";
  try {
    const created = normalizePost(await postApi.createPost({
      billId: selectedBill.value.id,
      title: trimmedTitle,
      content: trimmedContent,
    }));
    showSuccess.value = true;
    isSuccessLeaving.value = false;
    emit("created", {
      ...created,
      billTitle: created.billTitle || selectedBill.value.title,
    });
    successTimers.push(window.setTimeout(() => {
      isSuccessLeaving.value = true;
    }, 1900));
    successTimers.push(window.setTimeout(() => {
      emit("close");
    }, 2400));
  } catch (error) {
    errorMessage.value = getApiErrorState(error, "포스트를 게시하지 못했어요").message;
  } finally {
    isSubmitting.value = false;
  }
}

function closeOnEscape(event) {
  if (event.key === "Escape") emit("close");
}

onMounted(() => document.addEventListener("keydown", closeOnEscape));
onUnmounted(() => {
  document.removeEventListener("keydown", closeOnEscape);
  successTimers.forEach((timerId) => window.clearTimeout(timerId));
});
</script>

<template>
  <div class="post-modal-overlay" @click.self="emit('close')">
    <article class="post-create-modal" role="dialog" aria-modal="true">
      <header class="post-create-head">
        <div>
          <div class="post-create-kicker">포스트 작성</div>
          <h2>법안에 대한 의견을 남겨주세요</h2>
        </div>
        <button class="close" type="button" aria-label="닫기" @click="emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>
      </header>

      <form class="post-create-form" @submit.prevent="submitPost">
        <div class="post-selected-bill">
          <span>선택된 법안</span>
          <strong>{{ selectedBill?.title || "선택된 법안이 없습니다." }}</strong>
          <small>{{ selectedBill?.billNo || selectedBill?.id }}</small>
        </div>

        <label>
          <span>제목</span>
          <input v-model="title" type="text" maxlength="200" placeholder="포스트 제목을 입력해주세요." />
        </label>

        <label>
          <span>내용</span>
          <textarea v-model="content" rows="9" placeholder="법안에 대한 의견을 작성해주세요."></textarea>
        </label>

        <p v-if="errorMessage" class="post-action-error">{{ errorMessage }}</p>

        <div class="post-create-actions">
          <button class="btn btn-ghost" type="button" :disabled="isSubmitting" @click="emit('close')">
            취소
          </button>
          <button class="btn btn-primary" type="submit" :disabled="isSubmitting">
            {{ isSubmitting ? "게시 중" : "포스트 게시" }}
          </button>
        </div>
      </form>

      <div
        v-if="showSuccess"
        class="post-create-success"
        :class="{ leaving: isSuccessLeaving }"
        role="status"
      >
        포스트가 게시되었습니다
      </div>
    </article>
  </div>
</template>
