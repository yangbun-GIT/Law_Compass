<template>
  <section>
    <article class="card hero-card">
      <p class="kv">LawCompass 로컬 MVP</p>
      <h2>내 교통사고 케이스</h2>
      <p>케이스를 만들고 사고 정보, 영상 업로드, AI 분석, 쉬운 리포트와 근거 문서 확인까지 이어서 진행합니다.</p>
      <div class="dashboard-knia-grid">
        <RouterLink class="knia-entry-card" to="/knia/ranking">
          <span class="entry-kicker">검색순위 보기</span>
          <strong>많이 검색된 사고유형</strong>
          <small>KNIA 과실비율정보포털에서 많이 조회된 기준을 봅니다.</small>
        </RouterLink>
        <RouterLink class="knia-entry-card secondary-entry" to="/knia/ranking">
          <span class="entry-kicker">KNIA 기준 검색</span>
          <strong>기준번호/사고유형 검색</strong>
          <small>검색순위 화면에서 기준번호나 사고유형명으로 저장된 기준을 찾습니다.</small>
        </RouterLink>
      </div>
    </article>

    <ul class="list-reset card">
      <li v-for="item in items" :key="item.id" class="case-row">
        <div>
          <strong>{{ item.title }}</strong>
          <p class="kv">상태: {{ item.status }} / 생성: {{ formatDate(item.created_at) }}</p>
          <p>{{ item.description_text }}</p>
        </div>
        <div class="btn-row">
          <RouterLink class="btn secondary" :to="`/cases/${item.id}/wizard`">입력 이어가기</RouterLink>
          <RouterLink class="btn secondary" :to="`/cases/${item.id}/result`">결과 보기</RouterLink>
        </div>
      </li>
      <li v-if="!items.length">등록된 케이스가 없습니다.</li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api, type CaseItem } from '../api/client';

const items = ref<CaseItem[]>([]);

function formatDate(iso: string) {
  return new Date(iso).toLocaleString();
}

async function load() {
  const data = await api.listCases();
  items.value = data.items;
}

onMounted(load);
</script>

<style scoped>
.dashboard-knia-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }
.knia-entry-card { display: grid; gap: 7px; padding: 18px; border-radius: 22px; text-decoration: none; color: #effbff; background: linear-gradient(135deg, rgba(43, 210, 255, 0.18), rgba(255, 255, 255, 0.07)); border: 1px solid rgba(105, 225, 255, 0.28); box-shadow: 0 18px 42px rgba(0, 0, 0, 0.18); }
.knia-entry-card.secondary-entry { background: linear-gradient(135deg, rgba(78, 255, 190, 0.14), rgba(255, 255, 255, 0.06)); border-color: rgba(122, 255, 204, 0.24); }
.entry-kicker { color: #4fe4ff; font-size: 0.86rem; font-weight: 800; }
.knia-entry-card strong { font-size: 1.12rem; }
.knia-entry-card small { color: #b8c7d9; line-height: 1.45; }
@media (max-width: 720px) { .dashboard-knia-grid { grid-template-columns: 1fr; } }
</style>
