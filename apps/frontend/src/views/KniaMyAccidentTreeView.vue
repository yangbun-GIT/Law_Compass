<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { api } from '../api/client';
import KniaMenuTree from '../components/knia/KniaMenuTree.vue';
import KniaJsonSearchBox from '../components/knia/KniaJsonSearchBox.vue';
const route = useRoute();
const page = ref<any>(null);
const tree = ref<any[]>([]);
const error = ref('');
const no = computed(() => Number(route.params.myaccidentNo || 1));
onMounted(async () => {
  try {
    const res = await api.getKniaMyAccidentTree(no.value);
    page.value = res.page;
    tree.value = res.tree || [];
  } catch (e: any) { error.value = e.message || '메뉴 트리를 불러오지 못했습니다.'; }
});
</script>
<template>
  <main class="page-shell">
    <section class="hero-card glass-card">
      <p class="eyebrow">{{ page?.accident_party_label || 'KNIA 사고유형' }}</p>
      <h1>{{ page?.page_title || '사고유형 메뉴' }}</h1>
      <p>{{ page?.page_description || 'JSON visible_items에서 정리한 메뉴입니다.' }}</p>
      <a v-if="page?.page_url" :href="page.page_url" target="_blank" rel="noreferrer">과실비율정보포털 원문 보기</a>
    </section>
    <p v-if="error" class="error-text">{{ error }}</p>
    <section class="glass-card">
      <h2>사고유형 메뉴 트리</h2>
      <p class="muted">기준번호가 있는 항목은 기준 화면으로 이동할 수 있습니다.</p>
      <KniaMenuTree :nodes="tree" />
    </section>
    <KniaJsonSearchBox />
  </main>
</template>
