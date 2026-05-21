<script setup lang="ts">
defineProps<{ item: any }>();
</script>
<template>
  <article class="glass-card knia-media-card">
    <h3>{{ item.title || 'KNIA 관련 자료' }}</h3>
    <p>영상이나 원문은 과실비율정보포털 원본 링크로 확인합니다. 파일은 저장하지 않습니다.</p>
    <a v-if="item.target_url || item.source_url" :href="item.target_url || item.source_url" target="_blank" rel="noreferrer">
      {{ item.button_label || '원문 자료 보기' }}
    </a>
    <small>{{ item.attribution || '자료 출처: 과실비율정보포털' }}</small>
  </article>
</template>
