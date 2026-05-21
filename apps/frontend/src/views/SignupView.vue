<template>
  <section class="grid-2">
    <article class="card">
      <h2>회원가입</h2>
      <label>이메일
        <input v-model="email" type="email" />
      </label>
      <label>표시 이름
        <input v-model="name" />
      </label>
      <label>비밀번호
        <input v-model="password" type="password" />
      </label>
      <button class="btn" @click="submit">회원가입</button>
      <p :class="ok ? 'msg-ok' : 'msg-error'">{{ message }}</p>
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
import { ref } from "vue";
import { api, formatApiError } from "../api/client";

const email = ref("user@example.com");
const name = ref("홍길동");
const password = ref("password123");
const message = ref("");
const ok = ref(false);

async function submit() {
  try {
    await api.signup({ email: email.value, password: password.value, display_name: name.value });
    message.value = "가입 완료, 로그인 페이지로 이동하세요.";
    ok.value = true;
  } catch (e: any) {
    message.value = formatApiError(e, "회원가입에 실패했습니다.");
    ok.value = false;
  }
}
</script>
