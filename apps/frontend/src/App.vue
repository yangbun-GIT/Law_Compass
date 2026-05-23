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
        <RouterLink v-if="session.user?.role === 'admin'" to="/admin/agent-test">관리자 테스트</RouterLink>
        <RouterLink v-if="!session.user" to="/login">로그인</RouterLink>
        <RouterLink v-if="!session.user" to="/signup">회원가입</RouterLink>
        <span v-else class="user-chip">{{ session.user.display_name }}</span>
        <button v-if="session.user" class="btn secondary" @click="logout">로그아웃</button>
      </nav>
    </header>

    <main class="glass page-panel">
      <RouterView />
    </main>
  </div>

  <AiChatFloatingButton />
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import AiChatFloatingButton from "./components/chat/AiChatFloatingButton.vue";
import { useSessionStore } from "./stores/session";

const router = useRouter();
const session = useSessionStore();

async function logout() {
  await session.logout();
  await router.push("/login");
}
</script>

