<script setup lang="ts">
import { ref } from 'vue';
import { api } from '../../api/client';
import KniaJsonEvidenceCard from './KniaJsonEvidenceCard.vue';
const query = ref('후미추돌 정차 중 뒤차 추돌');
const party = ref('');
const loading = ref(false);
const items = ref<any[]>([]);
const run = async () => {
  loading.value = true;
  try { items.value = (await api.searchKniaJson(query.value, party.value, 8)).items || []; }
  finally { loading.value = false; }
};
</script>
<template>
  <section class="glass-card knia-search-box">
    <h2>KNIA JSON 근거 검색</h2>
    <div class="form-row">
      <input v-model="query" placeholder="예: 정차 중 뒤차가 박았어" />
      <select v-model="party">
        <option value="">전체</option><option value="car_vs_car">차대차</option><option value="car_vs_person">차대사람</option><option value="car_vs_bicycle">차대자전거</option><option value="car_vs_object">차대기물</option><option value="single_vehicle">차량단독</option>
      </select>
      <button @click="run">검색</button>
    </div>
    <p v-if="loading">검색 중입니다...</p>
    <div class="knia-search-results"><KniaJsonEvidenceCard v-for="item in items" :key="item.source_url + item.title" :item="item" /></div>
  </section>
</template>
