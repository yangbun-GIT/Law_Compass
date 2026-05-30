<template>
  <section class="knia-ranking-page">
    <article class="card hero-card ranking-hero">
      <div>
        <p class="eyebrow">KNIA 과실비율정보포털</p>
        <h2>많이 검색된 사고유형</h2>
        <p>
          과실비율정보포털 원본의 검색순위를 기준으로 정리했습니다.
          이 화면은 KNIA 원본 검색순위의 로컬 저장 스냅샷입니다.
          수집 시점과 원본 사이트 상태에 따라 표시 결과가 달라질 수 있습니다.
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
        <div class="collect-actions">
          <button class="btn collect-btn" :disabled="collecting" @click="collectRanking">
            {{ collecting ? '수집 중...' : '검색순위 수집/새로고침' }}
          </button>
          <button v-if="canCollectDetails" class="btn secondary collect-btn" :disabled="collectingDetails" @click="collectRankingDetails">
            {{ collectingDetails ? '상세 수집 중...' : '표시된 항목 상세 수집' }}
          </button>
        </div>
      </div>

      <AccidentPartyTypeTabs v-model="selectedParty" />

      <div class="ranking-search-row">
        <input v-model="searchQuery" placeholder="저장된 순위에서 기준번호 또는 사고유형 검색" @keyup.enter="load()" />
        <button class="btn secondary" :disabled="loading" @click="load()">검색</button>
        <button v-if="isFiltered" class="btn secondary" :disabled="loading" @click="resetSearch">초기화</button>
      </div>

      <p v-if="message" class="notice success">{{ message }}</p>
      <p v-if="error" class="notice error">{{ error }}</p>
      <p v-if="detailStatusText" class="kv detail-status">{{ detailStatusText }}</p>
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
          <strong>{{ emptyTitle }}</strong>
          <span>{{ emptyDescription }}</span>
          <button v-if="!isFiltered" class="btn" :disabled="collecting" @click="collectRanking">
            {{ collecting ? '수집 중...' : '검색순위 수집/새로고침' }}
          </button>
          <button v-else class="btn secondary" :disabled="loading" @click="resetSearch">검색 조건 초기화</button>
        </li>
      </ul>
      <p class="kv attribution">자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털</p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { api, formatApiError } from '../api/client';
import AccidentPartyTypeTabs from '../components/knia/AccidentPartyTypeTabs.vue';
import KniaRankingCard from '../components/knia/KniaRankingCard.vue';
import { useSessionStore } from '../stores/session';

const tabs = [
  { value: 'all', label: '전체' },
  { value: 'car_vs_car', label: '차대차' },
  { value: 'car_vs_person', label: '차대사람' },
  { value: 'car_vs_bicycle', label: '차대자전거' }
];

const items = ref<any[]>([]);
const detailSummary = ref<any>(null);
const selectedParty = ref('all');
const searchQuery = ref('');
const loading = ref(false);
const collecting = ref(false);
const collectingDetails = ref(false);
const error = ref('');
const message = ref('');
const session = useSessionStore();

const selectedLabel = computed(() => tabs.find((x) => x.value === selectedParty.value)?.label ?? '전체');
const isFiltered = computed(() => Boolean(searchQuery.value.trim()) || selectedParty.value !== 'all');
const isAdmin = computed(() => session.user?.role === 'admin');
const hasMissingDetails = computed(() => Number(detailSummary.value?.detail_missing_count || 0) > 0);
const canCollectDetails = computed(() => isAdmin.value && items.value.length > 0 && hasMissingDetails.value);
const detailStatusText = computed(() => {
  if (!items.value.length || !detailSummary.value) return '';
  const ready = Number(detailSummary.value.detail_ready_count || 0);
  const total = Number(detailSummary.value.displayed_count || items.value.length);
  const missing = Number(detailSummary.value.detail_missing_count || 0);
  return missing
    ? `표시된 ${total}건 중 상세 기준 ${ready}건 수집 완료, ${missing}건은 상세 본문 수집이 필요합니다.`
    : `표시된 ${total}건의 상세 기준이 모두 준비되어 있습니다.`;
});
const emptyTitle = computed(() => isFiltered.value ? '관련 기준을 찾지 못했습니다.' : '아직 수집된 검색순위가 없습니다.');
const emptyDescription = computed(() =>
  isFiltered.value
    ? '검색어를 바꿔 다시 시도해 주세요.'
    : '검색순위 수집/새로고침을 실행하면 KNIA 원본 ranking 데이터를 로컬 DB에 저장한 뒤 표시합니다.'
);

function describeCollectResult(result: any) {
  const ranking = result?.result?.ranking ?? result?.ranking ?? result;
  const categories = ranking?.categories ?? {};
  const count = Number(ranking?.ranking_count ?? 0);
  const detail = Object.entries(categories).map(([key, value]) => `${key} ${value}건`).join(', ');
  return count > 0
    ? `검색순위 ${count}건을 수집했습니다${detail ? ` (${detail})` : ''}.`
    : '수집은 완료되었지만 저장된 검색순위가 없습니다. 잠시 후 다시 시도해 주세요.';
}

