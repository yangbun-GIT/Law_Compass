<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ item: any }>();
const safeTargetUrl = computed(() => safeKniaUrl(props.item?.target_url || props.item?.source_url));

function safeKniaUrl(value: unknown) {
  const raw = String(value || '').trim();
  if (!raw || /\s/.test(raw)) return '';
  try {
    const url = new URL(raw);
    return ['http:', 'https:'].includes(url.protocol) && url.hostname.toLowerCase() === 'accident.knia.or.kr' ? url.toString() : '';
  } catch {
    return '';
  }
}
</script>
<template>
  <article class="glass-card knia-media-card">
    <h3>{{ item.title || 'KNIA 관련 자료' }}</h3>
    <p>영상이나 원문은 과실비율정보포털 원본 링크로 확인합니다. 파일은 저장하지 않습니다.</p>
    <a v-if="safeTargetUrl" :href="safeTargetUrl" target="_blank" rel="noopener noreferrer">
      {{ item.button_label || '원문 자료 보기' }}
    </a>
    <small>{{ item.attribution || '자료 출처: 과실비율정보포털' }}</small>
  </article>
</template>
