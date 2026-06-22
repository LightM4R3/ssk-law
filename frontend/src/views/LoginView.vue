<script setup>
import { computed, reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import AuthPasswordField from "../components/AuthPasswordField.vue";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const accountId = ref(typeof route.query.accountId === "string" ? route.query.accountId : "");
const password = ref("");
const signupCompleted = computed(() => route.query.registered === "1");
const isSubmitting = ref(false);
const formError = ref("");
const fieldErrors = reactive({
  accountId: "",
  password: "",
});

function updateAccountId(event) {
  accountId.value = event.target.value;
  fieldErrors.accountId = "";
  formError.value = "";
}

function updatePassword(value) {
  password.value = value;
  fieldErrors.password = "";
  formError.value = "";
}

function validateForm() {
  fieldErrors.accountId = "";
  fieldErrors.password = "";
  formError.value = "";

  if (!accountId.value.trim()) {
    fieldErrors.accountId = "아이디를 입력해 주세요.";
  }

  if (!password.value) {
    fieldErrors.password = "비밀번호를 입력해 주세요.";
  } else if (password.value.length < 8) {
    fieldErrors.password = "비밀번호는 8자 이상 입력해 주세요.";
  }

  return !fieldErrors.accountId && !fieldErrors.password;
}

async function submitLogin() {
  if (!validateForm()) return;

  isSubmitting.value = true;
  try {
    await authStore.login(accountId.value.trim(), password.value);
    await router.push({ name: "home" });
  } catch (error) {
    if (error.code === "ACCOUNT_NOT_FOUND") {
      fieldErrors.accountId = "존재하지 않는 아이디입니다.";
      fieldErrors.password = "";
    } else if (error.code === "INVALID_PASSWORD") {
      fieldErrors.accountId = "";
      fieldErrors.password = "비밀번호가 올바르지 않습니다.";
    } else {
      formError.value = "로그인 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <section class="auth-view" aria-labelledby="login-title">
    <div class="auth-shell">
      <header class="auth-heading">
        <div class="auth-brand-mark" aria-hidden="true">슥</div>
        <h1 id="login-title">로그인</h1>
        <p>슥 확인하는 법안, 슥법</p>
      </header>

      <form class="auth-form" novalidate @submit.prevent="submitLogin">
        <p v-if="signupCompleted" class="auth-form-success" role="status">
          회원가입이 완료되었습니다. 비밀번호를 입력해 로그인해 주세요.
        </p>

        <div class="auth-field" :class="{ 'has-error': fieldErrors.accountId }">
          <label for="login-id">아이디</label>
          <span class="auth-input-wrap">
            <input
              id="login-id"
              :value="accountId"
              type="text"
              autocomplete="username"
              placeholder="아이디를 입력하세요"
              required
              :aria-invalid="Boolean(fieldErrors.accountId)"
              :aria-describedby="fieldErrors.accountId ? 'login-id-error' : undefined"
              @input="updateAccountId"
            />
          </span>
          <small v-if="fieldErrors.accountId" id="login-id-error" class="auth-field-error" role="alert">
            {{ fieldErrors.accountId }}
          </small>
        </div>

        <AuthPasswordField
          id="login-password"
          :model-value="password"
          label="비밀번호"
          autocomplete="current-password"
          :error="fieldErrors.password"
          @update:model-value="updatePassword"
        />

        <p v-if="formError" class="auth-form-error" role="alert">{{ formError }}</p>

        <button
          class="auth-submit"
          type="submit"
          :disabled="isSubmitting"
          :aria-busy="isSubmitting"
        >
          슥 눌러 로그인하기
        </button>
      </form>

      <p class="auth-switch">
        아직 계정이 없으신가요?
        <RouterLink :to="{ name: 'signup' }">회원가입</RouterLink>
      </p>
    </div>
  </section>
</template>
