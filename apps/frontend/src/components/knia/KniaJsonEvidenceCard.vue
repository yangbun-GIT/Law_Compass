<script setup lang="ts">
defineProps<{ item: any }>();
</script>
<template>
  <article class="glass-card knia-json-evidence-card">
    <p class="eyebrow">{{ item.accident_party_label || 'KNIA 근거' }}</p>
    <h3>{{ item.title || '과실비율 기준' }}</h3>
    <p>{{ item.summary || '원문 기준을 확인해 주세요.' }}</p>
    <div class="tag-row"><span v-for="tag in item.display_tags || []" :key="tag" class="tag">{{ tag }}</span></div>
    <a v-if="item.source_url" :href="item.source_url" target="_blank" rel="noreferrer">원문 기준 보기</a>
    <small>{{ item.attribution || '자료 출처: 과실비율정보포털' }}</small>
  </article>
</template>
