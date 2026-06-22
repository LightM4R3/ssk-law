<script setup>
import { ref } from "vue";
import { RouterLink } from "vue-router";

import AuthPasswordField from "../components/AuthPasswordField.vue";

const accountId = ref("");
const nickname = ref("");
const password = ref("");
const passwordConfirm = ref("");
</script>

<template>
  <section class="auth-view" aria-labelledby="signup-title">
    <div class="auth-shell auth-shell-wide">
      <header class="auth-heading">
        <div class="auth-brand-mark" aria-hidden="true">슥</div>
        <h1 id="signup-title">회원가입</h1>
        <p>의견을 나눌 슥법 계정을 만드세요.</p>
      </header>

      <form class="auth-form" @submit.prevent>
        <label class="auth-field" for="signup-id">
          <span>아이디</span>
          <span class="auth-input-wrap">
            <input
              id="signup-id"
              v-model="accountId"
              type="text"
              autocomplete="username"
              placeholder="사용할 아이디를 입력하세요"
              required
            />
          </span>
        </label>

        <label class="auth-field" for="signup-nickname">
          <span>닉네임</span>
          <span class="auth-input-wrap">
            <input
              id="signup-nickname"
              v-model="nickname"
              type="text"
              autocomplete="nickname"
              placeholder="표시할 닉네임을 입력하세요"
              required
            />
          </span>
        </label>

        <AuthPasswordField
          id="signup-password"
          v-model="password"
          label="비밀번호"
          autocomplete="new-password"
          placeholder="8자 이상 입력하세요"
        />

        <AuthPasswordField
          id="signup-password-confirm"
          v-model="passwordConfirm"
          label="비밀번호 확인"
          autocomplete="new-password"
          placeholder="비밀번호를 다시 입력하세요"
        />

        <button class="auth-submit" type="submit">계정 만들기</button>
      </form>

      <p class="auth-switch">
        이미 계정이 있으신가요?
        <RouterLink :to="{ name: 'login' }">로그인</RouterLink>
      </p>
    </div>
  </section>
</template>
