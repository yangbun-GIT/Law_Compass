<template>
  <section class="grid-2">
    <article class="card">
      <h2>회원가입</h2>
      <form class="auth-form" @submit.prevent="submit">
        <label>이메일
          <input v-model.trim="email" type="email" autocomplete="email" placeholder="name@example.com" />
        </label>
        <label>표시 이름
          <input v-model.trim="name" autocomplete="name" placeholder="홍길동" maxlength="80" />
        </label>
        <label>비밀번호
          <input v-model="password" type="password" autocomplete="new-password" placeholder="8자 이상" />
        </label>
        <button class="btn" :disabled="!canSubmit" type="submit">회원가입</button>
      </form>
      <p v-if="message" :class="ok ? 'msg-ok' : 'msg-error'">{{ message }}</p>
    </article>

    <article class="card">
      <h3>보안 원칙</h3>
      <ul class="list-reset">
        <li>Access 토큰은 짧게, Refresh 토큰은 회전 방식으로 운용합니다.</li>
        <li>케이스/업로드 접근은 owner 체크로 BOLA를 차단합니다.</li>
        <li>감사 로그에 trace_id, 요청/응답 해시가 저장됩니다.</li>
      </ul>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { api, formatApiError } from "../api/client";

const router = useRouter();
const email = ref("");
const name = ref("");
const password = ref("");
const message = ref("");
const ok = ref(false);
const canSubmit = computed(() => isEmail(email.value) && name.value.trim().length > 0 && password.value.length >= 8);

function isEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

async function submit() {
  if (!canSubmit.value) {
    message.value = "이메일, 표시 이름, 8자 이상 비밀번호를 입력해 주세요.";
    ok.value = false;
    return;
  }
  try {
    const cleanEmail = email.value.trim();
    await api.signup({ email: cleanEmail, password: password.value, display_name: name.value.trim() });
    message.value = "가입 완료. 로그인 페이지로 이동합니다.";
    ok.value = true;
    await router.push({ path: "/login", query: { email: cleanEmail } });
  } catch (e: any) {
    message.value = formatApiError(e, "회원가입에 실패했습니다.");
    ok.value = false;
  }
}
</script>
