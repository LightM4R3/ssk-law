<script setup>
import { reactive, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import AuthPasswordField from "../components/AuthPasswordField.vue";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();
const accountId = ref("");
const nickname = ref("");
const password = ref("");
const passwordConfirm = ref("");
const isSubmitting = ref(false);
const formError = ref("");
const fieldErrors = reactive({
  accountId: "",
  nickname: "",
  password: "",
  passwordConfirm: "",
});

function clearError(field) {
  fieldErrors[field] = "";
  formError.value = "";
}

function updateAccountId(event) {
  accountId.value = event.target.value;
  clearError("accountId");
}

function updateNickname(event) {
  nickname.value = event.target.value;
  clearError("nickname");
}

function updatePassword(value) {
  password.value = value;
  clearError("password");
  clearError("passwordConfirm");
}

function updatePasswordConfirm(value) {
  passwordConfirm.value = value;
  clearError("passwordConfirm");
}

function validateForm() {
  Object.keys(fieldErrors).forEach((field) => {
    fieldErrors[field] = "";
  });
  formError.value = "";

  const normalizedId = accountId.value.trim();
  const normalizedNickname = nickname.value.trim();

  if (!normalizedId) {
    fieldErrors.accountId = "아이디를 입력해 주세요.";
  } else if (normalizedId.length > 50) {
    fieldErrors.accountId = "아이디는 50자 이내로 입력해 주세요.";
  }

  if (!normalizedNickname) {
    fieldErrors.nickname = "닉네임을 입력해 주세요.";
  } else if (normalizedNickname.length > 50) {
    fieldErrors.nickname = "닉네임은 50자 이내로 입력해 주세요.";
  }

  if (!password.value) {
    fieldErrors.password = "비밀번호를 입력해 주세요.";
  } else if (password.value.length < 8) {
    fieldErrors.password = "비밀번호는 8자 이상 입력해 주세요.";
  } else if (password.value.length > 128) {
    fieldErrors.password = "비밀번호는 128자 이내로 입력해 주세요.";
  } else if (!/[a-z]/.test(password.value) || !/[A-Z]/.test(password.value) || !/\d/.test(password.value)) {
    fieldErrors.password = "비밀번호에는 영문 대문자, 소문자, 숫자가 모두 포함되어야 합니다.";
  }

  if (!passwordConfirm.value) {
    fieldErrors.passwordConfirm = "비밀번호를 다시 입력해 주세요.";
  } else if (password.value !== passwordConfirm.value) {
    fieldErrors.passwordConfirm = "비밀번호가 일치하지 않습니다.";
  }

  return !Object.values(fieldErrors).some(Boolean);
}

async function submitSignup() {
  if (!validateForm()) return;

  const normalizedId = accountId.value.trim();
  isSubmitting.value = true;
  try {
    await authStore.signup({
      id: normalizedId,
      nickname: nickname.value.trim(),
      password: password.value,
    });
    await router.push({
      name: "login",
      query: { registered: "1", accountId: normalizedId },
    });
  } catch (error) {
    const payload = error.payload || {};
    if (payload.id) {
      fieldErrors.accountId = "이미 사용 중인 아이디입니다.";
    }
    if (payload.nickname) {
      fieldErrors.nickname = "이미 사용 중인 닉네임입니다.";
    }
    if (payload.password) {
      fieldErrors.password = "비밀번호는 8자 이상이며 영문 대문자, 소문자, 숫자를 모두 포함해야 합니다.";
    }
    if (!fieldErrors.accountId && !fieldErrors.nickname && !fieldErrors.password) {
      formError.value = "회원가입 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <section class="auth-view" aria-labelledby="signup-title">
    <div class="auth-shell auth-shell-wide">
      <header class="auth-heading">
        <div class="auth-brand-mark" aria-hidden="true">슥</div>
        <h1 id="signup-title">회원가입</h1>
        <p>의견을 나눌 슥법 계정을 만드세요.</p>
      </header>

      <form class="auth-form" novalidate @submit.prevent="submitSignup">
        <div class="auth-field" :class="{ 'has-error': fieldErrors.accountId }">
          <label for="signup-id">아이디</label>
          <span class="auth-input-wrap">
            <input
              id="signup-id"
              :value="accountId"
              type="text"
              autocomplete="username"
              placeholder="사용할 아이디를 입력하세요"
              maxlength="50"
              required
              :aria-invalid="Boolean(fieldErrors.accountId)"
              :aria-describedby="fieldErrors.accountId ? 'signup-id-error' : undefined"
              @input="updateAccountId"
            />
          </span>
          <small v-if="fieldErrors.accountId" id="signup-id-error" class="auth-field-error" role="alert">
            {{ fieldErrors.accountId }}
          </small>
        </div>

        <div class="auth-field" :class="{ 'has-error': fieldErrors.nickname }">
          <label for="signup-nickname">닉네임</label>
          <span class="auth-input-wrap">
            <input
              id="signup-nickname"
              :value="nickname"
              type="text"
              autocomplete="nickname"
              placeholder="표시할 닉네임을 입력하세요"
              maxlength="50"
              required
              :aria-invalid="Boolean(fieldErrors.nickname)"
              :aria-describedby="fieldErrors.nickname ? 'signup-nickname-error' : undefined"
              @input="updateNickname"
            />
          </span>
          <small v-if="fieldErrors.nickname" id="signup-nickname-error" class="auth-field-error" role="alert">
            {{ fieldErrors.nickname }}
          </small>
        </div>

        <AuthPasswordField
          id="signup-password"
          :model-value="password"
          label="비밀번호"
          autocomplete="new-password"
          placeholder="8자 이상 입력하세요"
          :error="fieldErrors.password"
          @update:model-value="updatePassword"
        />

        <AuthPasswordField
          id="signup-password-confirm"
          :model-value="passwordConfirm"
          label="비밀번호 확인"
          autocomplete="new-password"
          placeholder="비밀번호를 다시 입력하세요"
          :error="fieldErrors.passwordConfirm"
          @update:model-value="updatePasswordConfirm"
        />

        <p v-if="formError" class="auth-form-error" role="alert">{{ formError }}</p>

        <button
          class="auth-submit"
          type="submit"
          :disabled="isSubmitting"
          :aria-busy="isSubmitting"
        >
          <span class="auth-submit-label">
            {{ isSubmitting ? "계정 만드는 중..." : "계정 만들기" }}
          </span>
          <span v-if="isSubmitting" class="auth-submit-progress" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M4 12h15" />
              <path d="m14 7 5 5-5 5" />
            </svg>
          </span>
        </button>
      </form>

      <p class="auth-switch">
        이미 계정이 있으신가요?
        <RouterLink :to="{ name: 'login' }">로그인</RouterLink>
      </p>
    </div>
  </section>
</template>
