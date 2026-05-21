<template>
  <section class="grid-2">
    <article class="card">
      <h2>로그인</h2>
      <p class="kv">기존 계정으로 케이스를 조회하고 분석을 진행하세요.</p>
      <form class="auth-form" @submit.prevent="submit">
        <label>이메일
          <input v-model.trim="email" type="email" autocomplete="email" placeholder="name@example.com" />
        </label>
        <label>비밀번호
          <input v-model="password" type="password" autocomplete="current-password" placeholder="8자 이상" />
        </label>
        <button class="btn" :disabled="session.loading || !canSubmit" type="submit">{{ session.loading ? "로그인 중..." : "로그인" }}</button>
      </form>
      <p v-if="message" :class="messageClass">{{ message }}</p>
    </article>

    <article class="card">
      <h3>안내</h3>
      <ul class="list-reset">
        <li>법률/보험 확정 자문이 아닌 AI 참고 리포트입니다.</li>
        <li>모든 결과에는 근거와 불확실성 항목이 함께 제공됩니다.</li>
        <li>영상 원본은 S3에 private로 저장되고 URL은 짧게 발급됩니다.</li>
      </ul>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatApiError } from "../api/client";
import { useSessionStore } from "../stores/session";

const message = ref("");
const ok = ref(false);
const router = useRouter();
const route = useRoute();
const session = useSessionStore();
const email = ref(typeof route.query.email === "string" ? route.query.email : "");
const password = ref("");

const messageClass = computed(() => (ok.value ? "msg-ok" : "msg-error"));
const canSubmit = computed(() => isEmail(email.value) && password.value.length >= 8);

function isEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

async function submit() {
  if (!canSubmit.value) {
    message.value = "이메일 형식과 8자 이상 비밀번호를 입력해 주세요.";
    ok.value = false;
    return;
  }
  try {
    await session.login(email.value, password.value);
    message.value = "로그인 성공";
    ok.value = true;
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
    router.push(redirect);
  } catch (e: any) {
    message.value = formatApiError(e, "로그인에 실패했습니다.");
    ok.value = false;
  }
}
</script>
