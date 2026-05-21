<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../api/client';
import KniaMyAccidentPageGrid from '../components/knia/KniaMyAccidentPageGrid.vue';
import KniaJsonSearchBox from '../components/knia/KniaJsonSearchBox.vue';
const pages = ref<any[]>([]);
const error = ref('');
onMounted(async () => {
  try { pages.value = (await api.getKniaMyAccidentPages()).items || []; }
  catch (e: any) { error.value = e.message || 'KNIA 메뉴를 불러오지 못했습니다.'; }
});
</script>
<template>
  <main class="page-shell">
    <section class="hero-card glass-card">
      <p class="eyebrow">KNIA JSON 데이터</p>
      <h1>나의 과실비율 알아보기</h1>
      <p>사전에 수집한 과실비율정보포털 JSON을 기준으로 사고유형 메뉴와 근거를 보여드립니다.</p>
    </section>
    <p v-if="error" class="error-text">{{ error }}</p>
    <KniaMyAccidentPageGrid :pages="pages" />
    <KniaJsonSearchBox />
  </main>
</template>
