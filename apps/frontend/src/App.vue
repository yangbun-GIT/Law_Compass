<template>
  <div class="app-bg">
    <div class="aurora aurora-a"></div>
    <div class="aurora aurora-b"></div>
  </div>

  <div class="app-shell">
    <header class="glass topbar">
      <div>
        <h1>LawCompass</h1>
        <p class="muted">교통사고 AI 분석 도우미</p>
      </div>
      <nav>
        <RouterLink to="/">대시보드</RouterLink>
        <RouterLink to="/knia/ranking">KNIA 검색순위</RouterLink>
        <RouterLink to="/login">로그인</RouterLink>
        <RouterLink to="/signup">회원가입</RouterLink>
        <button v-if="session.user" class="btn secondary" @click="logout">로그아웃</button>
      </nav>
    </header>

    <main class="glass page-panel">
      <p v-if="session.user" class="kv">현재 사용자: {{ session.user.display_name }} ({{ session.user.email }})</p>
      <RouterView />
    </main>
  </div>

  <AiChatFloatingButton />
</template>

<script setup lang="ts">
import AiChatFloatingButton from "./components/chat/AiChatFloatingButton.vue";
import { useSessionStore } from "./stores/session";

const session = useSessionStore();

async function logout() {
  await session.logout();
}
</script>

