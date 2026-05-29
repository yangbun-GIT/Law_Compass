<script setup lang="ts">
import { computed, ref } from 'vue';
import { api, formatApiError } from '../../api/client';
import KniaJsonEvidenceCard from './KniaJsonEvidenceCard.vue';

const query = ref('후미추돌 정차 중 뒤차 추돌');
const party = ref('');
const loading = ref(false);
const items = ref<any[]>([]);
const error = ref('');
const searched = ref(false);
const canRun = computed(() => query.value.trim().length >= 2);

const run = async () => {
  const trimmed = query.value.trim();
  if (!trimmed) {
    error.value = '검색어를 입력해 주세요.';
    return;
  }
  if (!canRun.value) {
    error.value = '검색어를 2글자 이상 입력해 주세요.';
    return;
  }
  loading.value = true;
  error.value = '';
  searched.value = true;
  try {
    items.value = (await api.searchKniaJson(trimmed, party.value, 8)).items || [];
  } catch (e) {
    items.value = [];
    error.value = formatApiError(e, 'KNIA JSON 검색에 실패했습니다.');
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <section class="glass-card knia-search-box">
    <h2>KNIA JSON 근거 검색</h2>
    <div class="form-row">
      <input v-model="query" placeholder="예: 정차 중 뒤차가 박았어" @keyup.enter="run" />
      <select v-model="party">
        <option value="">전체</option>
        <option value="car_vs_car">차대차</option>
        <option value="car_vs_person">차대사람</option>
        <option value="car_vs_bicycle">차대자전거</option>
        <option value="car_vs_object">차대기물</option>
        <option value="single_vehicle">차량단독</option>
      </select>
      <button :disabled="loading || !canRun" @click="run">{{ loading ? '검색 중...' : '검색' }}</button>
    </div>
    <p v-if="loading" class="kv">검색 중입니다...</p>
    <p v-if="error" class="notice error">{{ error }}</p>
    <p v-else-if="searched && !loading && !items.length" class="empty-note">
      검색 조건에 맞는 KNIA JSON 근거가 없습니다. 사고유형을 전체로 바꾸거나 더 일반적인 사고 상황 단어로 검색해 주세요.
    </p>
    <div class="knia-search-results">
      <KniaJsonEvidenceCard v-for="item in items" :key="item.source_url + item.title" :item="item" />
    </div>
  </section>
</template>

<style scoped>
.notice {
  padding: 12px 14px;
  border-radius: 14px;
  font-weight: 800;
}
.notice.error {
  background: rgba(255, 112, 132, 0.13);
  border: 1px solid rgba(255, 112, 132, 0.35);
  color: #ffb7c3;
  white-space: pre-line;
}
.empty-note {
  color: var(--text-sub);
  padding: 14px;
  border-radius: 14px;
  border: 1px dashed rgba(201, 169, 98, 0.24);
}
</style>