function describeDetailCollectResult(result: any) {
  const detail = result?.result ?? result;
  const collected = Number(detail?.collected_count ?? 0);
  const target = Number(detail?.target_count ?? 0);
  const failed = Array.isArray(detail?.failed) ? detail.failed.length : 0;
  if (collected > 0) {
    return `상세 기준 ${collected}건을 수집했습니다${target ? ` (대상 ${target}건)` : ''}${failed ? `, 실패 ${failed}건` : ''}.`;
  }
  if (target === 0) return '현재 표시 범위에서 추가로 수집할 상세 기준이 없습니다.';
  return failed ? `상세 기준 수집에 실패한 항목이 ${failed}건 있습니다.` : '상세 기준 수집 결과가 없습니다.';
}

async function load(options: { preserveMessage?: boolean } = {}) {
  loading.value = true;
  error.value = '';
  if (!options.preserveMessage) message.value = '';
  try {
    const data = await api.getKniaRanking(20, selectedParty.value, searchQuery.value.trim());
    items.value = data.items || [];
    detailSummary.value = data.detail_summary || null;
    if (data.error) {
      error.value = '검색 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';
    }
  } catch (err: any) {
    const formatted = formatApiError(err, '검색 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
    error.value = formatted.includes('요청 처리 중 문제가 발생했습니다.')
      ? '검색 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'
      : formatted;
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
    await load({ preserveMessage: true });
    if (!items.value.length) {
      error.value = result?.result?.ranking?.errors?.join('\n') || '수집 후에도 표시할 데이터가 없습니다. KNIA 원본 응답 또는 네트워크 상태를 확인해 주세요.';
    }
  } catch (err: any) {
    error.value = formatApiError(err, '검색순위 수집에 실패했습니다.');
  } finally {
    collecting.value = false;
  }
}

async function collectRankingDetails() {
  if (!items.value.length) return;
  collectingDetails.value = true;
  error.value = '';
  message.value = '';
  try {
    const result = await api.adminCollectKniaRankingDetails({ limit: Math.min(items.value.length, 20), force: false });
    message.value = describeDetailCollectResult(result);
    await load({ preserveMessage: true });
  } catch (err: any) {
    error.value = formatApiError(err, '상세 기준 수집에 실패했습니다.');
  } finally {
    collectingDetails.value = false;
  }
}

function resetSearch() {
  const shouldLoad = selectedParty.value === 'all';
  selectedParty.value = 'all';
  searchQuery.value = '';
  message.value = '';
  if (shouldLoad) load();
}

watch(selectedParty, () => {
  message.value = '';
  load();
});

onMounted(load);
</script>

<style scoped>
.knia-ranking-page { display: grid; gap: 18px; }
.ranking-hero { display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; border-color: rgba(201, 169, 98, 0.34); }
.source-link { white-space: nowrap; }
.ranking-controls-card {
  display: grid;
  gap: 16px;
  border-color: rgba(201, 169, 98, 0.34);
  background:
      linear-gradient(135deg, rgba(232, 223, 212, 0.055), rgba(201, 169, 98, 0.04)),
      rgba(37, 30, 25, 0.86);
}
.section-heading { display: flex; justify-content: space-between; align-items: center; gap: 14px; }
.section-heading h3 { margin: 0; font-size: 1.35rem; }
.section-heading.compact { margin-bottom: 12px; }
.collect-actions { display: flex; flex-wrap: wrap; gap: 10px; justify-content: flex-end; }
.ranking-search-row { display: grid; grid-template-columns: 1fr auto auto; gap: 10px; }
.ranking-search-row input { min-height: 46px; }
.collect-btn { min-width: 190px; }
.detail-status { margin: 0; }
.notice {
  padding: 12px 14px;
  border-radius: 12px;
  font-weight: 700;
}
.notice.success {
  background: rgba(167, 193, 122, 0.13);
  border: 1px solid rgba(167, 193, 122, 0.34);
  color: #d7e7b7;
}
.notice.error {
  background: rgba(139, 38, 53, 0.22);
  border: 1px solid rgba(213, 137, 137, 0.36);
  color: #f0c1c1;
  white-space: pre-line;
}
.ranking-table-head {
  display: grid;
  grid-template-columns: 56px 96px minmax(260px, 1fr) 140px 80px 220px;
  gap: 12px;
  padding: 0 14px 10px;
  color: rgba(232, 223, 212, 0.68);
  font-size: 0.82rem;
  font-weight: 800;
  border-bottom: 1px solid rgba(201, 169, 98, 0.2);
}
.ranking-list { display: grid; gap: 12px; }
.ranking-empty { display: grid; gap: 10px; justify-items: start; padding: 22px; }
.ranking-empty strong { font-size: 1.1rem; }
.loading-text, .attribution { margin-top: 12px; }
@media (max-width: 720px) {
  .ranking-hero, .section-heading { display: grid; }
  .collect-actions { justify-content: stretch; }
  .ranking-search-row { grid-template-columns: 1fr; }
  .source-link, .collect-btn { width: 100%; justify-content: center; }
  .ranking-table-head { display: none; }
  .ranking-list-card,
  .ranking-controls-card,
  .ranking-hero { padding: 16px; }
}
</style>
