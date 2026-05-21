<template>
  <section class="knia-ranking-page">
    <article class="card hero-card ranking-hero">
      <div>
        <p class="eyebrow">KNIA 과실비율정보포털</p>
        <h2>많이 검색된 사고유형</h2>
        <p>
          과실비율정보포털 원본의 검색순위를 기준으로 정리했습니다.
          이 화면은 검색순위전용이며, 탭은 원본과 같이 4개만 제공합니다.
        </p>
      </div>
      <a class="btn secondary source-link" href="https://accident.knia.or.kr/ranking" target="_blank" rel="noopener noreferrer">
        KNIA 원본 보기
      </a>
    </article>

    <article class="card ranking-controls-card">
      <div class="section-heading">
        <div>
          <p class="eyebrow">검색순위 분류</p>
          <h3>원본 ranking 탭</h3>
        </div>
        <button class="btn collect-btn" :disabled="collecting" @click="collectRanking">
          {{ collecting ? '수집 중...' : '검색순위 수집/새로고침' }}
        </button>
      </div>

      <AccidentPartyTypeTabs v-model="selectedParty" />

      <div class="ranking-search-row">
        <input v-model="searchQuery" placeholder="저장된 순위에서 기준번호 또는 사고유형 검색" @keyup.enter="load" />
        <button class="btn secondary" :disabled="loading" @click="load">검색</button>
      </div>

      <p v-if="message" class="notice success">{{ message }}</p>
      <p v-if="error" class="notice error">{{ error }}</p>
    </article>

    <article class="card ranking-list-card">
      <div class="section-heading compact">
        <div>
          <p class="eyebrow">{{ selectedLabel }} 검색순위</p>
          <h3>최신 수집 기준</h3>
        </div>
        <span class="kv">{{ items.length }}건 표시</span>
      </div>

      <p v-if="loading" class="kv loading-text">불러오는 중입니다...</p>
      <ul v-else class="evidence-list ranking-list">
        <KniaRankingCard v-for="item in items" :key="`${item.rank}-${item.chart_no}-${selectedParty}`" :item="item" />
        <li v-if="!items.length" class="empty-state ranking-empty">
          <strong>아직 수집된 검색순위가 없습니다.</strong>
          <span>아래 버튼을 누르면 KNIA 원본 ranking 데이터를 수집한 뒤 다시 표시합니다.</span>
          <button class="btn" :disabled="collecting" @click="collectRanking">
            {{ collecting ? '수집 중...' : '검색순위 수집/새로고침' }}
          </button>
        </li>
      </ul>
      <p class="kv attribution">자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털</p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { api } from '../api/client';
import AccidentPartyTypeTabs from '../components/knia/AccidentPartyTypeTabs.vue';
import KniaRankingCard from '../components/knia/KniaRankingCard.vue';

const tabs = [
  { value: 'all', label: '전체' },
  { value: 'car_vs_car', label: '차대차' },
  { value: 'car_vs_person', label: '차대사람' },
  { value: 'car_vs_bicycle', label: '차대자전거' }
];

const items = ref<any[]>([]);
const selectedParty = ref('all');
const searchQuery = ref('');
const loading = ref(false);
const collecting = ref(false);
const error = ref('');
const message = ref('');

const selectedLabel = computed(() => tabs.find((x) => x.value === selectedParty.value)?.label ?? '전체');

function describeCollectResult(result: any) {
  const ranking = result?.result?.ranking ?? result?.ranking ?? result;
  const categories = ranking?.categories ?? {};
  const count = Number(ranking?.ranking_count ?? 0);
  const detail = Object.entries(categories).map(([key, value]) => `${key} ${value}건`).join(', ');
  return count > 0
    ? `검색순위 ${count}건을 수집했습니다${detail ? ` (${detail})` : ''}.`
    : '수집은 완료되었지만 저장된 검색순위가 없습니다. 잠시 후 다시 시도해 주세요.';
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const data = await api.getKniaRanking(20, selectedParty.value, searchQuery.value);
    items.value = data.items || [];
    if (!items.value.length && data.empty_message) message.value = data.empty_message;
  } catch (err: any) {
    error.value = err?.message || '검색순위를 불러오지 못했습니다.';
  } finally {
    loading.value = false;
  }
}

async function collectRanking() {
  collecting.value = true;
  error.value = '';
  message.value = '';
  try {
    const result = await api.adminCollectKnia({ menu: false, ranking: true, charts: false });
    message.value = describeCollectResult(result);
    await load();
    if (!items.value.length) {
      error.value = result?.result?.ranking?.errors?.join('\n') || '수집 후에도 표시할 데이터가 없습니다. KNIA 원본 응답 또는 네트워크 상태를 확인해 주세요.';
    }
  } catch (err: any) {
    error.value = err?.message || '검색순위 수집에 실패했습니다.';
  } finally {
    collecting.value = false;
  }
}

watch(selectedParty, () => {
  message.value = '';
  load();
});

onMounted(load);
</script>

<style scoped>
.knia-ranking-page { display: grid; gap: 18px; }
.ranking-hero { display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; }
.source-link { white-space: nowrap; }
.ranking-controls-card { display: grid; gap: 16px; border-color: rgba(76, 216, 255, 0.28); }
.section-heading { display: flex; justify-content: space-between; align-items: center; gap: 14px; }
.section-heading h3 { margin: 0; font-size: 1.35rem; }
.section-heading.compact { margin-bottom: 12px; }
.ranking-search-row { display: grid; grid-template-columns: 1fr auto; gap: 10px; }
.ranking-search-row input { min-height: 46px; }
.collect-btn { min-width: 190px; }
.notice { padding: 12px 14px; border-radius: 16px; font-weight: 700; }
.notice.success { background: rgba(53, 211, 154, 0.13); border: 1px solid rgba(53, 211, 154, 0.35); color: #9ff5d4; }
.notice.error { background: rgba(255, 112, 132, 0.13); border: 1px solid rgba(255, 112, 132, 0.35); color: #ffb7c3; white-space: pre-line; }
.ranking-table-head { display: grid; grid-template-columns: 56px 96px minmax(260px, 1fr) 140px 80px 220px; gap: 12px; padding: 0 14px 8px; color: #9fb1ca; font-size: 0.82rem; font-weight: 800; border-bottom: 1px solid rgba(255,255,255,0.1); }
.ranking-list { display: grid; gap: 0; }
.ranking-empty { display: grid; gap: 10px; justify-items: start; padding: 22px; }
.ranking-empty strong { font-size: 1.1rem; }
.loading-text, .attribution { margin-top: 12px; }
@media (max-width: 720px) {
  .ranking-hero, .section-heading { display: grid; }
  .ranking-search-row { grid-template-columns: 1fr; }
  .source-link, .collect-btn { width: 100%; justify-content: center; }
  .ranking-table-head { display: none; }
}
</style>
