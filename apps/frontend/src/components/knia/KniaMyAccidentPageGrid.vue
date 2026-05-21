<script setup lang="ts">
defineProps<{ pages: any[] }>();
</script>

<template>
  <div class="knia-page-grid">
    <RouterLink v-for="page in pages" :key="page.myaccident_no" class="glass-card knia-page-card" :to="`/knia/myaccident/${page.myaccident_no}`">
      <p class="eyebrow">{{ page.accident_party_label || '사고유형' }}</p>
      <h3>{{ page.page_title || `나의 과실비율 ${page.myaccident_no}` }}</h3>
      <p>{{ page.page_description || '수집된 과실비율 기준 메뉴를 확인할 수 있습니다.' }}</p>
      <span>{{ page.raw_menu_count || 0 }}개 메뉴</span>
    </RouterLink>
  </div>
</template>
