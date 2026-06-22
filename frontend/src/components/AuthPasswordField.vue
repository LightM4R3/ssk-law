<script setup>
import { ref } from "vue";

defineProps({
  id: {
    type: String,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
  modelValue: {
    type: String,
    default: "",
  },
  autocomplete: {
    type: String,
    default: "current-password",
  },
  placeholder: {
    type: String,
    default: "비밀번호를 입력하세요",
  },
  error: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["update:modelValue"]);
const isVisible = ref(false);
</script>

<template>
  <div class="auth-field" :class="{ 'has-error': error }">
    <label :for="id">{{ label }}</label>
    <span class="auth-input-wrap">
      <input
        :id="id"
        :value="modelValue"
        :type="isVisible ? 'text' : 'password'"
        :autocomplete="autocomplete"
        :placeholder="placeholder"
        minlength="8"
        required
        :aria-invalid="Boolean(error)"
        :aria-describedby="error ? `${id}-error` : undefined"
        @input="emit('update:modelValue', $event.target.value)"
      />
      <button
        class="auth-password-toggle"
        type="button"
        :aria-label="isVisible ? '비밀번호 숨기기' : '비밀번호 보기'"
        :aria-pressed="isVisible"
        @click="isVisible = !isVisible"
      >
        <svg v-if="isVisible" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M3 3l18 18" />
          <path d="M10.6 10.7a2 2 0 0 0 2.7 2.7" />
          <path d="M9.9 4.2A10.6 10.6 0 0 1 12 4c5.4 0 9 5.6 9 5.6a12.8 12.8 0 0 1-2.1 2.7" />
          <path d="M6.6 6.7C4.3 8.2 3 10.4 3 10.4S6.6 16 12 16c1.1 0 2.1-.2 3-.6" />
        </svg>
        <svg v-else viewBox="0 0 24 24" aria-hidden="true">
          <path d="M3 12s3.6-5.6 9-5.6 9 5.6 9 5.6-3.6 5.6-9 5.6S3 12 3 12Z" />
          <circle cx="12" cy="12" r="2.4" />
        </svg>
      </button>
    </span>
    <small v-if="error" :id="`${id}-error`" class="auth-field-error" role="alert">
      {{ error }}
    </small>
  </div>
</template>
